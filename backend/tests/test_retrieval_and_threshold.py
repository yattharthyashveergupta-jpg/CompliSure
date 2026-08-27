"""
Tests for Vector Retrieval and Evidence Threshold Gating.
"""
from backend.app.services.retrieval_service import VectorStore
from backend.app.services.evidence_service import EvidenceService
from backend.app.models.schemas import DocumentChunk, RetrievedChunk, DecisionType, EvidenceStatus


def test_vector_store_retrieval_ranking(tmp_path):
    """Verifies that vector search ranks the most semantically relevant passage highest."""
    store = VectorStore(storage_path=tmp_path / "test_index.json")
    
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            document_id="doc1",
            document_name="Travel Policy.pdf",
            page_number=4,
            section="Reimbursement",
            chunk_index=0,
            text="Employees may claim travel reimbursement up to ₹5,000 per trip for domestic travel."
        ),
        DocumentChunk(
            chunk_id="c2",
            document_id="doc2",
            document_name="Security Policy.pdf",
            page_number=1,
            section="Passwords",
            chunk_index=1,
            text="All system accounts must use multi-factor authentication and passwords must be at least 12 characters."
        )
    ]
    store.add_chunks(chunks)
    
    # Query matching chunk 1
    results_travel = store.search("What is the maximum reimbursement for travel?", top_k=2)
    assert len(results_travel) == 2
    assert results_travel[0].chunk.chunk_id == "c1"
    assert results_travel[0].relevance_score > results_travel[1].relevance_score

    # Query matching chunk 2
    results_sec = store.search("What is the required password length for security?", top_k=2)
    assert results_sec[0].chunk.chunk_id == "c2"


def test_evidence_threshold_gating():
    """Confirms that below-threshold evidence results in REFUSE decision."""
    evi_svc = EvidenceService()
    
    # Case 1: High relevance evidence (meets threshold)
    c1 = DocumentChunk(
        chunk_id="c1",
        document_id="doc1",
        document_name="Travel Policy.pdf",
        page_number=4,
        section="Travel Limits",
        chunk_index=0,
        text="Travel reimbursement limit is ₹5,000 per trip."
    )
    retrieved_high = [
        RetrievedChunk(chunk=c1, relevance_score=0.92)
    ]
    res_high = evi_svc.evaluate_sufficiency("travel reimbursement", retrieved_high, threshold=0.75)
    assert res_high.is_sufficient is True
    assert res_high.decision == DecisionType.ANSWER
    assert res_high.evidence_status == EvidenceStatus.HIGH
    assert len(res_high.citations) == 1

    # Case 2: Low relevance evidence (unrelated question below threshold)
    retrieved_low = [
        RetrievedChunk(chunk=c1, relevance_score=0.42)
    ]
    res_low = evi_svc.evaluate_sufficiency("cryptocurrency disbursement policy", retrieved_low, threshold=0.75)
    assert res_low.is_sufficient is False
    assert res_low.decision == DecisionType.REFUSE
    assert res_low.evidence_status in (EvidenceStatus.LOW, EvidenceStatus.INSUFFICIENT)
    assert "No sufficiently relevant" in res_low.refusal_reason or "threshold" in res_low.refusal_reason
