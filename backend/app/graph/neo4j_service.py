"""
Neo4j Graph Service — manages the Software Knowledge Graph in Neo4j.
Handles node/relationship creation and graph traversal queries for React Flow.
"""
import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def get_driver(self) -> Optional[Driver]:
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                # Verify connection
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j graph database.")
            except Exception as e:
                logger.warning(f"Could not connect to Neo4j at {settings.neo4j_uri}: {e}")
                self._driver = None
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    # ── Graph Ingestion ──────────────────────────────────────────

    def build_repository_graph(self, repo_id: str, repo_name: str, file_records: List[Dict], symbols: List[Dict]):
        """
        Build or replace graph nodes and relationships for a repository.
        """
        driver = self.get_driver()
        if not driver:
            logger.warning("Neo4j driver unavailable; skipping graph database persistence.")
            return

        with driver.session() as session:
            # 1. Clear previous repo nodes
            session.run(
                "MATCH (r:Repository {id: $repo_id}) DETACH DELETE r",
                repo_id=repo_id
            )
            session.run(
                "MATCH (n {repo_id: $repo_id}) DETACH DELETE n",
                repo_id=repo_id
            )

            # 2. Create Repository Node
            session.run(
                """
                CREATE (r:Repository {
                    id: $repo_id,
                    name: $repo_name
                })
                """,
                repo_id=repo_id, repo_name=repo_name
            )

            # 3. Create File Nodes & CONTAINS relationships
            file_map = {}
            for f in file_records:
                node_id = f"file_{f['id']}"
                file_map[f['path']] = node_id
                session.run(
                    """
                    MATCH (r:Repository {id: $repo_id})
                    CREATE (f:File {
                        id: $node_id,
                        repo_id: $repo_id,
                        path: $path,
                        language: $language,
                        lines: $lines,
                        name: $name
                    })
                    CREATE (r)-[:CONTAINS]->(f)
                    """,
                    repo_id=repo_id, node_id=node_id, path=f['path'],
                    language=f['language'], lines=f['lines'], name=f['path'].split('/')[-1]
                )

            # 4. Create Symbol Nodes (Class, Function, Method) & DEFINES relationships
            symbol_node_map = {}
            for s in symbols:
                stype = s['type'].capitalize()
                node_id = f"sym_{s['id']}"
                symbol_node_map[s['name']] = node_id
                if s.get('qualified_name'):
                    symbol_node_map[s['qualified_name']] = node_id

                file_node_id = file_map.get(s['file_path'])

                # Create node dynamically with label (Class/Function/Method/Import)
                cypher = f"""
                MATCH (f:File {{id: $file_node_id}})
                CREATE (s:{stype} {{
                    id: $node_id,
                    repo_id: $repo_id,
                    name: $name,
                    qualified_name: $qualified_name,
                    file_path: $file_path,
                    line_start: $line_start,
                    line_end: $line_end,
                    signature: $signature
                }})
                CREATE (f)-[:DEFINES]->(s)
                """
                if file_node_id:
                    session.run(
                        cypher,
                        file_node_id=file_node_id, node_id=node_id, repo_id=repo_id,
                        name=s['name'], qualified_name=s.get('qualified_name', s['name']),
                        file_path=s['file_path'], line_start=s['line_start'],
                        line_end=s['line_end'], signature=s.get('signature', '')
                    )

            # 5. Extract IMPORTS & CALLS relationships
            for s in symbols:
                if s['type'] == "import":
                    # Connect File -> File / Module
                    imported_name = s['name']
                    # Check if imported_name matches a file path
                    target_file_id = None
                    for path, fid in file_map.items():
                        if imported_name.replace('.', '/') in path or path.endswith(f"{imported_name}.py"):
                            target_file_id = fid
                            break

                    file_node_id = file_map.get(s['file_path'])
                    if file_node_id and target_file_id:
                        session.run(
                            """
                            MATCH (src:File {id: $src_id}), (dst:File {id: $dst_id})
                            MERGE (src)-[:IMPORTS]->(dst)
                            """,
                            src_id=file_node_id, dst_id=target_file_id
                        )

            logger.info(f"Graph constructed in Neo4j for repository {repo_id}")

    # ── Graph Query for React Flow ────────────────────────────────

    def get_graph_data(self, repo_id: str, max_nodes: int = 150) -> Dict[str, Any]:
        """
        Fetch graph formatted for React Flow frontend.
        """
        driver = self.get_driver()
        if not driver:
            return {"nodes": [], "edges": []}

        cypher = """
        MATCH (r:Repository {id: $repo_id})-[:CONTAINS]->(f:File)
        OPTIONAL MATCH (f)-[rel:DEFINES|IMPORTS]->(target)
        RETURN f, rel, target
        LIMIT $max_nodes
        """
        with driver.session() as session:
            result = session.run(cypher, repo_id=repo_id, max_nodes=max_nodes)
            nodes_dict = {}
            edges = []

            for record in result:
                f = record["f"]
                rel = record["rel"]
                target = record["target"]

                if f and f["id"] not in nodes_dict:
                    nodes_dict[f["id"]] = {
                        "id": f["id"],
                        "type": "file",
                        "data": {
                            "label": f.get("name", f["path"]),
                            "path": f["path"],
                            "language": f.get("language", ""),
                            "nodeType": "File"
                        }
                    }

                if target and target["id"] not in nodes_dict:
                    t_labels = list(target.labels) if hasattr(target, "labels") else ["Symbol"]
                    t_type = t_labels[0] if t_labels else "Symbol"
                    nodes_dict[target["id"]] = {
                        "id": target["id"],
                        "type": t_type.lower(),
                        "data": {
                            "label": target.get("name", "Unnamed"),
                            "path": target.get("file_path", ""),
                            "line": target.get("line_start", 0),
                            "nodeType": t_type
                        }
                    }

                if f and target and rel:
                    edges.append({
                        "id": f"e_{f['id']}_{target['id']}_{rel.type}",
                        "source": f["id"],
                        "target": target["id"],
                        "label": rel.type,
                    })

            return {
                "nodes": list(nodes_dict.values()),
                "edges": edges
            }


# Singleton
neo4j_service = Neo4jService()
