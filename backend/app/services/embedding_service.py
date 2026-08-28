"""
Embedding Service for CompliSure.
Produces semantic dense vector embeddings with unified Google GenAI support and deterministic local embeddings.
"""
from typing import List, Union
import zlib
import re
import numpy as np
from backend.app.config import settings
from backend.app.services.llm_client import genai_manager
from backend.app.utils.logging import logger


class EmbeddingService:
    """Computes dense vector representations for queries and document chunks."""

    def __init__(self):
        self.embedding_model = settings.EMBEDDING_MODEL

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a normalized dense vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of strings into normalized dense vectors."""
        if not texts:
            return []

        # If Google GenAI client is available and active
        if genai_manager.is_remote_active:
            try:
                client = genai_manager.client
                embeddings = []
                for text in texts:
                    clean_text = text.strip() or "empty"
                    response = client.models.embed_content(
                        model=self.embedding_model,
                        contents=clean_text
                    )
                    if hasattr(response, "embedding") and response.embedding:
                        vec = list(response.embedding.values)
                    elif hasattr(response, "embeddings") and response.embeddings:
                        vec = list(response.embeddings[0].values)
                    else:
                        vec = self._local_dense_embed(clean_text)
                    embeddings.append(self._normalize(vec))
                return embeddings
            except Exception as e:
                genai_manager.mark_remote_failed(e)

        # Local deterministic semantic dense embedding
        return [self._normalize(self._local_dense_embed(t)) for t in texts]

    def _local_dense_embed(self, text: str, dim: int = 256) -> List[float]:
        """
        Deterministic semantic dense token embedding.
        Uses stemmed tokens and subword n-grams for robust matching.
        """
        vec = np.zeros(dim, dtype=np.float32)
        clean = re.sub(r"[^\w\s]", " ", text.lower()).strip()
        raw_tokens = [t for t in clean.split() if len(t) >= 2]
        if not raw_tokens:
            return vec.tolist()

        for i, token in enumerate(raw_tokens):
            stem = re.sub(r"(?:ing|ed|es|s)$", "", token) if len(token) > 3 else token
            
            idx1 = zlib.crc32(token.encode("utf-8")) % dim
            vec[idx1] += 3.0 + len(token) * 0.5
            
            s_idx = zlib.crc32(stem.encode("utf-8")) % dim
            vec[s_idx] += 4.0

            # Bigram
            if i < len(raw_tokens) - 1:
                next_stem = re.sub(r"(?:ing|ed|es|s)$", "", raw_tokens[i+1]) if len(raw_tokens[i+1]) > 3 else raw_tokens[i+1]
                idx2 = zlib.crc32(f"{stem}_{next_stem}".encode("utf-8")) % dim
                vec[idx2] += 4.0

            # 3-char prefixes & suffixes for stem matching
            if len(token) >= 4:
                p_idx = zlib.crc32(token[:4].encode("utf-8")) % dim
                vec[p_idx] += 2.0

        return vec.tolist()

    @staticmethod
    def _normalize(vec: Union[List[float], np.ndarray]) -> List[float]:
        """Normalizes vector to unit L2 norm."""
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()


embedding_service = EmbeddingService()
