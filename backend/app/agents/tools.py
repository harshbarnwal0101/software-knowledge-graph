"""
AI Agent Tools — repository inspection tools available to the LangGraph AI Agent.
"""
import logging
from typing import List, Dict, Any
from pathlib import Path
from sqlalchemy import select

from app.models.symbol import Symbol
from app.models.file_record import FileRecord
from app.graph.neo4j_service import neo4j_service
from app.services.git_service import get_repo_path, get_git_log
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def tool_search_code(repo_id: str, query: str) -> List[Dict[str, Any]]:
    """Search code using hybrid keyword + vector retrieval."""
    from app.retrieval.hybrid_search import hybrid_search
    async with AsyncSessionLocal() as db:
        return await hybrid_search(db, repo_id, query, top_k=6)


async def tool_get_symbol(repo_id: str, symbol_name: str) -> List[Dict[str, Any]]:
    """Look up a specific symbol (class, function, method) in AST index."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Symbol).where(Symbol.repo_id == repo_id, Symbol.name.ilike(f"%{symbol_name}%"))
        )
        symbols = res.scalars().all()
        return [
            {
                "name": s.name,
                "type": s.symbol_type,
                "file_path": s.file_path,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "signature": s.signature,
                "docstring": s.docstring,
            }
            for s in symbols
        ]


async def tool_get_file(repo_id: str, file_path: str, max_lines: int = 150) -> Dict[str, Any]:
    """Read full or partial source code of a file."""
    repo_dir = get_repo_path(repo_id)
    target = repo_dir / file_path

    if not target.exists() or not target.is_file():
        return {"error": f"File {file_path} not found"}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()[:max_lines]
        return {
            "file_path": file_path,
            "total_lines": len(content.splitlines()),
            "content": "\n".join(lines),
        }
    except Exception as e:
        return {"error": str(e)}


async def tool_traverse_graph(repo_id: str, symbol_name: str) -> Dict[str, Any]:
    """Query Neo4j knowledge graph for node dependencies and connected edges."""
    driver = neo4j_service.get_driver()
    if not driver:
        return {"graph": "Neo4j unavailable"}

    cypher = """
    MATCH (n {name: $name, repo_id: $repo_id})-[r]-(connected)
    RETURN type(r) as relationship, connected.name as target_name, labels(connected) as target_type, connected.file_path as target_file
    LIMIT 10
    """
    try:
        with driver.session() as session:
            result = session.run(cypher, name=symbol_name, repo_id=repo_id)
            connections = [
                {
                    "relationship": rec["relationship"],
                    "target_name": rec["target_name"],
                    "target_type": list(rec["target_type"])[0] if rec["target_type"] else "",
                    "target_file": rec["target_file"],
                }
                for rec in result
            ]
            return {"symbol": symbol_name, "connections": connections}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_git_history(repo_id: str) -> List[Dict[str, Any]]:
    """Extract recent git commit history."""
    repo_dir = get_repo_path(repo_id)
    if not repo_dir.exists():
        return []
    return get_git_log(repo_dir, max_commits=10)
