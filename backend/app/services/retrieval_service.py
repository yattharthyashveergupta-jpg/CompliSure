"""
Vector Retrieval Service.
Provides semantic indexing and top-k retrieval over page-aware compliance chunks.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import json
import re
from pathlib import Path
from backend.app.models.schemas import DocumentChunk, RetrievedChunk
from backend.app.services.embedding_service import embedding_service
from backend.app.config import settings
from backend.app.utils.logging import logger


class VectorStore:
    """In-memory + persistent Vector Index with Cosine Similarity Search."""

    def __init__(self, storage_path: Path = settings.VECTOR_STORAGE_DIR / "vector_index.json"):
        self.storage_path = storage_path
        self.chunks: Dict[str, DocumentChunk] = {}
        self.embeddings: Dict[str, List[float]] = {}
        self._load()

    def add_chunks(self, chunks: List[DocumentChunk]):
        """Embeds and indexes a list of document chunks."""
        if not chunks:
            return

        texts = [c.text for c in chunks]
        embeddings = embedding_service.embed_batch(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
            self.chunks[chunk.chunk_id] = chunk
            self.embeddings[chunk.chunk_id] = emb

        self._save()
        logger.info(f"Indexed {len(chunks)} chunks into vector store. Total chunks: {len(self.chunks)}")

    def delete_document(self, document_id: str):
        """Removes all chunks belonging to a document."""
        to_delete = [cid for cid, chunk in self.chunks.items() if chunk.document_id == document_id]
        for cid in to_delete:
            del self.chunks[cid]
            if cid in self.embeddings:
                del self.embeddings[cid]
        self._save()
        logger.info(f"Removed {len(to_delete)} chunks for document_id '{document_id}'")

    def search(self, query: str, top_k: int = 5, document_id: Optional[str] = None) -> List[RetrievedChunk]:
        """Searches vector index and returns ranked chunks with relevance scores."""
        if not self.chunks:
            return []

        query_emb = np.array(embedding_service.embed_text(query), dtype=np.float32)

        results = []
        for chunk_id, emb_list in self.embeddings.items():
            chunk = self.chunks[chunk_id]
            if document_id and chunk.document_id != document_id:
                continue

            chunk_emb = np.array(emb_list, dtype=np.float32)
            
            # Cosine similarity for unit-normalized vectors: dot product
            dot = float(np.dot(query_emb, chunk_emb))
            cosine_sim = max(0.0, min(1.0, dot))

            # Exact lexical policy term overlap
            lexical_overlap = self._lexical_overlap(query, chunk.text)

            # High-fidelity hybrid fusion
            if lexical_overlap >= 0.50:
                lexical_score = 0.78 + (lexical_overlap - 0.50) * 0.40
            elif lexical_overlap >= 0.25:
                lexical_score = 0.55 + (lexical_overlap - 0.25) * 0.90
            elif lexical_overlap > 0:
                lexical_score = 0.25 + lexical_overlap * 1.0
            else:
                lexical_score = 0.05

            final_relevance = max(cosine_sim, lexical_score)
            final_relevance = min(0.98, max(0.05, final_relevance))

            results.append(RetrievedChunk(chunk=chunk, relevance_score=round(final_relevance, 4)))

        # Sort descending by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]

    def _lexical_overlap(self, query: str, text: str) -> float:
        """Calculates content token overlap ratio between query and text using stems."""
        stopwords = {"what", "is", "the", "for", "and", "or", "in", "at", "to", "a", "an", "of", "on", "can", "how", "many", "do", "does", "be", "with", "from"}
        q_raw = [w for w in re.findall(r"\b[a-z0-9]+\b", query.lower()) if w not in stopwords and len(w) >= 3]
        t_raw = [w for w in re.findall(r"\b[a-z0-9]+\b", text.lower()) if w not in stopwords and len(w) >= 3]
        
        if not q_raw:
            return 0.0

        q_stems = {re.sub(r"(?:ing|ed|es|s)$", "", w) for w in q_raw}
        t_stems = {re.sub(r"(?:ing|ed|es|s)$", "", w) for w in t_raw}
        
        overlap = len(q_stems.intersection(t_stems))
        return overlap / len(q_stems)

    def _save(self):
        """Persists index to disk."""
        try:
            data = {
                "chunks": [c.model_dump(exclude={"embedding"}) for c in self.chunks.values()],
                "embeddings": self.embeddings
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to persist vector index: {e}")

    def _load(self):
        """Loads index from disk if exists."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("chunks", []):
                    c = DocumentChunk(**item)
                    self.chunks[c.chunk_id] = c
                self.embeddings = data.get("embeddings", {})
            logger.info(f"Loaded {len(self.chunks)} chunks from persisted vector store.")
        except Exception as e:
            logger.warning(f"Could not load vector store from disk ({e}). Starting fresh.")


vector_store = VectorStore()
