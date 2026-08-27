"""
PDF Ingestion Service using PyMuPDF (fitz).
Extracts text page-by-page, preserving exact page numbers and document structure.
"""
from typing import List, Optional
import fitz  # PyMuPDF
import re
from pathlib import Path
from backend.app.models.schemas import ExtractedPage
from backend.app.utils.logging import logger


class PDFProcessingError(Exception):
    """Raised when PDF extraction or validation fails."""
    pass


class PDFService:
    """Handles PDF validation and page-by-page text extraction."""

    @staticmethod
    def extract_pages_from_bytes(file_bytes: bytes, filename: str) -> List[ExtractedPage]:
        """Extracts text page by page from raw PDF bytes."""
        if not file_bytes:
            raise PDFProcessingError(f"PDF file '{filename}' is empty (0 bytes).")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Failed to open PDF stream for {filename}: {e}")
            raise PDFProcessingError(f"Invalid or corrupted PDF file: {str(e)}")

        return PDFService._process_fitz_doc(doc, filename)

    @staticmethod
    def extract_pages_from_file(file_path: Path) -> List[ExtractedPage]:
        """Extracts text page by page from a PDF file path."""
        if not file_path.exists():
            raise PDFProcessingError(f"File not found at path: {file_path}")

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            logger.error(f"Failed to open PDF at {file_path}: {e}")
            raise PDFProcessingError(f"Invalid or unreadable PDF file: {str(e)}")

        return PDFService._process_fitz_doc(doc, file_path.name)

    @staticmethod
    def _process_fitz_doc(doc: fitz.Document, filename: str) -> List[ExtractedPage]:
        """Internal helper to iterate pages and extract text with section hints."""
        try:
            if doc.page_count == 0:
                raise PDFProcessingError(f"PDF '{filename}' contains 0 pages.")

            pages: List[ExtractedPage] = []
            current_section = None

            for page_idx in range(doc.page_count):
                page = doc.load_page(page_idx)
                text = page.get_text("text")
                clean_text = text.strip()

                # Try to extract section title if present in top lines
                section_candidate = PDFService._detect_section(clean_text)
                if section_candidate:
                    current_section = section_candidate

                pages.append(
                    ExtractedPage(
                        page_number=page_idx + 1,  # 1-indexed for citations
                        text=clean_text,
                        section=current_section,
                        char_count=len(clean_text)
                    )
                )

            total_chars = sum(p.char_count for p in pages)
            if total_chars == 0:
                logger.warning(f"PDF '{filename}' has {doc.page_count} pages but no extractable text (might be scanned images).")

            logger.info(f"Successfully extracted {len(pages)} pages ({total_chars} chars) from '{filename}'")
            return pages

        finally:
            doc.close()

    @staticmethod
    def _detect_section(text: str) -> Optional[str]:
        """Detects section heading from top lines of a page."""
        if not text:
            return None
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:3]:
            # Common policy header patterns: e.g. "Section 4. Travel Expenses" or "4. Reimbursement Policy"
            if re.match(r"^(Section\s+\d+|[\d\.]+\s+[A-Z][A-Za-z\s]{3,40}|[A-Z\s]{4,35})$", line):
                return line
        return None


pdf_service = PDFService()
