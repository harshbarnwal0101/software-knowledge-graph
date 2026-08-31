import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepoStatus
from app.models.file_record import FileRecord
from app.models.symbol import Symbol
from app.api.schemas import RepositoryCreate, RepositoryOut
from app.api.deps import get_current_user
from app.services.ingestion_service import run_analysis
from app.services.impact_service import analyze_impact
from app.services.patch_service import generate_patch
from app.services.git_service import get_repo_path, get_git_log
from app.graph.neo4j_service import neo4j_service
from app.retrieval.hybrid_search import hybrid_search
from app.agents.codebase_agent import codebase_agent

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 15


class ChatRequest(BaseModel):
    question: str


class ImpactRequest(BaseModel):
    target_name: str


class ModifyCodeRequest(BaseModel):
    file_path: str
    instruction: str


def _extract_repo_name(github_url: str) -> str:
    match = re.search(r"github\.com/[^/]+/([^/\.]+)", github_url)
    return match.group(1) if match else github_url.split("/")[-1]


def _validate_github_url(url: str) -> bool:
    return bool(re.match(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", url))


# ── CRUD ──────────────────────────────────────────────────────

@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def create_repository(
    body: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _validate_github_url(body.github_url):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    name = body.name or _extract_repo_name(body.github_url)

    repo = Repository(
        user_id=current_user.id,
        name=name,
        description=body.description,
        github_url=body.github_url,
        status=RepoStatus.pending,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@router.get("", response_model=List[RepositoryOut])
async def list_repositories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Repository).where(Repository.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{repo_id}", response_model=RepositoryOut)
async def get_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = await _get_owned_repo(db, repo_id, current_user.id)
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = await _get_owned_repo(db, repo_id, current_user.id)
    await db.delete(repo)
    await db.commit()
    try:
        from app.services.git_service import delete_repository as delete_clone
        delete_clone(repo_id)
    except Exception:
        pass


# ── Analysis ──────────────────────────────────────────────────

@router.post("/{repo_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = await _get_owned_repo(db, repo_id, current_user.id)

    if repo.status in (RepoStatus.cloning, RepoStatus.parsing, RepoStatus.building_graph, RepoStatus.embedding):
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    repo.status = RepoStatus.pending
    repo.status_message = "Analysis queued…"
    await db.commit()

    background_tasks.add_task(run_analysis, repo_id)

    return {"message": "Analysis started", "repo_id": repo_id}


# ── Files & Symbols ───────────────────────────────────────────

@router.get("/{repo_id}/files")
async def list_files(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    result = await db.execute(
        select(FileRecord).where(FileRecord.repo_id == repo_id).order_by(FileRecord.path)
    )
    files = result.scalars().all()
    return [
        {"id": f.id, "path": f.path, "language": f.language, "lines": f.lines, "size_bytes": f.size_bytes}
        for f in files
    ]


@router.get("/{repo_id}/symbols")
async def list_symbols(
    repo_id: str,
    symbol_type: str = None,
    search: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)

    query = select(Symbol).where(Symbol.repo_id == repo_id)
    if symbol_type:
        query = query.where(Symbol.symbol_type == symbol_type)
    if search:
        query = query.where(Symbol.name.ilike(f"%{search}%"))

    query = query.order_by(Symbol.file_path, Symbol.line_start).limit(limit)
    result = await db.execute(query)
    symbols = result.scalars().all()

    return [
        {
            "id": s.id, "type": s.symbol_type, "name": s.name, "qualified_name": s.qualified_name,
            "parent_name": s.parent_name, "file_path": s.file_path, "language": s.language,
            "line_start": s.line_start, "line_end": s.line_end, "signature": s.signature, "docstring": s.docstring
        }
        for s in symbols
    ]


# ── Graph API ─────────────────────────────────────────────────

@router.get("/{repo_id}/graph")
async def get_repository_graph(
    repo_id: str,
    limit: int = 150,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    data = neo4j_service.get_graph_data(repo_id, max_nodes=limit)

    if not data or not data.get("nodes"):
        result_files = await db.execute(select(FileRecord).where(FileRecord.repo_id == repo_id).limit(40))
        files = result_files.scalars().all()
        result_symbols = await db.execute(select(Symbol).where(Symbol.repo_id == repo_id).limit(100))
        symbols = result_symbols.scalars().all()

        nodes, edges, file_node_ids = [], [], {}
        for f in files:
            nid = f"file_{f.id}"
            file_node_ids[f.path] = nid
            nodes.append({"id": nid, "type": "file", "data": {"label": f.path.split("/")[-1], "path": f.path, "language": f.language, "nodeType": "File"}})

        for s in symbols:
            sid = f"sym_{s.id}"
            nodes.append({"id": sid, "type": s.symbol_type, "data": {"label": s.name, "path": s.file_path, "line": s.line_start, "signature": s.signature, "nodeType": s.symbol_type.capitalize()}})
            if s.file_path in file_node_ids:
                edges.append({"id": f"e_{file_node_ids[s.file_path]}_{sid}_DEFINES", "source": file_node_ids[s.file_path], "target": sid, "label": "DEFINES"})

        data = {"nodes": nodes, "edges": edges}

    return data


# ── Search & Chat ──────────────────────────────────────────────

@router.post("/{repo_id}/search")
async def search_repository(
    repo_id: str,
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    results = await hybrid_search(db, repo_id, body.query, top_k=body.limit or 15)
    return {"query": body.query, "results": results}


@router.post("/{repo_id}/chat")
async def chat_with_repository(
    repo_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    response = await codebase_agent.answer_question(repo_id, body.question)
    return response


# ── Impact & History ──────────────────────────────────────────

@router.post("/{repo_id}/impact-analysis")
async def get_impact_analysis(
    repo_id: str,
    body: ImpactRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    return await analyze_impact(db, repo_id, body.target_name)


@router.get("/{repo_id}/history")
async def get_repository_history(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    return {"commits": get_git_log(get_repo_path(repo_id), max_commits=30)}


# ── Repository Health & Hotspots ──────────────────────────────

@router.get("/{repo_id}/health")
async def get_repository_health(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)

    # Large files (> 300 lines)
    large_files_res = await db.execute(
        select(FileRecord).where(FileRecord.repo_id == repo_id, FileRecord.lines > 300).limit(10)
    )
    large_files = [f.path for f in large_files_res.scalars().all()]

    # Missing docstrings
    missing_docs_res = await db.execute(
        select(Symbol).where(
            Symbol.repo_id == repo_id,
            Symbol.symbol_type.in_(["class", "function"]),
            Symbol.docstring == None
        ).limit(10)
    )
    missing_docs = [s.name for s in missing_docs_res.scalars().all()]

    return {
        "health_score": max(50, 100 - (len(large_files) * 5) - (len(missing_docs) * 2)),
        "large_files": large_files,
        "missing_docstrings": missing_docs,
        "hotspot_warnings": [
            f"File '{f}' exceeds 300 lines of code — consider modularizing." for f in large_files[:3]
        ]
    }


# ── Proposed Patch Generation ─────────────────────────────────

@router.post("/{repo_id}/modify-code")
async def proposed_code_modification(
    repo_id: str,
    body: ModifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_repo(db, repo_id, current_user.id)
    patch = generate_patch(repo_id, body.file_path, body.instruction)
    return patch


# ── Helpers ───────────────────────────────────────────────────

async def _get_owned_repo(db: AsyncSession, repo_id: str, user_id: str) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.user_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
