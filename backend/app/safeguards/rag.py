"""
Mode 2: Standard RAG (Retrieval-Augmented Generation).
Retrieves top-k passages and prompts the LLM to answer unconditionally, without an evidence threshold gate.
Demonstrates that naive RAG still generates confident wrong answers when relevant documents are absent.
"""
import time
from backend.app.models.schemas import (
    ChatRequest,
    ChatResponse,
    DecisionType,
    EvidenceStatus,
    VerificationStatus,
    SourceCitation,
    SafeguardMode
)
from backend.app.services.retrieval_service import vector_store
from backend.app.services.answer_service import answer_service
from backend.app.config import settings


class RAGSafeguard:
    """Safeguard Mode 2: Standard RAG without threshold gating."""

    def process(self, request: ChatRequest, query_id: str) -> ChatResponse:
        start_time = time.time()
        top_k = request.top_k or settings.DEFAULT_TOP_K
        
        # Retrieve chunks without threshold filtering
        retrieved_chunks = vector_store.search(request.question, top_k=top_k)
        
        citations = [
            SourceCitation(
                document=rc.chunk.document_name,
                page=rc.chunk.page_number,
                section=rc.chunk.section,
                chunk_id=rc.chunk.chunk_id,
                relevance_score=rc.relevance_score,
                snippet=rc.chunk.text[:200]
            )
            for rc in retrieved_chunks
        ]

        top_score = retrieved_chunks[0].relevance_score if retrieved_chunks else 0.0

        if retrieved_chunks:
            answer = answer_service.generate_answer(request.question, retrieved_chunks)
            evidence_status = EvidenceStatus.MEDIUM if top_score > 0.6 else EvidenceStatus.LOW
        else:
            answer = "No document chunks were found in the database."
            evidence_status = EvidenceStatus.INSUFFICIENT

        latency = (time.time() - start_time) * 1000

        return ChatResponse(
            decision=DecisionType.ANSWER,
            answer=answer,
            evidence_status=evidence_status,
            sources=citations,
            verification=VerificationStatus.NOT_APPLICABLE,  # Mode 2 has no verification
            refusal_reason=None,
            confidence_score=round(top_score, 2),
            mode_used=SafeguardMode.RAG,
            query_id=query_id,
            latency_ms=round(latency, 2)
        )


rag_safeguard = RAGSafeguard()
