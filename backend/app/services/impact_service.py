"""
Impact Analysis Service — analyzes what code will break if a class, function, or file is changed.
Traverses Neo4j graph and SQL symbol dependencies to determine risk level and affected modules.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.symbol import Symbol
from app.models.file_record import FileRecord
from app.graph.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)


async def analyze_impact(db: AsyncSession, repo_id: str, target_name: str) -> Dict[str, Any]:
    """
    Perform graph-based impact analysis for target symbol or file.
    """
    # 1. Lookup target symbol details
    target_sym_res = await db.execute(
        select(Symbol).where(Symbol.repo_id == repo_id, Symbol.name.ilike(f"%{target_name}%"))
    )
    target_symbols = target_sym_res.scalars().all()

    target_info = {
        "name": target_name,
        "found": len(target_symbols) > 0,
        "files": list(set([s.file_path for s in target_symbols])),
    }

    # 2. Query Graph / SQL for dependents
    direct_dependents = []
    indirect_dependents = []
    recommended_tests = []

    driver = neo4j_service.get_driver()
    if driver:
        cypher = """
        MATCH (target {name: $name, repo_id: $repo_id})<-[r]-(dep)
        RETURN dep.name as name, dep.file_path as file_path, labels(dep) as type, type(r) as relation
        LIMIT 20
        """
        try:
            with driver.session() as session:
                result = session.run(cypher, name=target_name, repo_id=repo_id)
                for rec in result:
                    direct_dependents.append({
                        "name": rec["name"] or "Unnamed",
                        "file_path": rec["file_path"] or "",
                        "type": list(rec["type"])[0] if rec["type"] else "Symbol",
                        "relation": rec["relation"],
                    })
        except Exception as e:
            logger.warning(f"Neo4j impact query failed: {e}")

    # Fallback / augment with SQL import/symbol match
    if not direct_dependents:
        all_syms_res = await db.execute(select(Symbol).where(Symbol.repo_id == repo_id).limit(150))
        all_syms = all_syms_res.scalars().all()
        for s in all_syms:
            if s.symbol_type == "import" and target_name in s.name:
                direct_dependents.append({
                    "name": s.file_path.split("/")[-1],
                    "file_path": s.file_path,
                    "type": "File",
                    "relation": "IMPORTS",
                })

    # Search test files
    test_files_res = await db.execute(
        select(FileRecord).where(FileRecord.repo_id == repo_id, FileRecord.path.ilike("%test%"))
    )
    test_files = test_files_res.scalars().all()
    for tf in test_files:
        recommended_tests.append(tf.path)

    # 3. Calculate Risk Level
    dep_count = len(direct_dependents)
    if dep_count >= 5:
        risk_level = "HIGH"
        risk_explanation = f"High risk change — {dep_count} modules depend directly on {target_name}."
    elif dep_count >= 2:
        risk_level = "MEDIUM"
        risk_explanation = f"Medium risk change — {dep_count} modules depend directly on {target_name}."
    else:
        risk_level = "LOW"
        risk_explanation = f"Low risk change — {dep_count} direct dependents found."

    return {
        "target": target_info,
        "impact_level": risk_level,
        "risk_explanation": risk_explanation,
        "direct_dependents": direct_dependents,
        "indirect_dependents": indirect_dependents,
        "recommended_tests": recommended_tests[:5],
    }
