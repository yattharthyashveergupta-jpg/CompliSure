"""
Tests for PDF Extraction and Validation Service.
"""
import pytest
from backend.app.services.pdf_service import PDFService, PDFProcessingError
from backend.app.services.document_service import document_service


def test_pdf_extraction_valid_document():
    """Verifies that PyMuPDF correctly extracts text and preserves 1-indexed page numbers."""
    pages_content = [
        "Section 1. Travel Rules\n\nEmployees traveling for official work are covered under this policy.",
        "Section 2. Reimbursement Limit\n\nDomestic travel is reimbursable up to ₹5,000 per trip."
    ]
    pdf_bytes = document_service._create_sample_pdf_bytes("Test Policy.pdf", pages_content)
    
    extracted_pages = PDFService.extract_pages_from_bytes(pdf_bytes, "Test Policy.pdf")
    
    assert len(extracted_pages) == 2
    assert extracted_pages[0].page_number == 1
    assert extracted_pages[1].page_number == 2
    assert "Section 1" in extracted_pages[0].text or "Travel Rules" in extracted_pages[0].text
    assert "5,000" in extracted_pages[1].text
    assert extracted_pages[0].char_count > 0


def test_pdf_empty_bytes_raises_error():
    """Ensures empty byte input is rejected safely."""
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.extract_pages_from_bytes(b"", "empty.pdf")
    assert "is empty" in str(exc_info.value)


def test_pdf_corrupted_bytes_raises_error():
    """Ensures malformed or corrupted files fail with structured exception."""
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.extract_pages_from_bytes(b"NOT A VALID PDF HEADER", "corrupt.pdf")
    assert "Invalid or corrupted PDF" in str(exc_info.value)
