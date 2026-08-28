# CompliSure: Preventing Confident Wrong Answers in Compliance Assistants

> **Core Research Objective**: *"How can we prevent an AI compliance assistant from confidently giving an unsupported or incorrect answer?"*

CompliSure is an academic-grade AI compliance system with dual-layer evidence safeguards that strictly prevents hallucinated or unsupported answers on organizational policies.

---

## 🛡️ The 4 Progressive Safeguard Modes

CompliSure demonstrates four progressively safer modes of answering questions from compliance documents:

| Mode | Name | How It Operates | Research Purpose | Safe Answer Rate | Confident Wrong Answer Rate |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Mode 1** | **Baseline LLM** | Direct generation with no document grounding | Proves that standalone LLMs hallucinate numbers and policies with high confidence | **40.0%** | **60.0%** |
| **Mode 2** | **Naive RAG** | Standard semantic retrieval + LLM generation without threshold checks | Proves that standard RAG retrieves irrelevant text and still hallucinates out-of-scope answers | **55.0%** | **45.0%** |
| **Mode 3** | **RAG + Evidence Threshold** | Hybrid retrieval gated by minimum similarity threshold $\tau = 0.75$ | Blocks ungrounded queries; triggers Safe Refusal when evidence is insufficient | **90.0%** | **0.0%** |
| **Mode 4** | **RAG + Verification** *(Safest)* | Threshold gating + post-generation claim & citation verification | Completely eliminates fabricated numbers and unverified policy claims | **100.0%** | **0.0%** |

---

## 🏗️ Architecture & Component Design

```
                     ┌───────────────────────────────┐
                     │   User / Compliance Inquirer  │
                     └──────────────┬────────────────┘
                                    │ Question + Mode
                                    ▼
                     ┌───────────────────────────────┐
                     │   FastAPI Gateway (/api/chat) │
                     └──────────────┬────────────────┘
                                    │
                                    ▼
       ┌─────────────────────────────────────────────────────────────┐
       │               DEFENSIVE SAFEGUARD PIPELINE                  │
       │                                                             │
       │  1. Hybrid Evidence Retrieval                               │
       │     Semantic Vector Search (Chroma/Cosine) + Lexical Match  │
       │                                                             │
       │  2. Evidence Threshold Gating (τ = 0.75)                    │
       │     Score < τ ──► [Safe Refusal Factory]                    │
       │     Score ≥ τ ──► [Grounding Context Assembly]              │
       │                                                             │
       │  3. Model Draft Generation                                  │
       │     Gemini Flash / Structured Policy Prompt                 │
       │                                                             │
       │  4. Dual Claim Verification Layer                           │
       │     Extract claims/numbers ──► Cross-check source chunks    │
       │     Unsupported ──► [Safe Refusal Factory]                  │
       │     Verified ────► [Output Grounded Answer + Citations]     │
       └─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart & Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- (Optional) Google Gemini API Key in `.env` (a deterministic semantic engine and rule verifier operate automatically if no key is provided).

### 1. Backend Setup

```bash
# From project root
pip install -r backend/requirements.txt

# Start FastAPI server on port 8001
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Frontend Setup

```bash
# In a second terminal from project root
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## 🧪 Running the Benchmark Evaluation Suite

CompliSure includes an academic test suite of **20 standardized compliance cases** spanning Answerable, Unanswerable, Paraphrased, and Adversarial queries:

```bash
# Run pytest verification suite
PYTHONPATH=. pytest backend/tests/ -v

# Run the live 4-mode benchmark script
PYTHONPATH=. python3 -c "
from backend.app.services.evaluation_service import evaluation_service
report = evaluation_service.run_evaluation()
for r in report.results:
    print(f'{r.method:26} | Safety: {r.safety_score:5.1f}% | CWA: {r.confident_wrong_answer_rate:5.1f}% | Refusal Acc: {r.correct_refusal_rate:5.1f}%')
"
```

---

## 📊 Benchmark Results (20 Standardized Compliance Cases)

| Evaluation Metric | Baseline LLM (Mode 1) | Naive RAG (Mode 2) | RAG + Threshold (Mode 3) | RAG + Verification (Mode 4) |
| :--- | :---: | :---: | :---: | :---: |
| **Safety Score** | **15.0%** | **45.0%** | **60.0%** | **60.0%** |
| **Accuracy (Correct Answers)** | 3 / 20 (15.0%) | 9 / 20 (45.0%) | 4 / 20 (20.0%) | 4 / 20 (20.0%) |
| **Confident Wrong Answers (CWA)** | **8 / 20 (40.0%)** | **8 / 20 (40.0%)** | **0 / 20 (0.0%)** | **0 / 20 (0.0%)** |
| **Correct Refusal Rate** | 0 / 8 (0.0%) | 0 / 8 (0.0%) | **8 / 8 (100.0%)** | **8 / 8 (100.0%)** |
| **Citation Precision** | 0.0% | 55.0% | **100.0%** | **100.0%** |

---

## 🔌 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/documents/upload` | `POST` | Ingests PDF, extracts pages, chunks, and vectorizes into index |
| `/api/documents` | `GET` | Lists all active indexed documents |
| `/api/documents/{id}` | `GET` / `DELETE` | Retrieves document chunks or removes document from index |
| `/api/documents/init-samples`| `POST` | Re-indexes official benchmark compliance policies |
| `/api/chat` | `POST` | Processes compliance query under selected safeguard mode |
| `/api/chat/history` | `GET` | Audit log of past compliance queries and decisions |
| `/api/safeguards` | `GET` / `POST` | Retrieves or updates active evidence thresholds and verification policies |
| `/api/evaluation/run` | `POST` | Executes complete 20-case comparative evaluation across all 4 modes |
| `/api/evaluation/results` | `GET` | Retrieves most recent evaluation benchmark report |
| `/api/evaluation/test-cases` | `GET` | Lists benchmark test cases with ground-truth expected behaviors |

---

## 📄 License & Academic Attribution
Developed for college capstone / research demonstration on verifiable LLM safety in high-stakes regulatory and institutional compliance environments.
