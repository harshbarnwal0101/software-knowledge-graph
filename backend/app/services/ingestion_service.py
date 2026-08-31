"""
Ingestion service — orchestrates the full repository analysis pipeline.

Pipeline:
  clone → discover files → parse → extract symbols → build graph → update DB stats → done
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
            logger.error(f"Repository {repo_id} not found")
            return

        logger.info(f"Starting analysis for {repo.name} ({repo_id})")

        # ── 2. Clone ─────────────────────────────────────────────
        await _update_status(db, repo_id, RepoStatus.cloning, "Cloning repository…")
        try:
            repo_path = clone_repository(repo_id, repo.github_url)
        except Exception as e:
            logger.error(f"Clone failed for {repo_id}: {e}")
            await _update_status(db, repo_id, RepoStatus.failed, f"Clone failed: {str(e)[:200]}")
            return

        # ── 3. Discover files ─────────────────────────────────────
        await _update_status(db, repo_id, RepoStatus.parsing, "Discovering and parsing files…")
        try:
            files = registry.discover_files(repo_path)
            logger.info(f"Discovered {len(files)} source files in {repo.name}")
        except Exception as e:
            logger.error(f"File discovery failed: {e}")
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

        for file_path in files:
            try:
                parsed = registry.parse_file(file_path)
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

                # Store symbols
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

            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
                parse_errors += 1

        await db.commit()

        # ── 6. Build Knowledge Graph in Neo4j ──────────────────────
        await _update_status(db, repo_id, RepoStatus.building_graph, "Building knowledge graph…")
        try:
            neo4j_service.build_repository_graph(
                repo_id=repo_id,
                repo_name=repo.name,
                file_records=file_records_list,
                symbols=symbols_list,
            )
        except Exception as e:
            logger.warning(f"Neo4j graph building failed: {e}")

        # ── 7. Update repository stats ────────────────────────────
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
            f"Analysis complete for {repo_id}: "
            f"{len(files)} files, {total_classes} classes, {total_functions} functions"
        )
