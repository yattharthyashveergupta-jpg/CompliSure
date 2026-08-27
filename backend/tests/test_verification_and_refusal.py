"""
Tests for Verification and Safe Refusal Logic.
"""
from backend.app.services.verification_service import VerificationService
from backend.app.safeguards.safe_refusal import SafeRefusalFactory
from backend.app.models.schemas import (
    DocumentChunk,
    RetrievedChunk,
    VerificationStatus,
    DecisionType
)


def test_verification_rejects_hallucinated_amounts():
    """Confirms that the verifier flags answers with numbers not present in source text."""
    verifier = VerificationService()
    
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        document_name="Travel Policy.pdf",
        page_number=4,
        section="Limits",
        chunk_index=0,
        text="Domestic travel reimbursement is capped at ₹5,000 per trip."
    )
    retrieved = [RetrievedChunk(chunk=chunk, relevance_score=0.9)]
    
    # Answer hallucinates $25,000 instead of 5,000
    fake_answer = "Employees can claim up to ₹25,000 per trip."
    
    res = verifier.verify_answer(
        question="What is the travel reimbursement limit?",
        answer=fake_answer,
        evidence_chunks=retrieved
    )
    
    assert res.status == VerificationStatus.UNSUPPORTED
    assert res.is_valid is False
    assert len(res.unsupported_claims) > 0


def test_verification_passes_grounded_answer():
    """Confirms that properly cited and grounded answers pass verification."""
    verifier = VerificationService()
    
    chunk = DocumentChunk(
        chunk_id="c1",
        document_id="d1",
        document_name="Security Policy.pdf",
        page_number=1,
        section="Passwords",
        chunk_index=0,
        text="All system passwords must contain a minimum of 12 characters and expire every 90 days."
    )
    retrieved = [RetrievedChunk(chunk=chunk, relevance_score=0.95)]
    
    valid_answer = "According to Security Policy.pdf, passwords must be at least 12 characters and expire in 90 days."
    
    res = verifier.verify_answer(
        question="What is the password requirement?",
        answer=valid_answer,
        evidence_chunks=retrieved
    )
    
    assert res.status in (VerificationStatus.SUPPORTED, VerificationStatus.PARTIALLY_SUPPORTED)


def test_safe_refusal_factory():
    """Verifies that refusal factory produces compliant refusal payloads."""
    refusal = SafeRefusalFactory.create_insufficient_evidence_refusal(
        reason="No chunks above threshold",
        query_id="q_refuse_test"
    )
    assert refusal.decision == DecisionType.REFUSE
    assert "sufficient supporting evidence was not found" in refusal.answer
    assert refusal.query_id == "q_refuse_test"
    assert len(refusal.sources) == 0
