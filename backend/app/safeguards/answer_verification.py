"""
Mode 4: RAG + Evidence Threshold + Answer Verification.
The strongest institutional safeguard:
1. Retrieves top-k chunks
2. Checks relevance against evidence threshold (gates insufficient evidence)
3. Generates grounded answer from qualifying chunks
4. Runs independent second-stage factual verification against the source passages
5. Safely refuses if the answer contains unsupported claims or fabricated citations.
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
from backend.app.services.verification_service import verification_service
from backend.app.safeguards.safe_refusal import safe_refusal_factory
from backend.app.config import settings
from backend.app.utils.logging import logger


class AnswerVerificationSafeguard:
    """Safeguard Mode 4: Two-stage Gated & Verified Grounding."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        top_k = request.top_k or settings.DEFAULT_TOP_K
        threshold = request.threshold if request.threshold is not None else settings.DEFAULT_EVIDENCE_THRESHOLD

        # Step 1: Retrieval
        retrieved_chunks = vector_store.search(request.question, top_k=top_k)

        # Step 2: Evidence Sufficiency Gate
        eval_result = evidence_service.evaluate_sufficiency(
            query=request.question,
            retrieved_chunks=retrieved_chunks,
            threshold=threshold
        )

        if not eval_result.is_sufficient:
            latency = (time.time() - start_time) * 1000
            response = safe_refusal_factory.create_insufficient_evidence_refusal(
                reason=eval_result.refusal_reason,
                mode=SafeguardMode.RAG_THRESHOLD_VERIFICATION,
                confidence=eval_result.confidence_score,
                query_id=query_id
            )
            response.latency_ms = round(latency, 2)
            return response

        # Step 3: Grounded Answer Generation
        raw_answer = answer_service.generate_answer(request.question, eval_result.qualifying_chunks)

        # Step 4: Independent Verification Stage
        verification_result = verification_service.verify_answer(
            question=request.question,
            answer=raw_answer,
            evidence_chunks=eval_result.qualifying_chunks
        )

        latency = (time.time() - start_time) * 1000

        # Step 5: Verification Gate
        if not verification_result.is_valid:
            logger.warning(
                f"Answer rejected by verification safeguard: status={verification_result.status}, "
                f"reason={verification_result.reason}"
            )
            response = safe_refusal_factory.create_verification_failed_refusal(
                reason=verification_result.reason,
                mode=SafeguardMode.RAG_THRESHOLD_VERIFICATION,
                confidence=verification_result.confidence,
                query_id=query_id
            )
            response.latency_ms = round(latency, 2)
            return response

        # Final Verified Response
        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=raw_answer,
            evidence_status=eval_result.evidence_status,
            sources=eval_result.citations,
            verification=verification_result.status,
            refusal_reason=None,
            confidence_score=round(eval_result.confidence_score * verification_result.confidence, 2),
            mode_used=SafeguardMode.RAG_THRESHOLD_VERIFICATION,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


answer_verification_safeguard = AnswerVerificationSafeguard()
