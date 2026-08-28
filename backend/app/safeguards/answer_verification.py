"""
Mode 4: RAG with Evidence Threshold and Independent Answer Verification.
The primary and most robust safeguard in CompliSure:
1. Gated by evidence sufficiency threshold.
2. Generates grounded answer with source citations.
3. Performs second-stage factual verification against retrieved text.
4. Safely refuses to answer if verification fails or unsupported claims are detected.
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


class AnswerVerificationSafeguard:
    """Safeguard Mode 4: RAG + Evidence Threshold + Second-Stage Verification."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        threshold = request.threshold if request.threshold is not None else settings.DEFAULT_EVIDENCE_THRESHOLD
        top_k = request.top_k or settings.DEFAULT_TOP_K
        min_chunks = request.min_supporting_chunks or settings.MIN_SUPPORTING_CHUNKS
        allow_unsupported = request.allow_unsupported_answers if request.allow_unsupported_answers is not None else settings.ALLOW_UNSUPPORTED_ANSWERS
        require_citation = request.require_source_citation if request.require_source_citation is not None else settings.REQUIRE_SOURCE_CITATION
        enable_verification = request.enable_answer_verification if request.enable_answer_verification is not None else settings.ENABLE_ANSWER_VERIFICATION

        # Stage 1: Retrieval
        retrieved_chunks = vector_store.search(request.question, top_k=top_k)

        # Stage 2: Evidence Threshold Gate
        sufficiency = evidence_service.evaluate_sufficiency(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
            threshold=threshold,
            min_supporting_chunks=min_chunks
        )

        if not sufficiency.is_sufficient:
            if not allow_unsupported:
                refusal = safe_refusal_factory.create_insufficient_evidence_refusal(
                    reason=sufficiency.refusal_reason or "Evidence below sufficiency threshold.",
                    query_id=query_id
                )
                refusal.mode_used = SafeguardMode.RAG_THRESHOLD_VERIFICATION
                refusal.confidence_score = round(sufficiency.top_score, 2)
                refusal.latency_ms = round((time.time() - start_time) * 1000, 2)
                return refusal

        # Stage 3: Grounded Answer Generation
        chunks_to_use = sufficiency.qualifying_chunks if sufficiency.qualifying_chunks else retrieved_chunks
        answer = answer_service.generate_answer(request.question, chunks_to_use)

        # Citation validation
        if require_citation and not sufficiency.citations:
            if not allow_unsupported:
                refusal = safe_refusal_factory.create_insufficient_evidence_refusal(
                    reason="Required verifiable source citations could not be established from available documents.",
                    query_id=query_id
                )
                refusal.mode_used = SafeguardMode.RAG_THRESHOLD_VERIFICATION
                refusal.latency_ms = round((time.time() - start_time) * 1000, 2)
                return refusal

        # Stage 4: Independent Factual Answer Verification
        verification = VerificationStatus.NOT_APPLICABLE
        if enable_verification:
            ver_res = verification_service.verify_answer(
                question=request.question,
                answer=answer,
                evidence_chunks=chunks_to_use,
                allow_unsupported=allow_unsupported
            )
            verification = ver_res.status

            if not ver_res.is_valid:
                if not allow_unsupported:
                    refusal = safe_refusal_factory.create_verification_failed_refusal(
                        reason=ver_res.reason,
                        unsupported_claims=ver_res.unsupported_claims,
                        query_id=query_id
                    )
                    refusal.mode_used = SafeguardMode.RAG_THRESHOLD_VERIFICATION
                    refusal.sources = sufficiency.citations
                    refusal.confidence_score = round(ver_res.confidence, 2)
                    refusal.latency_ms = round((time.time() - start_time) * 1000, 2)
                    return refusal
                else:
                    answer = f"[UNVERIFIED CLAIM WARNING] {answer}"

        latency = (time.time() - start_time) * 1000

        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=answer,
            evidence_status=sufficiency.evidence_status,
            sources=sufficiency.citations,
            verification=verification,
            refusal_reason=None,
            confidence_score=round(sufficiency.top_score, 2),
            mode_used=SafeguardMode.RAG_THRESHOLD_VERIFICATION,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


answer_verification_safeguard = AnswerVerificationSafeguard()
