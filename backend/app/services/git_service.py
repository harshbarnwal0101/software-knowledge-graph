"""
Git service — clone and manage repository checkouts.
"""
import os
import shutil
import logging
import subprocess
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base directory where repos are cloned
REPOS_BASE = Path(__file__).parent.parent.parent / "repos"
REPOS_BASE.mkdir(exist_ok=True)


def get_repo_path(repo_id: str) -> Path:
    return REPOS_BASE / repo_id


def clone_repository(repo_id: str, github_url: str) -> Path:
    """
    Clone a GitHub repository to disk.
    Returns the local path.
    Raises RuntimeError on failure.
    """
    dest = get_repo_path(repo_id)

    # Remove previous clone if exists
    if dest.exists():
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)

    # Build clone command
    cmd = ["git", "clone", "--depth", "1"]

    # Inject token for private repos if available
    if settings.github_token:
        # Insert token into URL: https://TOKEN@github.com/...
        url = github_url.replace("https://", f"https://{settings.github_token}@")
    else:
        url = github_url

    cmd += [url, str(dest)]

    logger.info(f"Cloning {github_url} → {dest}")

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("git clone timed out after 5 minutes")

    logger.info(f"Clone complete: {dest}")
    return dest


def delete_repository(repo_id: str) -> None:
    """Remove a cloned repository from disk."""
    dest = get_repo_path(repo_id)
    if dest.exists():
        shutil.rmtree(dest)
        logger.info(f"Deleted repo dir: {dest}")


def get_git_log(repo_path: Path, max_commits: int = 50) -> list[dict]:
    """Extract recent git commits from the cloned repository."""
    try:
        result = subprocess.run(
            [
                "git", "log",
                f"--max-count={max_commits}",
                "--pretty=format:%H|%an|%ae|%ai|%s",
            ],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            timeout=30,
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })
        return commits
    except Exception as e:
        logger.warning(f"Could not extract git log: {e}")
        return []
