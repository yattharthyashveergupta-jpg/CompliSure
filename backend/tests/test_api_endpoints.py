"""
Tests for FastAPI HTTP Endpoints.
Covers health, documents, chat, safeguards, evaluations, and audit logs.
"""
import io
import pytest
from starlette.testclient import TestClient
from reportlab.pdfgen import canvas
from backend.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Tests /api/health probe."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "active_model" in data


def test_list_documents(client):
    """Tests GET /api/documents returns sample policies."""
    response = client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) >= 1
    assert any("Travel" in d["title"] or "Travel" in d["filename"] for d in docs)


def test_document_detail_and_chunks(client):
    """Tests GET /api/documents/{id} returns full metadata and chunks."""
    docs = client.get("/api/documents").json()
    assert len(docs) > 0
    doc_id = docs[0]["id"]

    res = client.get(f"/api/documents/{doc_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == doc_id
    assert "chunks" in detail
    assert len(detail["chunks"]) > 0


def test_upload_custom_pdf(client):
    """Tests POST /api/documents/upload with in-memory generated PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "ACADEMIC INTEGRITY POLICY")
    c.drawString(100, 720, "Section 1. Plagiarism Rule")
    c.drawString(100, 700, "All submitted work must be original. Plagiarism incurs immediate course failure.")
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    files = {"file": ("Academic_Integrity.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/api/documents/upload", files=files)
    assert response.status_code == 201
    doc_summary = response.json()
    assert doc_summary["filename"] == "Academic_Integrity.pdf"
    assert doc_summary["pages"] == 1
    assert doc_summary["chunk_count"] >= 1

    # Cleanup uploaded document
    del_res = client.delete(f"/api/documents/{doc_summary['id']}")
    assert del_res.status_code == 200


def test_chat_grounded_answer(client):
    """Tests POST /api/chat with answerable question."""
    payload = {
        "question": "What is the domestic travel reimbursement limit?",
        "mode": "rag_threshold_verification"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] in ("ANSWER", "REFUSE")
    if data["decision"] == "ANSWER":
        assert len(data["sources"]) > 0
        assert data["sources"][0]["page"] > 0


def test_chat_unanswerable_refusal(client):
    """Tests POST /api/chat with unanswerable query."""
    payload = {
        "question": "What is the policy for astronaut space travel reimbursement?",
        "mode": "rag_threshold_verification",
        "threshold": 0.80
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "REFUSE"
    assert "reliable" in data["answer"].lower() or "evidence" in data["answer"].lower()


def test_chat_history_audit(client):
    """Tests GET /api/chat/history retrieving query audit logs."""
    # Send a query
    client.post("/api/chat", json={"question": "What is the password policy?", "mode": "rag_threshold_verification"})
    
    res = client.get("/api/chat/history?limit=10")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert "question" in logs[0]
    assert "decision" in logs[0]


def test_safeguards_configuration(client):
    """Tests GET and POST /api/safeguards."""
    # Get config
    get_res = client.get("/api/safeguards")
    assert get_res.status_code == 200
    config = get_res.json()
    assert "evidence_threshold" in config

    # Update config
    update_payload = config.copy()
    update_payload["evidence_threshold"] = 0.82
    post_res = client.post("/api/safeguards/configure", json=update_payload)
    assert post_res.status_code == 200
    assert post_res.json()["evidence_threshold"] == 0.82

    # Reset
    update_payload["evidence_threshold"] = 0.75
    client.post("/api/safeguards/configure", json=update_payload)


def test_evaluation_benchmark_cases(client):
    """Tests GET /api/evaluation/test-cases and alias /api/evaluation/benchmark-cases."""
    response = client.get("/api/evaluation/test-cases")
    assert response.status_code == 200
    cases = response.json()
    assert isinstance(cases, list)
    assert len(cases) >= 5
    assert any(c["category"].lower() in ("unanswerable", "adversarial_unsupported", "insufficient_evidence") for c in cases)
    assert any(c["category"].lower() in ("answerable", "grounded_answerable") for c in cases)


def test_evaluation_run(client):
    """Tests POST /api/evaluation/run benchmark execution."""
    payload = {
        "modes": ["rag_threshold", "rag_threshold_verification"]
    }
    response = client.post("/api/evaluation/run", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert "results" in report
    assert len(report["results"]) == 2
    assert "test_set_size" in report
    assert report["test_set_size"] >= 5
