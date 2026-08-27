"""
Compliance Chat & Question-Answering Endpoints.
Routes queries through the selected safeguard mode with full provenance and audit logging.
"""
from typing import List
import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatHistoryItem,
    SafeguardMode,
    SourceCitation,
    DecisionType,
    EvidenceStatus,
    VerificationStatus
)
from backend.app.models.database import get_db, ChatLogModel
from backend.app.safeguards.baseline import baseline_safeguard
from backend.app.safeguards.rag import rag_safeguard
from backend.app.safeguards.evidence_threshold import evidence_threshold_safeguard
from backend.app.safeguards.answer_verification import answer_verification_safeguard
from backend.app.config import settings
from backend.app.utils.logging import log_query_decision, logger

router = APIRouter(prefix="/chat", tags=["Chat & Safeguards"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate compliance question and generate safe response"
)
def process_question(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a compliance query to the AI pipeline.
    Executes retrieval, evidence thresholding, grounded generation, and factual verification.
    """
    query_id = str(uuid.uuid4())[:8]
    mode = request.mode or SafeguardMode(settings.DEFAULT_SAFEGUARD_MODE)

    # Route according to chosen safeguard mode
    if mode == SafeguardMode.BASELINE_LLM:
        response = baseline_safeguard.process(request, query_id=query_id)
    elif mode == SafeguardMode.RAG:
        response = rag_safeguard.process(request, query_id=query_id)
    elif mode == SafeguardMode.RAG_THRESHOLD:
        response = evidence_threshold_safeguard.process(request, query_id=query_id)
    elif mode == SafeguardMode.RAG_THRESHOLD_VERIFICATION:
        response = answer_verification_safeguard.process(request, query_id=query_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown safeguard mode: '{mode}'"
        )

    # Structured Audit Logging
    top_score = response.sources[0].relevance_score if response.sources else 0.0
    log_query_decision(
        question=request.question,
        mode=mode.value,
        decision=response.decision.value,
        evidence_status=response.evidence_status.value,
        verification=response.verification.value,
        top_score=top_score,
        sources_count=len(response.sources)
    )

    # Persist log to Database for compliance audit trail
    try:
        log_record = ChatLogModel(
            id=query_id,
            timestamp=datetime.utcnow(),
            question=request.question,
            mode=mode.value,
            decision=response.decision.value,
            answer=response.answer,
            evidence_status=response.evidence_status.value,
            verification=response.verification.value,
            refusal_reason=response.refusal_reason,
            sources_json=json.dumps([s.model_dump() for s in response.sources]),
            confidence_score=response.confidence_score,
            latency_ms=response.latency_ms or 0.0
        )
        db.add(log_record)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not persist chat log record: {e}")

    return response


@router.get(
    "/history",
    response_model=List[ChatHistoryItem],
    summary="Get recent compliance assistant query audit history"
)
def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieves previous questions and safeguard decision audit logs."""
    logs = db.query(ChatLogModel).order_by(ChatLogModel.timestamp.desc()).limit(limit).all()
    history = []
    for l in logs:
        try:
            sources_data = json.loads(l.sources_json)
            sources = [SourceCitation(**s) for s in sources_data]
        except Exception:
            sources = []

        history.append(
            ChatHistoryItem(
                id=l.id,
                timestamp=l.timestamp.strftime("%b %d, %H:%M:%S"),
                question=l.question,
                mode=SafeguardMode(l.mode) if l.mode in SafeguardMode._value2member_map_ else SafeguardMode.RAG_THRESHOLD_VERIFICATION,
                decision=DecisionType(l.decision),
                answer=l.answer,
                evidence_status=EvidenceStatus(l.evidence_status),
                verification=VerificationStatus(l.verification),
                refusal_reason=l.refusal_reason,
                sources=sources,
                confidence_score=l.confidence_score
            )
        )
    return history
