"""
Ingestion service — orchestrates the full repository analysis pipeline.

Pipeline:
  clone → discover files → parse → extract symbols → build graph → generate embeddings → update DB stats → done
"""
import logging
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository, RepoStatus
from app.models.file_record import FileRecord
from app.models.symbol import Symbol
from app.services.git_service import clone_repository, delete_repository
from app.parsers.registry import registry
from app.graph.neo4j_service import neo4j_service
from app.retrieval.vector_service import vector_service
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _update_status(db: AsyncSession, repo_id: str, status: RepoStatus, message: str = None):
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if repo:
        repo.status = status
        if message:
            repo.status_message = message
        await db.commit()


async def run_analysis(repo_id: str):
    """
    Full ingestion pipeline for a repository.
    Called as a FastAPI BackgroundTask.
    """
    async with AsyncSessionLocal() as db:
        # ── 1. Load repo ────────────────────────────────────────
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if not repo:
            logger.error(f"[INGESTION] Repository {repo_id} not found — aborting.")
            return

        logger.info(f"[INGESTION] Starting analysis for {repo.name} ({repo_id})")

        # ── 2. Clone ─────────────────────────────────────────────
        await _update_status(db, repo_id, RepoStatus.cloning, "Cloning repository…")
        try:
            import asyncio
            logger.info(f"[INGESTION] Starting clone: {repo.github_url}")
            repo_path = await asyncio.to_thread(
                clone_repository,
                repo_id,
                repo.github_url
            )
            logger.info(f"[INGESTION] Clone completed → {repo_path}")
        except Exception as e:
            logger.error(f"[INGESTION] Clone failed for {repo_id}: {e}")
            await _update_status(db, repo_id, RepoStatus.failed, f"Clone failed: {str(e)[:200]}")
            return

        # ── 3. Discover files ─────────────────────────────────────
        await _update_status(db, repo_id, RepoStatus.parsing, "Discovering and parsing files…")
        try:
            files = await asyncio.to_thread(registry.discover_files, repo_path)
            logger.info(f"[INGESTION] Discovered {len(files)} source files in {repo.name}")
        except Exception as e:
            logger.error(f"[INGESTION] File discovery failed: {e}")
            await _update_status(db, repo_id, RepoStatus.failed, f"File discovery failed: {str(e)[:200]}")
            return

        # ── 4. Clear previous data ────────────────────────────────
        await db.execute(delete(Symbol).where(Symbol.repo_id == repo_id))
        await db.execute(delete(FileRecord).where(FileRecord.repo_id == repo_id))
        await db.commit()

        # ── 5. Parse files + store symbols ────────────────────────
        total_lines = 0
        total_classes = 0
        total_functions = 0
        parse_errors = 0

        file_records_list = []
        symbols_list = []
        chunks_for_embedding = []

        for file_path in files:
            try:
                parsed = await asyncio.to_thread(registry.parse_file, file_path)
                if not parsed:
                    continue

                relative_path = str(file_path.relative_to(repo_path))

                # Store FileRecord
                f_id = str(uuid.uuid4())
                file_record = FileRecord(
                    id=f_id,
                    repo_id=repo_id,
                    path=relative_path,
                    language=parsed.language,
                    lines=parsed.lines,
                    size_bytes=file_path.stat().st_size,
                )
                db.add(file_record)
                await db.flush()

                file_records_list.append({
                    "id": f_id,
                    "path": relative_path,
                    "language": parsed.language,
                    "lines": parsed.lines,
                })

                total_lines += parsed.lines
                total_classes += len(parsed.classes)
                total_functions += len(parsed.functions) + len(parsed.methods)

                if parsed.errors:
                    parse_errors += 1

                # Read source text for chunking
                source_content = ""
                try:
                    source_content = file_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

                # Store symbols & create chunks
                for sym in parsed.symbols:
                    s_id = str(uuid.uuid4())
                    db.add(Symbol(
                        id=s_id,
                        repo_id=repo_id,
                        file_id=f_id,
                        file_path=relative_path,
                        language=parsed.language,
                        symbol_type=sym.symbol_type,
                        name=sym.name,
                        qualified_name=sym.qualified_name,
                        parent_name=sym.parent_name,
                        line_start=sym.line_start,
                        line_end=sym.line_end,
                        docstring=sym.docstring,
                        signature=sym.signature,
                    ))

                    symbols_list.append({
                        "id": s_id,
                        "file_id": f_id,
                        "file_path": relative_path,
                        "language": parsed.language,
                        "type": sym.symbol_type,
                        "name": sym.name,
                        "qualified_name": sym.qualified_name,
                        "line_start": sym.line_start,
                        "line_end": sym.line_end,
                        "signature": sym.signature,
                    })

                    # Add symbol chunk for vector embedding
                    chunk_text = f"File: {relative_path}\nSymbol: {sym.symbol_type} {sym.name}\n"
                    if sym.signature:
                        chunk_text += f"Signature: {sym.signature}\n"
                    if sym.docstring:
                        chunk_text += f"Docstring: {sym.docstring}\n"

                    chunks_for_embedding.append({
                        "file_path": relative_path,
                        "name": sym.name,
                        "chunk_type": sym.symbol_type,
                        "line_start": sym.line_start,
                        "line_end": sym.line_end,
                        "content": chunk_text,
                    })

                # If file has content, add full file overview chunk
                if source_content:
                    chunks_for_embedding.append({
                        "file_path": relative_path,
                        "name": relative_path.split("/")[-1],
                        "chunk_type": "file",
                        "line_start": 1,
                        "line_end": parsed.lines,
                        "content": f"File: {relative_path}\nLanguage: {parsed.language}\n\n" + source_content[:1500],
                    })

            except Exception as e:
                logger.warning(f"[INGESTION] Failed to parse {file_path}: {e}")
                parse_errors += 1

        await db.commit()
        logger.info(f"[INGESTION] Parsing completed — {len(file_records_list)} files, {len(symbols_list)} symbols")

        # ── 6. Build Knowledge Graph in Neo4j ──────────────────────
        await _update_status(db, repo_id, RepoStatus.building_graph, "Building knowledge graph…")
        logger.info(f"[INGESTION] Building knowledge graph in Neo4j…")
        try:
            await asyncio.to_thread(
                neo4j_service.build_repository_graph,
                repo_id,
                repo.name,
                file_records_list,
                symbols_list,
            )
            logger.info(f"[INGESTION] Knowledge graph built successfully")
        except Exception as e:
            logger.warning(f"[INGESTION] Neo4j graph building failed (non-fatal): {e}")

        # ── 7. Generate Vector Embeddings in Qdrant ────────────────
        await _update_status(db, repo_id, RepoStatus.embedding, "Generating vector embeddings…")
        logger.info(f"[INGESTION] Generating vector embeddings in Qdrant ({len(chunks_for_embedding)} chunks)…")
        try:
            await asyncio.to_thread(vector_service.index_chunks, repo_id, chunks_for_embedding)
            logger.info(f"[INGESTION] Vector embeddings generated successfully")
        except Exception as e:
            logger.warning(f"[INGESTION] Vector embedding failed (non-fatal): {e}")

        # ── 8. Update repository status to Ready ──────────────────
        result = await db.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()
        if repo:
            repo.total_files = len(files)
            repo.total_lines = total_lines
            repo.total_classes = total_classes
            repo.total_functions = total_functions
            repo.status = RepoStatus.ready
            repo.status_message = (
                f"Analysis complete. "
                f"{len(files)} files, {total_classes} classes, {total_functions} functions parsed."
                + (f" ({parse_errors} files had parse errors)" if parse_errors else "")
            )
            await db.commit()

        logger.info(
            f"[INGESTION] Analysis complete for {repo_id}: "
            f"{len(files)} files, {total_classes} classes, {total_functions} functions"
        )
