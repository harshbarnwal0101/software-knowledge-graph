import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.user import User
from app.models.repository import Repository, RepoStatus
from app.api.schemas import RepositoryCreate, RepositoryOut
from app.api.deps import get_current_user

router = APIRouter()


def _extract_repo_name(github_url: str) -> str:
    """Extract repo name from GitHub URL."""
    match = re.search(r"github\.com/[^/]+/([^/\.]+)", github_url)
    return match.group(1) if match else github_url.split("/")[-1]


def _validate_github_url(url: str) -> bool:
    return bool(re.match(r"https?://github\.com/[\w\-\.]+/[\w\-\.]+", url))


@router.post("", response_model=RepositoryOut, status_code=status.HTTP_201_CREATED)
async def create_repository(
    body: RepositoryCreate,
    background_tasks: BackgroundTasks,
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

    # TODO Phase 2: background_tasks.add_task(analyze_repository, repo.id)

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
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.user_id == current_user.id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.user_id == current_user.id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    await db.delete(repo)
    await db.commit()
