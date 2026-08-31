"""
Qdrant Vector Database Service — manages vector index for code search & RAG.
Stores embeddings for code chunks, docstrings, classes, and READMEs.
"""
import logging
import uuid
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings
from app.embeddings.embedding_service import embedding_service

logger = logging.getLogger(__name__)

COLLECTION_NAME = "codebase_chunks"
VECTOR_DIM = 1536


class VectorService:
    def __init__(self):
        self._client: Optional[QdrantClient] = None

    def get_client(self) -> Optional[QdrantClient]:
        if self._client is None:
            try:
                self._client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    timeout=10,
                )
                self._ensure_collection()
                logger.info(f"Connected to Qdrant at {settings.qdrant_host}:{settings.qdrant_port}")
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant: {e}")
                self._client = None
        return self._client

    def _ensure_collection(self):
        if not self._client:
            return
        try:
            collections = [c.name for c in self._client.get_collections().collections]
            if COLLECTION_NAME not in collections:
                self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=VECTOR_DIM,
                        distance=models.Distance.COSINE,
                    )
                )
                logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
        except Exception as e:
            logger.warning(f"Failed to verify/create Qdrant collection: {e}")

    # ── Indexing ──────────────────────────────────────────────────

    def index_chunks(self, repo_id: str, chunks: List[Dict[str, Any]]):
        """
        Index code chunks into Qdrant for a repository.
        Each chunk is a dict: { content, file_path, line_start, line_end, chunk_type, name }
        """
        client = self.get_client()
        if not client or not chunks:
            return

        # 1. Delete existing vectors for this repo
        try:
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="repo_id",
                                match=models.MatchValue(value=repo_id)
                            )
                        ]
                    )
                )
            )
        except Exception:
            pass

        # 2. Generate embeddings in batches of 50
        batch_size = 50
        points = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["content"] for c in batch]
            vectors = embedding_service.embed_batch(texts)

            for item, vec in zip(batch, vectors):
                point_id = str(uuid.uuid4())
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vec,
                        payload={
                            "repo_id": repo_id,
                            "file_path": item["file_path"],
                            "content": item["content"][:2000],  # cap stored text
                            "line_start": item.get("line_start", 1),
                            "line_end": item.get("line_end", 1),
                            "chunk_type": item.get("chunk_type", "code"),
                            "name": item.get("name", ""),
                        }
                    )
                )

        # 3. Upsert to Qdrant
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Indexed {len(points)} vector chunks into Qdrant for repo {repo_id}")
        except Exception as e:
            logger.warning(f"Qdrant upsert failed: {e}")

    # ── Vector Search ─────────────────────────────────────────────

    def search(self, repo_id: str, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search code database using semantic vector similarity.
        """
        client = self.get_client()
        if not client:
            return []

        query_vec = embedding_service.embed_text(query)

        try:
            res = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vec,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="repo_id",
                            match=models.MatchValue(value=repo_id)
                        )
                    ]
                ),
                limit=top_k,
            )

            results = []
            for hit in res:
                results.append({
                    "score": round(hit.score, 4),
                    "file_path": hit.payload.get("file_path"),
                    "content": hit.payload.get("content"),
                    "line_start": hit.payload.get("line_start"),
                    "line_end": hit.payload.get("line_end"),
                    "chunk_type": hit.payload.get("chunk_type"),
                    "name": hit.payload.get("name"),
                })
            return results
        except Exception as e:
            logger.warning(f"Qdrant search query failed: {e}")
            return []


# Singleton
vector_service = VectorService()
