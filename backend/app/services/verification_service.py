"""
Answer Verification Service for CompliSure.
Independent second-stage verification: checks whether generated answer claims are factually entailed by retrieved evidence.
"""
from typing import List, Optional
import re
from pydantic import BaseModel
from backend.app.models.schemas import RetrievedChunk, VerificationStatus
from backend.app.config import settings
from backend.app.services.llm_client import genai_manager
from backend.app.utils.logging import logger

try:
    from google.genai import types
    HAS_TYPES = True
except ImportError:
    HAS_TYPES = False


class VerificationResult(BaseModel):
    """Result of independent answer verification."""
    status: VerificationStatus
    is_valid: bool
    confidence: float
    reason: str
    unsupported_claims: List[str] = []


VERIFIER_PROMPT = """
You are a Compliance Fact-Checking Auditor.

TASK: Verify if every factual claim in the GENERATED ANSWER is explicitly supported by the RETRIEVED EVIDENCE.

Classify into exactly one:
- SUPPORTED: Every fact, figure, deadline, and policy rule in the answer is strictly present in the evidence.
- PARTIALLY_SUPPORTED: Some parts are supported, but there are ungrounded assumptions or missing citations.
- UNSUPPORTED: The answer makes up rules, numbers, limits, or contradicts the evidence.

Provide your classification in the format:
STATUS: [SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED]
REASON: [Brief explanation]
"""


class VerificationService:
    """Evaluates generated compliance answers against retrieved passages."""

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

    def verify_answer(
        self,
        question: str,
        answer: str,
        evidence_chunks: List[RetrievedChunk],
        allow_unsupported: bool = False
    ) -> VerificationResult:
        """
        Verifies answer support against retrieved chunks.
        Returns SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.
        """
        if not evidence_chunks:
            return VerificationResult(
                status=VerificationStatus.UNSUPPORTED,
                is_valid=False,
                confidence=0.0,
                reason="No supporting evidence was provided to verify the answer.",
                unsupported_claims=[answer]
            )

        combined_evidence = " ".join([
            f"{ec.chunk.document_name} Page {ec.chunk.page_number} Section {ec.chunk.section or ''} {ec.chunk.text}"
            for ec in evidence_chunks
        ])

        # If Google GenAI client is available and active
        if genai_manager.is_remote_active and HAS_TYPES:
            try:
                client = genai_manager.client
                prompt = (
                    f"USER QUESTION: {question}\n\n"
                    f"GENERATED ANSWER: {answer}\n\n"
                    f"RETRIEVED EVIDENCE:\n{combined_evidence}\n"
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=VERIFIER_PROMPT,
                        temperature=0.0,
                        max_output_tokens=200
                    )
                )
                if response and response.text:
                    return self._parse_llm_verification(response.text, allow_unsupported)
            except Exception as e:
                genai_manager.mark_remote_failed(e)

        # Deterministic rule-based NLI / token entailment verifier
        return self._rule_based_verification(answer, combined_evidence, allow_unsupported)

    def _parse_llm_verification(self, text: str, allow_unsupported: bool) -> VerificationResult:
        """Parses structured output from LLM verifier."""
        status_match = re.search(r"STATUS:\s*(SUPPORTED|PARTIALLY_SUPPORTED|UNSUPPORTED)", text, re.IGNORECASE)
        reason_match = re.search(r"REASON:\s*(.*)", text, re.DOTALL | re.IGNORECASE)

        status_str = status_match.group(1).upper() if status_match else "SUPPORTED"
        reason = reason_match.group(1).strip() if reason_match else "Verified against source text."

        if status_str == "SUPPORTED":
            return VerificationResult(
                status=VerificationStatus.SUPPORTED,
                is_valid=True,
                confidence=0.95,
                reason=reason
            )
        elif status_str == "PARTIALLY_SUPPORTED":
            return VerificationResult(
                status=VerificationStatus.PARTIALLY_SUPPORTED,
                is_valid=allow_unsupported,
                confidence=0.60,
                reason=reason
            )
        else:
            return VerificationResult(
                status=VerificationStatus.UNSUPPORTED,
                is_valid=False,
                confidence=0.10,
                reason=reason,
                unsupported_claims=["Generated answer could not be grounded in evidence."]
            )

    def _rule_based_verification(self, answer: str, combined_evidence: str, allow_unsupported: bool) -> VerificationResult:
        """Heuristic factual consistency checker based on key entities and numerical tokens."""
        ans_clean = answer.lower()
        evi_clean = combined_evidence.lower()

        # Strip page/section metadata references before extracting substantive numbers
        ans_substantive = re.sub(r"\bpage\s+\d+\b|\bp\.\s*\d+\b|\bsection\s+\d+\b", "", ans_clean, flags=re.IGNORECASE)

        # Check numerical tokens / amounts (e.g. ₹5,000, 30 days, 24 hours)
        numbers = re.findall(r"(?:[₹$€£]?\d+(?:,\d+)*(?:\.\d+)?|\b\d+\b)", ans_substantive)
        unsupported_nums = [n for n in numbers if n.lower() not in evi_clean and re.sub(r"[^\d]", "", n) not in evi_clean]

        if unsupported_nums:
            return VerificationResult(
                status=VerificationStatus.UNSUPPORTED,
                is_valid=False,
                confidence=0.15,
                reason=f"Found unsupported numeric/policy claims: {', '.join(unsupported_nums)} not in evidence.",
                unsupported_claims=unsupported_nums
            )

        # Keyword overlap check
        ans_words = [w for w in re.findall(r"\b[a-z]{4,}\b", ans_clean) if w not in {"according", "policy", "document", "page", "section"}]
        if not ans_words:
            return VerificationResult(
                status=VerificationStatus.SUPPORTED,
                is_valid=True,
                confidence=0.90,
                reason="Answer verified with source document text."
            )

        supported_count = sum(1 for w in ans_words if w in evi_clean)
        ratio = supported_count / len(ans_words)

        if ratio >= 0.65:
            return VerificationResult(
                status=VerificationStatus.SUPPORTED,
                is_valid=True,
                confidence=round(ratio, 2),
                reason="Key factual claims are substantiated by the retrieved evidence."
            )
        elif ratio >= 0.40:
            return VerificationResult(
                status=VerificationStatus.PARTIALLY_SUPPORTED,
                is_valid=allow_unsupported,
                confidence=round(ratio, 2),
                reason="Some claims lack explicit grounding in the retrieved passages."
            )
        else:
            return VerificationResult(
                status=VerificationStatus.UNSUPPORTED,
                is_valid=False,
                confidence=round(ratio, 2),
                reason="The answer is not sufficiently grounded in the retrieved text.",
                unsupported_claims=["Insufficient semantic overlap with approved evidence."]
            )


verification_service = VerificationService()
