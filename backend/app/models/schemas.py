"""
Pydantic Schemas for CompliSure API.
Defines all request, response, and internal data structures.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SafeguardMode(str, Enum):
    """Safeguard evaluation modes."""
    BASELINE_LLM = "baseline"
    RAG = "rag"
    RAG_THRESHOLD = "rag_threshold"
    RAG_THRESHOLD_VERIFICATION = "rag_threshold_verification"


class DecisionType(str, Enum):
    """High-level system decision."""
    ANSWER = "ANSWER"
    REFUSE = "REFUSE"


class EvidenceStatus(str, Enum):
    """Evidence grounding status."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class VerificationStatus(str, Enum):
    """Answer factual verification result."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DocStatus(str, Enum):
    """Document processing status."""
    INDEXED = "Indexed"
    PROCESSING = "Processing"
    ERROR = "Error"
    NEEDS_REVIEW = "Needs review"


# Document and Chunk Models
class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: Optional[str] = None
    chunk_index: int
    char_count: int


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: Optional[str] = None
    chunk_index: int
    text: str
    embedding: Optional[List[float]] = None


class ExtractedPage(BaseModel):
    page_number: int
    text: str
    section: Optional[str] = None
    char_count: int


class DocumentSummary(BaseModel):
    id: str
    filename: str
    title: str
    pages: int
    chunk_count: int
    status: DocStatus
    created_at: str
    file_size_bytes: int


class DocumentDetail(DocumentSummary):
    chunks: List[ChunkMetadata] = []


# Retrieval and Citation Models
class SourceCitation(BaseModel):
    document: str
    page: int
    section: Optional[str] = None
    chunk_id: str
    relevance_score: float
    snippet: Optional[str] = None


class RetrievedChunk(BaseModel):
    chunk: DocumentChunk
    relevance_score: float


# Chat Models
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User's compliance query")
    mode: Optional[SafeguardMode] = Field(
        default=None,
        description="Safeguard mode. If omitted, uses server default (rag_threshold_verification)"
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override minimum evidence relevance threshold [0.0 - 1.0]"
    )
    top_k: Optional[int] = Field(default=None, ge=1, le=20, description="Top-k chunks to retrieve")
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    decision: DecisionType
    answer: str
    evidence_status: EvidenceStatus
    sources: List[SourceCitation] = []
    verification: VerificationStatus
    refusal_reason: Optional[str] = None
    confidence_score: float = Field(..., description="Evidence-backed confidence score [0.0 - 1.0]")
    mode_used: SafeguardMode
    query_id: Optional[str] = None
    latency_ms: Optional[float] = None


class ChatHistoryItem(BaseModel):
    id: str
    timestamp: str
    question: str
    mode: SafeguardMode
    decision: DecisionType
    answer: str
    evidence_status: EvidenceStatus
    verification: VerificationStatus
    refusal_reason: Optional[str] = None
    sources: List[SourceCitation] = []
    confidence_score: float


# Safeguard Configuration Models
class SafeguardConfig(BaseModel):
    evidence_threshold: float = Field(0.75, ge=0.0, le=1.0)
    require_source_citation: bool = True
    enable_answer_verification: bool = True
    allow_unsupported_answers: bool = False
    default_mode: SafeguardMode = SafeguardMode.RAG_THRESHOLD_VERIFICATION
    top_k: int = Field(5, ge=1, le=20)
    chunk_size: int = Field(400, ge=100, le=2000)
    chunk_overlap: int = Field(50, ge=0, le=500)


# Evaluation Models
class EvaluationTestCase(BaseModel):
    id: str
    category: str  # "answerable", "unanswerable", "paraphrased", "ambiguous"
    question: str
    expected_behavior: str  # "ANSWER" or "REFUSE"
    expected_answer_summary: Optional[str] = None
    expected_document: Optional[str] = None
    expected_page: Optional[int] = None
    notes: Optional[str] = None


class EvaluationRunRequest(BaseModel):
    modes: Optional[List[SafeguardMode]] = None
    threshold: Optional[float] = None
    sample_size: Optional[int] = None


class EvaluationResultRow(BaseModel):
    method: str
    mode_key: SafeguardMode
    total_questions: int
    correct_answers: int
    wrong_answers: int
    correct_refusals: int
    false_refusals: int
    confident_wrong_answers: int
    correct_answer_rate: float
    wrong_answer_rate: float
    confident_wrong_answer_rate: float
    correct_refusal_rate: float
    false_refusal_rate: float
    citation_accuracy: float
    verification_failure_rate: float
    safety_score: float


class EvaluationCaseLog(BaseModel):
    case_id: str
    category: str
    question: str
    mode: SafeguardMode
    expected_behavior: str
    actual_decision: DecisionType
    actual_answer: str
    evidence_status: EvidenceStatus
    verification: VerificationStatus
    is_correct: bool
    is_confident_wrong_answer: bool
    relevance_scores: List[float] = []
    top_source: Optional[str] = None


class EvaluationReport(BaseModel):
    run_id: str
    timestamp: str
    test_set_size: int
    results: List[EvaluationResultRow]
    detailed_logs: List[EvaluationCaseLog]
