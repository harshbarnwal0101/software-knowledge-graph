"""
Embedding Service — generates vector embeddings for code chunks and documentation.
Uses OpenAI or OpenAI-compatible embedding API, with a fallback vector generator.
"""
import logging
from typing import List
import math

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self._client = None
        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                )
                logger.info("Initialized OpenAI embedding client.")
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")
                self._client = None

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text string."""
        vectors = self.embed_batch([text])
        return vectors[0] if vectors else self._fallback_vector(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of strings."""
        if not texts:
            return []

        if self._client:
            try:
                # Sanitize texts (max ~8k chars per string to avoid token limits)
                clean_texts = [t[:8000].replace("\0", "") for t in texts]
                res = self._client.embeddings.create(
                    model=settings.embedding_model,
                    input=clean_texts
                )
                return [d.embedding for d in res.data]
            except Exception as e:
                logger.warning(f"OpenAI embedding call failed: {e}. Using deterministic vector fallback.")

        # Fallback vector generator (1536 dims)
        return [self._fallback_vector(t) for t in texts]

    def _fallback_vector(self, text: str, dim: int = 1536) -> List[float]:
        """
        Deterministic pseudo-embedding for testing without active OpenAI API keys.
        Produces consistent normalized vectors derived from string hash.
        """
        vec = []
        seed = sum(ord(c) for c in text[:200])
        for i in range(dim):
            val = math.sin(seed * (i + 1) * 0.1)
            vec.append(val)

        # Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


# Singleton
embedding_service = EmbeddingService()
