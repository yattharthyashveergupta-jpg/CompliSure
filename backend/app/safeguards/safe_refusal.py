"""
Standardized Safe Refusal utilities.
Ensures uniform, compliance-grade safe refusals when evidence is insufficient or unverified.
"""
from typing import Optional
from backend.app.models.schemas import ChatResponse, DecisionType, EvidenceStatus, VerificationStatus, SafeguardMode


class SafeRefusalFactory:
    """Creates consistent compliance safe refusal responses."""

    @staticmethod
    def create_insufficient_evidence_refusal(
        reason: Optional[str] = None,
        mode: SafeguardMode = SafeguardMode.RAG_THRESHOLD_VERIFICATION,
        confidence: float = 0.0,
        query_id: Optional[str] = None
    ) -> ChatResponse:
        """Standard refusal when evidence is missing or below threshold."""
        explanation = reason or "No sufficiently relevant supporting evidence was found in the approved compliance documents."
        return ChatResponse(
            decision=DecisionType.REFUSE,
            answer="I can't answer this reliably from the provided compliance documents because sufficient supporting evidence was not found.",
            evidence_status=EvidenceStatus.INSUFFICIENT,
            sources=[],
            verification=VerificationStatus.NOT_APPLICABLE,
            refusal_reason=explanation,
            confidence_score=confidence,
            mode_used=mode,
            query_id=query_id
        )

    @staticmethod
    def create_verification_failed_refusal(
        reason: Optional[str] = None,
        mode: SafeguardMode = SafeguardMode.RAG_THRESHOLD_VERIFICATION,
        confidence: float = 0.0,
        query_id: Optional[str] = None
    ) -> ChatResponse:
        """Refusal when generated answer cannot be verified against source text."""
        explanation = reason or "Generated answer contained claims that could not be verified against the approved documents."
        return ChatResponse(
            decision=DecisionType.REFUSE,
            answer="I couldn't verify this answer against the provided compliance documents, so I won't provide an unsupported answer.",
            evidence_status=EvidenceStatus.LOW,
            sources=[],
            verification=VerificationStatus.UNSUPPORTED,
            refusal_reason=explanation,
            confidence_score=confidence,
            mode_used=mode,
            query_id=query_id
        )


safe_refusal_factory = SafeRefusalFactory()
