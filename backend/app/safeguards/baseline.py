"""
Mode 1: Baseline LLM.
Generates answers directly from LLM parametric weights without document retrieval.
Serves as the experimental baseline demonstrating susceptibility to confident hallucinations.
"""
import time
from backend.app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DecisionType,
    EvidenceStatus,
    VerificationStatus,
    SafeguardMode
)
from backend.app.services.answer_service import answer_service


class BaselineSafeguard:
    """Safeguard Mode 1: Pure LLM without retrieval."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        
        # Mode 1 does not retrieve or ground on documents
        answer = answer_service.generate_answer(request.question, evidence_chunks=[], is_baseline=True)
        latency = (time.time() - start_time) * 1000

        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=answer,
            evidence_status=EvidenceStatus.INSUFFICIENT,  # No evidence exists
            sources=[],
            verification=VerificationStatus.NOT_APPLICABLE,
            refusal_reason=None,
            confidence_score=0.5,  # Arbitrary baseline confidence
            mode_used=SafeguardMode.BASELINE_LLM,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


baseline_safeguard = BaselineSafeguard()
