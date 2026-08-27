"""
Mode 3: RAG + Evidence Threshold.
Retrieves top-k passages, calculates similarity, and enforces a strict evidence sufficiency threshold.
Refuses immediately when retrieved evidence score is below threshold.
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
from backend.app.services.retrieval_service import vector_store
from backend.app.services.evidence_service import evidence_service
from backend.app.services.answer_service import answer_service
from backend.app.safeguards.safe_refusal import safe_refusal_factory
from backend.app.config import settings


class EvidenceThresholdSafeguard:
    """Safeguard Mode 3: RAG with Evidence Threshold Gating."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        top_k = request.top_k or settings.DEFAULT_TOP_K
        threshold = request.threshold if request.threshold is not None else settings.DEFAULT_EVIDENCE_THRESHOLD

        # 1. Retrieve chunks
        retrieved_chunks = vector_store.search(request.question, top_k=top_k)

        # 2. Evaluate evidence sufficiency
        eval_result = evidence_service.evaluate_sufficiency(
            query=request.question,
            retrieved_chunks=retrieved_chunks,
            threshold=threshold
        )

        latency = (time.time() - start_time) * 1000

        # 3. Gate: if evidence insufficient, refuse!
        if not eval_result.is_sufficient:
            response = safe_refusal_factory.create_insufficient_evidence_refusal(
                reason=eval_result.refusal_reason,
                mode=SafeguardMode.RAG_THRESHOLD,
                confidence=eval_result.confidence_score,
                query_id=query_id
            )
            response.latency_ms = round(latency, 2)
            return response

        # 4. Generate grounded answer
        answer = answer_service.generate_answer(request.question, eval_result.qualifying_chunks)

        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=answer,
            evidence_status=eval_result.evidence_status,
            sources=eval_result.citations,
            verification=VerificationStatus.NOT_APPLICABLE,  # Verification not active in Mode 3
            refusal_reason=None,
            confidence_score=eval_result.confidence_score,
            mode_used=SafeguardMode.RAG_THRESHOLD,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


evidence_threshold_safeguard = EvidenceThresholdSafeguard()
