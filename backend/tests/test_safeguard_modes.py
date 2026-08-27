"""
Tests for Safeguard Modes Comparison.
Demonstrates behavioral contrast between Baseline, Naive RAG, Threshold, and Verified modes.
"""
import pytest
from backend.app.models.schemas import ChatRequest, DecisionType, SafeguardMode
from backend.app.services.document_service import document_service
from backend.app.models.database import SessionLocal, init_db
from backend.app.safeguards.baseline import baseline_safeguard
from backend.app.safeguards.rag import rag_safeguard
from backend.app.safeguards.evidence_threshold import evidence_threshold_safeguard
from backend.app.safeguards.answer_verification import answer_verification_safeguard


@pytest.fixture(scope="module", autouse=True)
def setup_test_knowledge_base():
    """Initializes sample policies in the database for test suite."""
    init_db()
    db = SessionLocal()
    try:
        document_service.initialize_sample_documents(db)
    finally:
        db.close()


def test_mode_1_baseline_always_answers_even_unsupported():
    """Mode 1 (Baseline LLM) generates answers without grounding on documents."""
    req = ChatRequest(
        question="What is the reimbursement limit for international business class flights?",
        mode=SafeguardMode.BASELINE_LLM
    )
    res = baseline_safeguard.process(req, query_id="t1")
    assert res.decision == DecisionType.ANSWER
    assert len(res.sources) == 0  # No grounding documents


def test_mode_3_refuses_unanswerable_question():
    """Mode 3 (RAG + Evidence Threshold) safely refuses when no relevant evidence exists."""
    req = ChatRequest(
        question="Can research grants be disbursed via cryptocurrency or Bitcoin?",
        mode=SafeguardMode.RAG_THRESHOLD,
        threshold=0.75
    )
    res = evidence_threshold_safeguard.process(req, query_id="t3")
    assert res.decision == DecisionType.REFUSE
    assert "sufficient supporting evidence was not found" in res.answer or "reliably" in res.answer


def test_mode_4_answers_grounded_question_with_verified_citation():
    """Mode 4 (RAG + Verification) provides verified grounded answer with page citation."""
    req = ChatRequest(
        question="What is the maximum domestic travel reimbursement allowed?",
        mode=SafeguardMode.RAG_THRESHOLD_VERIFICATION,
        threshold=0.70
    )
    res = answer_verification_safeguard.process(req, query_id="t4")
    assert res.decision == DecisionType.ANSWER
    assert len(res.sources) > 0
    assert res.sources[0].page > 0
    assert "5,000" in res.answer or "Employee Travel Policy" in res.sources[0].document
