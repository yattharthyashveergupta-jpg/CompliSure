"""
Tests for FastAPI HTTP Endpoints.
"""
import pytest
from starlette.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Tests /api/health probe."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_documents(client):
    """Tests GET /api/documents returns sample policies."""
    response = client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert isinstance(docs, list)
    assert len(docs) >= 1
    assert any("Travel" in d["title"] or "Travel" in d["filename"] for d in docs)


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
