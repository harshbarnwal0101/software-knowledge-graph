"""
Patch & Code Modification Service — generates unified diff patches for code modifications.
Never modifies user repository without explicit approval.
"""
import difflib
import logging
from typing import Dict, Any

from app.services.git_service import get_repo_path

logger = logging.getLogger(__name__)


def generate_patch(repo_id: str, file_path: str, instruction: str) -> Dict[str, Any]:
    """
    Propose code changes based on user instructions and return unified diff.
    """
    repo_dir = get_repo_path(repo_id)
    target = repo_dir / file_path

    if not target.exists() or not target.is_file():
        return {"error": f"File {file_path} not found"}

    try:
        original_content = target.read_text(encoding="utf-8", errors="replace")
        original_lines = original_content.splitlines(keepends=True)

        # Simple demonstration patch: append instruction comment or function wrapper
        modified_lines = list(original_lines)
        comment = f"\n# Proposed modification: {instruction}\n"
        modified_lines.append(comment)

        diff = "".join(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        ))

        return {
            "file_path": file_path,
            "instruction": instruction,
            "diff": diff or "No changes required.",
            "status": "proposed_diff_ready",
        }
    except Exception as e:
        return {"error": str(e)}
