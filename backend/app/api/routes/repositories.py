import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepoStatus
from app.models.file_record import FileRecord
from app.models.symbol import Symbol
from app.api.schemas import RepositoryCreate, RepositoryOut
from app.api.deps import get_current_user
from app.services.ingestion_service import run_analysis

router = APIRouter()


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
    # Clean up cloned files
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
    """
    Trigger repository analysis pipeline in the background.
    Returns 202 immediately. Poll GET /repositories/{id} for status.
    """
    repo = await _get_owned_repo(db, repo_id, current_user.id)

    if repo.status in (RepoStatus.cloning, RepoStatus.parsing, RepoStatus.building_graph, RepoStatus.embedding):
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    # Reset status
    repo.status = RepoStatus.pending
    repo.status_message = "Analysis queued…"
    await db.commit()

    background_tasks.add_task(run_analysis, repo_id)

    return {"message": "Analysis started", "repo_id": repo_id}


# ── Files ─────────────────────────────────────────────────────

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
        {
            "id": f.id,
            "path": f.path,
            "language": f.language,
            "lines": f.lines,
            "size_bytes": f.size_bytes,
        }
        for f in files
    ]


# ── Symbols ───────────────────────────────────────────────────

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
            "id": s.id,
            "type": s.symbol_type,
            "name": s.name,
            "qualified_name": s.qualified_name,
            "parent_name": s.parent_name,
            "file_path": s.file_path,
            "language": s.language,
            "line_start": s.line_start,
            "line_end": s.line_end,
            "signature": s.signature,
            "docstring": s.docstring,
        }
        for s in symbols
    ]


# ── Helpers ───────────────────────────────────────────────────

async def _get_owned_repo(db: AsyncSession, repo_id: str, user_id: str) -> Repository:
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.user_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
