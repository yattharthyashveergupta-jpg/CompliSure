"""
Evidence Sufficiency & Grounding Evaluation Service.
The core research mechanism: determines whether retrieved evidence genuinely supports answering a question.
"""
from typing import List, Tuple, Optional
from pydantic import BaseModel
from backend.app.models.schemas import (
    RetrievedChunk,
    SourceCitation,
    EvidenceStatus,
    DecisionType
)
from backend.app.config import settings
from backend.app.utils.logging import logger


class EvidenceEvaluationResult(BaseModel):
    """Result of the evidence sufficiency assessment."""
    is_sufficient: bool
    evidence_status: EvidenceStatus
    decision: DecisionType
    confidence_score: float
    top_score: float
    qualifying_chunks: List[RetrievedChunk]
    citations: List[SourceCitation]
    refusal_reason: Optional[str] = None


class EvidenceService:
    """Evaluates retrieved chunks for relevance, completeness, and sufficiency."""

    def evaluate_sufficiency(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        threshold: float = settings.DEFAULT_EVIDENCE_THRESHOLD,
        min_supporting_chunks: int = settings.MIN_SUPPORTING_CHUNKS
    ) -> EvidenceEvaluationResult:
        """
        Assesses if retrieved chunks provide sufficient evidence to answer the query.
        Implements strict evidence gating.
        """
        if not retrieved_chunks:
            return EvidenceEvaluationResult(
                is_sufficient=False,
                evidence_status=EvidenceStatus.INSUFFICIENT,
                decision=DecisionType.REFUSE,
                confidence_score=0.0,
                top_score=0.0,
                qualifying_chunks=[],
                citations=[],
                refusal_reason="No relevant compliance passages were found in the approved document set."
            )

        top_score = retrieved_chunks[0].relevance_score
        qualifying = [rc for rc in retrieved_chunks if rc.relevance_score >= threshold]

        # Convert qualifying chunks to structured citations
        citations = [
            SourceCitation(
                document=rc.chunk.document_name,
                page=rc.chunk.page_number,
                section=rc.chunk.section,
                chunk_id=rc.chunk.chunk_id,
                relevance_score=rc.relevance_score,
                snippet=rc.chunk.text[:220] + "..." if len(rc.chunk.text) > 220 else rc.chunk.text
            )
            for rc in qualifying
        ]

        # Determine evidence status and confidence
        if len(qualifying) >= min_supporting_chunks and top_score >= threshold:
            if top_score >= 0.85:
                status = EvidenceStatus.HIGH
                confidence = min(0.98, top_score)
            else:
                status = EvidenceStatus.MEDIUM
                confidence = round(top_score * 0.9, 2)

            return EvidenceEvaluationResult(
                is_sufficient=True,
                evidence_status=status,
                decision=DecisionType.ANSWER,
                confidence_score=confidence,
                top_score=top_score,
                qualifying_chunks=qualifying,
                citations=citations,
                refusal_reason=None
            )
        else:
            # Below threshold or insufficient chunk count
            if top_score >= 0.60:
                status = EvidenceStatus.LOW
                refusal_reason = (
                    f"Retrieved passages did not meet the required relevance threshold "
                    f"({top_score:.2f} < {threshold:.2f}). Evidence is insufficient to answer reliably."
                )
            else:
                status = EvidenceStatus.INSUFFICIENT
                refusal_reason = (
                    "No sufficiently relevant supporting evidence was found in the approved compliance documents."
                )

            return EvidenceEvaluationResult(
                is_sufficient=False,
                evidence_status=status,
                decision=DecisionType.REFUSE,
                confidence_score=round(top_score * 0.3, 2),
                top_score=top_score,
                qualifying_chunks=[],
                citations=[],
                refusal_reason=refusal_reason
            )


evidence_service = EvidenceService()
