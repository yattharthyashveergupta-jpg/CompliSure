# CompliSure Backend & AI Safeguards Engine

> **Academic Project Title**: *Preventing Confident Wrong Answers in Compliance Assistants*  
> **Core Operating Principle**: *Answer when evidence exists. Refuse when evidence is insufficient.*

---

## 1. Executive Overview

Compliance assistants operating in regulated sectors (finance, healthcare, legal, higher education governance) cannot afford ungrounded hallucinations or fabricated assertions. Standard Large Language Models (LLMs) and naive Retrieval-Augmented Generation (RAG) systems frequently generate **Confident Wrong Answers (CWA)** when asked questions not covered by the underlying source documents.

**CompliSure** is a modular, production-grade backend and AI safeguards engine designed to eliminate confident wrong answers through a multi-stage evidence verification architecture:

1. **PDF Ingestion & Page Extraction**: Uses PyMuPDF (`fitz`) to extract structured text while strictly preserving 1-indexed page numbers.
2. **Page-Aware Chunking**: Splits document pages into semantic chunks that retain document identity, page numbers, section headers, and chunk indices.
3. **Semantic Retrieval**: Normalizes vector embeddings and ranks passages using cosine similarity with lexical grounding.
4. **Evidence Sufficiency Gating**: Assesses whether retrieved chunks exceed a calibrated relevance threshold. If evidence is insufficient, the system safely refuses to answer.
5. **Grounded Generation**: Prompts Google Gemini with strict zero-hallucination instructions and explicit evidence constraints.
6. **Two-Stage Factual Verification**: An independent verifier audits generated claims against source text to detect and reject ungrounded figures or hallucinated citations.
7. **Empirical Benchmarking & Evaluation**: Provides an automated test framework computing 8 compliance metrics across 4 experimental safeguard modes.

---

## 2. Architecture & Safeguard Modes

CompliSure implements 4 distinct operational modes for academic experimentation:

| Safeguard Mode | Pipeline Flow | Behavior on Unanswerable Queries | Confident Wrong Answer Risk |
| :--- | :--- | :--- | :--- |
| **Mode 1: Baseline LLM** | Question → LLM → Output | Invents plausible but unverified policy rules | **Critical (High)** |
| **Mode 2: Standard RAG** | Question → Retrieval → LLM → Output | Answers unconditionally using low-relevance passages | **Substantial (Moderate-High)** |
| **Mode 3: RAG + Evidence Threshold** | Question → Retrieval → **Threshold Gate** → LLM / Safe Refusal | **Safely Refuses** when top relevance score < threshold | **Low** |
| **Mode 4: RAG + Verification** | Question → Retrieval → **Threshold Gate** → LLM → **Verification Auditor** → Final Grounded Answer / Refusal | **Safely Refuses** if evidence is insufficient OR answer contains unverified claims | **Zero / Negligible** |

---

## 3. Directory Layout

```
backend/
├── app/
│   ├── api/                     # FastAPI Route Endpoints
│   │   ├── chat.py              # /api/chat & audit history
│   │   ├── documents.py         # /api/documents (upload, list, detail, delete)
│   │   ├── evaluation.py        # /api/evaluation/run & /api/evaluation/results
│   │   └── safeguards.py        # /api/safeguards configuration
│   ├── config.py                # Environment-driven settings (pydantic-settings)
│   ├── main.py                  # FastAPI Application Entry Point & Lifespan
│   ├── models/
│   │   ├── database.py          # SQLAlchemy SQLite Models & Session Management
│   │   └── schemas.py           # Pydantic v2 API Data Contracts & Enums
│   ├── safeguards/              # 4 Experimental Safeguard Implementations
│   │   ├── baseline.py          # Mode 1: Baseline LLM
│   │   ├── rag.py               # Mode 2: Standard Naive RAG
│   │   ├── evidence_threshold.py# Mode 3: RAG + Relevance Threshold Gating
│   │   ├── answer_verification.py # Mode 4: Two-Stage Verification
│   │   └── safe_refusal.py      # Standardized Safe Refusal Generators
│   ├── services/
│   │   ├── answer_service.py    # Grounded Gemini Generation Engine
│   │   ├── chunking_service.py  # Page-Aware Passage Splitter
│   │   ├── document_service.py  # Document Lifecycle & Sample Policy Initializer
│   │   ├── embedding_service.py # Vector Embeddings (Gemini + Local Dense Fallback)
│   │   ├── evaluation_service.py# Benchmark Experiment Runner & Metrics Engine
│   │   ├── pdf_service.py       # PyMuPDF Page Text Extractor
│   │   ├── retrieval_service.py # Vector Store & Cosine Search Index
│   │   └── verification_service.py # Second-stage NLI & Claim Verifier
│   └── utils/
│       └── logging.py           # Structured Audit Logger
├── data/                        # Persistent SQLite DB, Vector Index, & PDF Storage
├── requirements.txt             # Python Dependencies Manifest
└── tests/                       # Pytest Automated Test Suite
    ├── test_api_endpoints.py
    ├── test_chunking_service.py
    ├── test_pdf_service.py
    ├── test_retrieval_and_threshold.py
    ├── test_safeguard_modes.py
    └── test_verification_and_refusal.py
```

---

## 4. API Endpoints Reference

### Chat & Query Processing
- `POST /api/chat`: Submit a compliance question with safeguard mode and parameters.
- `GET /api/chat/history`: Retrieve recent query audit history and provenance logs.

### Document Management
- `POST /api/documents/upload`: Upload and index a compliance PDF file.
- `GET /api/documents`: List all indexed compliance documents with metadata.
- `GET /api/documents/{id}`: View document details and individual page-aware chunks.
- `DELETE /api/documents/{id}`: Remove document, SQLite records, and vector indices.
- `POST /api/documents/init-samples`: Seed or reset default sample compliance documents.

### Safeguard Configuration
- `GET /api/safeguards`: Retrieve current evidence thresholds and active flags.
- `POST /api/safeguards/configure`: Update evidence thresholds, top-k, and verification rules.

### Evaluation & Academic Benchmarking
- `POST /api/evaluation/run`: Execute benchmark dataset across safeguard modes.
- `GET /api/evaluation/results`: Fetch the latest comparative evaluation report.
- `GET /api/evaluation/test-cases`: List all 20 benchmark test cases.

---

## 5. Running the Backend & Test Suite

### Running the FastAPI Server:
```bash
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running the Automated Pytest Suite:
```bash
python3 -m pytest backend/tests -v
```
