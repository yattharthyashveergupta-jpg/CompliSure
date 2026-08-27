"""
Safeguards Implementation Package.
Contains all 4 experimental modes for academic comparison.
"""
from backend.app.safeguards.baseline import BaselineSafeguard
from backend.app.safeguards.rag import RAGSafeguard
from backend.app.safeguards.evidence_threshold import EvidenceThresholdSafeguard
from backend.app.safeguards.answer_verification import AnswerVerificationSafeguard
from backend.app.safeguards.safe_refusal import safe_refusal_factory

__all__ = [
    "BaselineSafeguard",
    "RAGSafeguard",
    "EvidenceThresholdSafeguard",
    "AnswerVerificationSafeguard",
    "safe_refusal_factory"
]
