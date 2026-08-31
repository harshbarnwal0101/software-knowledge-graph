"""
Patch & Code Modification Service — generates unified diff patches for code modifications.
Never modifies user repository without explicit approval.
"""
import difflib
import logging
import re
from typing import Dict, Any

from app.services.git_service import get_repo_path
from app.core.config import settings

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

        modified_content = original_content
        llm = None
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                llm = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
            except Exception:
                pass
        
        if llm:
            try:
                prompt_messages = [
                    {
                        "role": "system", 
                        "content": "You are an expert software engineer. Modify the provided code according to the instruction. Output ONLY the complete modified code, surrounded by ``` code block syntax."
                    },
                    {
                        "role": "user",
                        "content": f"Instruction: {instruction}\n\nOriginal Code:\n```\n{original_content}\n```"
                    }
                ]
                res = llm.chat.completions.create(
                    model=settings.llm_model,
                    messages=prompt_messages,
                    temperature=0.2,
                )
                answer_text = res.choices[0].message.content
                
                # Extract code from Markdown block
                match = re.search(r"```[a-zA-Z]*\n(.*?)```", answer_text, re.DOTALL)
                if match:
                    modified_content = match.group(1)
                else:
                    modified_content = answer_text.strip()
            except Exception as e:
                logger.warning(f"LLM patch generation failed: {e}")
                modified_content = original_content + f"\n# Proposed modification: {instruction}\n"
        else:
            # Fallback when no API key
            modified_content = original_content + f"\n# Proposed modification: {instruction}\n"

        # Ensure trailing newline is handled properly based on original
        if not modified_content.endswith("\n") and original_content.endswith("\n"):
            modified_content += "\n"
        elif modified_content.endswith("\n") and not original_content.endswith("\n"):
            modified_content = modified_content.rstrip("\n")

        modified_lines = modified_content.splitlines(keepends=True)

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
