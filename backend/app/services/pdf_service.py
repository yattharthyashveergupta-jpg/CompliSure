"""
Document Text Extraction Service.
Extracts text page-by-page from PDFs and plain text files, preserving exact page numbers and document structure.
"""
from typing import List, Optional
import re
from pathlib import Path
from backend.app.models.schemas import ExtractedPage
from backend.app.utils.logging import logger

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None


class PDFProcessingError(Exception):
    """Raised when document extraction or validation fails."""
    pass


class PDFService:
    """Handles PDF/document validation and page-by-page text extraction."""

    @staticmethod
    def extract_pages_from_bytes(file_bytes: bytes, filename: str) -> List[ExtractedPage]:
        """Extracts text page by page from raw document bytes."""
        if not file_bytes or len(file_bytes) == 0:
            raise PDFProcessingError(f"Document file '{filename}' is empty (0 bytes).")

        lower_name = filename.lower()
        if lower_name.endswith(".txt") or lower_name.endswith(".md"):
            return PDFService._extract_from_text_bytes(file_bytes, filename)

        if not fitz:
            raise PDFProcessingError("PyMuPDF engine is not available for PDF processing.")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Failed to open PDF stream for {filename}: {e}")
            raise PDFProcessingError(f"Invalid or corrupted PDF file: {str(e)}")

        return PDFService._process_fitz_doc(doc, filename)

    @staticmethod
    def extract_pages_from_file(file_path: Path) -> List[ExtractedPage]:
        """Extracts text page by page from a file path."""
        if not file_path.exists():
            raise PDFProcessingError(f"File not found at path: {file_path}")

        file_bytes = file_path.read_bytes()
        return PDFService.extract_pages_from_bytes(file_bytes, file_path.name)

    @staticmethod
    def _extract_from_text_bytes(file_bytes: bytes, filename: str) -> List[ExtractedPage]:
        """Handles plain text / markdown files by paginating by character budget."""
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                raise PDFProcessingError(f"Failed to decode text document '{filename}': {e}")

        clean_text = text.strip()
        if not clean_text:
            raise PDFProcessingError(f"Document '{filename}' contains no readable text content.")

        # Paginate roughly ~2000 chars per page
        page_size = 2000
        paragraphs = clean_text.split("\n\n")
        pages: List[ExtractedPage] = []
        current_page_text = []
        current_len = 0
        page_num = 1

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_len + len(para) > page_size and current_page_text:
                full_page_str = "\n\n".join(current_page_text)
                pages.append(
                    ExtractedPage(
                        page_number=page_num,
                        text=full_page_str,
                        section=PDFService._detect_section(full_page_str),
                        char_count=len(full_page_str)
                    )
                )
                page_num += 1
                current_page_text = [para]
                current_len = len(para)
            else:
                current_page_text.append(para)
                current_len += len(para) + 2

        if current_page_text:
            full_page_str = "\n\n".join(current_page_text)
            pages.append(
                ExtractedPage(
                    page_number=page_num,
                    text=full_page_str,
                    section=PDFService._detect_section(full_page_str),
                    char_count=len(full_page_str)
                )
            )

        return pages

    @staticmethod
    def _process_fitz_doc(doc, filename: str) -> List[ExtractedPage]:
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
                logger.warning(f"PDF '{filename}' has {doc.page_count} pages but no extractable text.")

            logger.info(f"Extracted {len(pages)} pages ({total_chars} chars) from '{filename}'")
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
            if re.match(r"^(Section\s+\d+|[\d\.]+\s+[A-Z][A-Za-z\s]{3,40}|[A-Z\s]{4,35})$", line):
                return line
        return None


pdf_service = PDFService()
