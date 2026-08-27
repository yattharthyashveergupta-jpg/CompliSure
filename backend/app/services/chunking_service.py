"""
Page-Aware Chunking Service.
Splits extracted document pages into semantic chunks while strictly preserving page and document metadata.
"""
from typing import List
import re
from backend.app.models.schemas import ExtractedPage, DocumentChunk
from backend.app.config import settings
from backend.app.utils.logging import logger


class ChunkingService:
    """Chunks page text into digestible passages with preserved metadata."""

    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document_pages(
        self,
        document_id: str,
        document_name: str,
        pages: List[ExtractedPage],
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> List[DocumentChunk]:
        """Splits extracted pages into page-bound metadata chunks."""
        size = chunk_size or self.chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self.chunk_overlap
        all_chunks: List[DocumentChunk] = []
        global_chunk_index = 0

        for page in pages:
            if not page.text.strip():
                continue

            page_chunks_text = self._split_page_text(page.text, size, overlap)

            for local_idx, chunk_text in enumerate(page_chunks_text):
                clean_chunk = chunk_text.strip()
                if len(clean_chunk) < 15:  # Skip tiny fragments
                    continue

                chunk_id = f"{document_id}_p{page.page_number}_c{local_idx}"
                
                # Check for localized section title within chunk
                chunk_section = page.section or self._extract_subheading(clean_chunk)

                all_chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_name=document_name,
                        page_number=page.page_number,
                        section=chunk_section,
                        chunk_index=global_chunk_index,
                        text=clean_chunk
                    )
                )
                global_chunk_index += 1

        logger.info(f"Chunked document '{document_name}' into {len(all_chunks)} page-aware chunks.")
        return all_chunks

    def _split_page_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Splits text by paragraphs, then sentences, respecting boundaries."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)

            # If a single paragraph is larger than chunk_size, split by sentences
            if para_len > chunk_size:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    if current_len + len(sentence) > chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        # Keep overlap if possible
                        if chunk_overlap > 0 and len(current_chunk) > 1:
                            current_chunk = current_chunk[-1:]
                            current_len = sum(len(s) for s in current_chunk) + len(current_chunk)
                        else:
                            current_chunk = []
                            current_len = 0
                    current_chunk.append(sentence)
                    current_len += len(sentence) + 1
            else:
                if current_len + para_len > chunk_size and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [para]
                    current_len = para_len
                else:
                    current_chunk.append(para)
                    current_len += para_len + 2

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    def _extract_subheading(self, text: str) -> str:
        """Finds any bold/numbered subheading inside the chunk."""
        match = re.search(r"^(?:[\d\.]+\s+|Section\s+\d+:?\s*)([A-Za-z\s]{3,35})", text, re.MULTILINE)
        if match:
            return match.group(0).strip()
        return "General Policy"


chunking_service = ChunkingService()
