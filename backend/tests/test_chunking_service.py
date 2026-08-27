"""
Tests for Page-Aware Chunking Service.
"""
from backend.app.services.chunking_service import ChunkingService
from backend.app.models.schemas import ExtractedPage


def test_chunking_preserves_page_metadata():
    """Confirms that all created chunks strictly retain page_number and document_id."""
    chunker = ChunkingService(chunk_size=150, chunk_overlap=20)
    
    pages = [
        ExtractedPage(page_number=1, text="First paragraph on page 1.\n\nSecond paragraph on page 1 with more details.", char_count=70),
        ExtractedPage(page_number=2, text="Third paragraph on page 2 describing Section 4.", char_count=45)
    ]
    
    chunks = chunker.chunk_document_pages(
        document_id="doc_123",
        document_name="Test Doc.pdf",
        pages=pages
    )
    
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.document_id == "doc_123"
        assert chunk.document_name == "Test Doc.pdf"
        assert chunk.page_number in (1, 2)
        assert chunk.chunk_id.startswith("doc_123_p")
        assert len(chunk.text) > 0


def test_chunking_avoids_empty_text():
    """Ensures blank pages do not produce invalid chunks."""
    chunker = ChunkingService()
    pages = [ExtractedPage(page_number=1, text="   \n\n   ", char_count=0)]
    chunks = chunker.chunk_document_pages("doc_empty", "Empty.pdf", pages)
    assert len(chunks) == 0
