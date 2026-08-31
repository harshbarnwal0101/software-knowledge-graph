"""
Hybrid Search Engine — combines Exact Keyword/Symbol Search + Vector Semantic Search
with Reciprocal Rank Fusion (RRF) for code retrieval.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.symbol import Symbol
from app.models.file_record import FileRecord
from app.retrieval.vector_service import vector_service

logger = logging.getLogger(__name__)


async def hybrid_search(
    db: AsyncSession,
    repo_id: str,
    query: str,
    top_k: int = 15,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid retrieval (Keyword SQL + Vector Qdrant) merged via RRF.
    """
    query_str = query.strip()
    if not query_str:
        return []

    # 1. Keyword / Symbol Search in PostgreSQL
    keyword_results = []
    try:
        # Match symbol names or file paths
        sym_query = (
            select(Symbol)
            .where(
                Symbol.repo_id == repo_id,
                or_(
                    Symbol.name.ilike(f"%{query_str}%"),
                    Symbol.qualified_name.ilike(f"%{query_str}%"),
                    Symbol.file_path.ilike(f"%{query_str}%"),
                )
            )
            .limit(top_k)
        )
        res = await db.execute(sym_query)
        symbols = res.scalars().all()

        for s in symbols:
            keyword_results.append({
                "source": "keyword",
                "file_path": s.file_path,
                "name": s.name,
                "type": s.symbol_type,
                "line_start": s.line_start,
                "line_end": s.line_end,
                "content": f"{s.symbol_type.capitalize()} {s.name} in {s.file_path}:{s.line_start}",
            })
    except Exception as e:
        logger.warning(f"Keyword search failed: {e}")

    # 2. Vector Semantic Search in Qdrant
    vector_results = []
    try:
        vec_hits = vector_service.search(repo_id, query_str, top_k=top_k)
        for hit in vec_hits:
            vector_results.append({
                "source": "vector",
                "file_path": hit["file_path"],
                "name": hit.get("name", ""),
                "type": hit.get("chunk_type", "code"),
                "line_start": hit.get("line_start", 1),
                "line_end": hit.get("line_end", 1),
                "content": hit["content"],
                "vector_score": hit["score"],
            })
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")

    # 3. Reciprocal Rank Fusion (RRF)
    rrf_scores = {}
    item_map = {}
    k_constant = 60

    # Rank Keyword Results
    for rank, item in enumerate(keyword_results, 1):
        key = f"{item['file_path']}:{item['line_start']}:{item['name']}"
        rrf_scores[key] = rrf_scores.get(key, 0) + (1.0 / (k_constant + rank))
        item_map[key] = item

    # Rank Vector Results
    for rank, item in enumerate(vector_results, 1):
        key = f"{item['file_path']}:{item['line_start']}:{item['name']}"
        rrf_scores[key] = rrf_scores.get(key, 0) + (1.0 / (k_constant + rank))
        if key not in item_map:
            item_map[key] = item
        else:
            item_map[key]["source"] = "hybrid"

    # Sort items by RRF score
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)

    final_results = []
    for key in sorted_keys[:top_k]:
        item = item_map[key]
        item["rrf_score"] = round(rrf_scores[key], 4)
        final_results.append(item)

    return final_results
