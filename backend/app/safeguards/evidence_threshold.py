"""
Mode 3: RAG with Evidence Threshold Gating.
Retrieves chunks and strictly requires the top relevance score to exceed the threshold.
Safely refuses to answer when evidence is insufficient, preventing ungrounded hallucinations.
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
    """Safeguard Mode 3: RAG + Evidence Threshold Gate."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        threshold = request.threshold if request.threshold is not None else settings.DEFAULT_EVIDENCE_THRESHOLD
        top_k = request.top_k or settings.DEFAULT_TOP_K
        min_chunks = request.min_supporting_chunks or settings.MIN_SUPPORTING_CHUNKS
        allow_unsupported = request.allow_unsupported_answers if request.allow_unsupported_answers is not None else settings.ALLOW_UNSUPPORTED_ANSWERS
        require_citation = request.require_source_citation if request.require_source_citation is not None else settings.REQUIRE_SOURCE_CITATION

        # Step 1: Retrieve candidate chunks
        retrieved_chunks = vector_store.search(request.question, top_k=top_k)

        # Step 2: Evidence sufficiency evaluation
        sufficiency = evidence_service.evaluate_sufficiency(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
            threshold=threshold,
            min_supporting_chunks=min_chunks
        )

        # Step 3: Threshold gate decision
        if not sufficiency.is_sufficient:
            if not allow_unsupported:
                # Primary compliance behavior: Abstain / Refuse
                refusal = safe_refusal_factory.create_insufficient_evidence_refusal(
                    reason=sufficiency.refusal_reason or "Evidence below sufficiency threshold.",
                    query_id=query_id
                )
                refusal.mode_used = SafeguardMode.RAG_THRESHOLD
                refusal.confidence_score = round(sufficiency.top_score, 2)
                refusal.latency_ms = round((time.time() - start_time) * 1000, 2)
                return refusal
            else:
                # If explicit policy allows unsupported generation with warning
                answer = answer_service.generate_answer(request.question, retrieved_chunks)
                latency = (time.time() - start_time) * 1000
                return ChatResponse(
                    decision=DecisionType.ANSWER,
                    answer=f"[UNSUPPORTED / UNGROUNDED NOTICE] {answer}",
                    evidence_status=EvidenceStatus.INSUFFICIENT,
                    sources=sufficiency.citations,
                    verification=VerificationStatus.UNSUPPORTED,
                    refusal_reason="Policy allowed ungrounded response with explicit disclosure warning.",
                    confidence_score=round(sufficiency.top_score, 2),
                    mode_used=SafeguardMode.RAG_THRESHOLD,
                    query_id=query_id,
                    latency_ms=round(latency, 2)
                )

        # Step 4: Grounded answer generation using qualified chunks
        answer = answer_service.generate_answer(request.question, sufficiency.qualifying_chunks)

        # Step 5: Citation requirement check
        if require_citation and not sufficiency.citations:
            refusal = safe_refusal_factory.create_insufficient_evidence_refusal(
                reason="Institutional policy requires verifiable source citations, which could not be established.",
                query_id=query_id
            )
            refusal.mode_used = SafeguardMode.RAG_THRESHOLD
            refusal.latency_ms = round((time.time() - start_time) * 1000, 2)
            return refusal

        latency = (time.time() - start_time) * 1000

        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=answer,
            evidence_status=sufficiency.evidence_status,
            sources=sufficiency.citations,
            verification=VerificationStatus.NOT_APPLICABLE,
            refusal_reason=None,
            confidence_score=round(sufficiency.top_score, 2),
            mode_used=SafeguardMode.RAG_THRESHOLD,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


evidence_threshold_safeguard = EvidenceThresholdSafeguard()
