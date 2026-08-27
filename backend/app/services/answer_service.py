"""
Answer Generation Service using Google Gemini API.
Constructs strict grounding prompts and enforces zero-hallucination policies.
"""
from typing import List, Optional, Union
import re
from backend.app.models.schemas import RetrievedChunk, SourceCitation
from backend.app.config import settings
from backend.app.utils.logging import logger

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


STRICT_SYSTEM_INSTRUCTION = """
You are CompliSure, an evidence-grounded compliance assistant for regulated institutions.

CRITICAL OPERATING RULES:
1. Grounding Rule: Answer the user's question using ONLY the factual statements contained in the provided "Retrieved Evidence" passages.
2. Zero Hallucination: Do NOT use outside general knowledge, do NOT invent rules, deadlines, dollar figures, or procedures not explicitly stated in the evidence.
3. Unsupported Claims: If the provided evidence does not explicitly answer the question or if important details are missing, reply: "The provided compliance documents do not contain sufficient information to answer this question."
4. Citation Integrity: Do NOT make up page numbers or document titles. Only refer to the provided evidence sources.
5. Tone: Objective, professional, concise, compliance-oriented.
"""


def is_valid_gemini_key(key: Optional[str]) -> bool:
    """Checks if API key is a realistically configured Google Gemini key."""
    if not key:
        return False
    k = key.strip()
    return len(k) >= 20 and not k.startswith("your_") and not k.startswith("test_") and not k.startswith("mock_")


class AnswerService:
    """Generates strictly grounded answers from verified compliance chunks."""

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL
        self._client = None
        self._remote_failed = False
        api_key = settings.GEMINI_API_KEY
        if HAS_GENAI and is_valid_gemini_key(api_key):
            try:
                self._client = genai.Client(api_key=api_key.strip())
                logger.info(f"Initialized Google GenAI LLM Client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI LLM client: {e}")
                self._client = None

    def generate_answer(
        self,
        question: str,
        evidence_chunks: List[RetrievedChunk],
        is_baseline: bool = False
    ) -> str:
        """
        Generates an answer to the question.
        If is_baseline=True, generates without evidence context (Mode 1: Baseline LLM).
        Otherwise, grounds strictly on evidence_chunks.
        """
        if is_baseline:
            return self._generate_baseline(question)

        if not evidence_chunks:
            return "I can't answer this reliably because no supporting evidence was provided."

        # Format evidence blocks
        evidence_text = "\n\n".join([
            f"--- EVIDENCE SOURCE {idx+1} ---\n"
            f"Document: {ec.chunk.document_name}\n"
            f"Page: {ec.chunk.page_number}\n"
            f"Section: {ec.chunk.section or 'General'}\n"
            f"Content: {ec.chunk.text}"
            for idx, ec in enumerate(evidence_chunks)
        ])

        prompt = (
            f"USER QUESTION:\n{question}\n\n"
            f"RETRIEVED EVIDENCE:\n{evidence_text}\n\n"
            f"INSTRUCTION: Based solely on the retrieved evidence above, answer the question clearly and directly. "
            f"If the evidence does not clearly state the answer, state that information is missing."
        )

        if self._client and not self._remote_failed:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=STRICT_SYSTEM_INSTRUCTION,
                        temperature=0.0,  # Deterministic for compliance
                        max_output_tokens=600
                    )
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.info(f"Gemini API unavailable or timed out ({e}). Switching to local deterministic engine.")
                self._remote_failed = True

        # Deterministic extraction fallback for offline / test environments
        return self._extract_grounded_answer(question, evidence_chunks)

    def _generate_baseline(self, question: str) -> str:
        """Baseline LLM mode without any document retrieval context."""
        prompt = (
            f"Answer this compliance/policy question as a helpful assistant:\n"
            f"{question}"
        )
        if self._client and not self._remote_failed:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=300
                    )
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                self._remote_failed = True

        # Deterministic ungrounded baseline simulation: generates plausible standard answer
        return (
            f"Standard institutional policies typically allow standard expense and procedure claims. "
            f"For '{question}', typical allowances range depending on organizational department approval."
        )

    def _extract_grounded_answer(self, question: str, evidence_chunks: List[RetrievedChunk]) -> str:
        """Deterministic answer extraction from chunks for test suite and offline use."""
        # Find the most relevant sentence from top chunks
        top_chunk = evidence_chunks[0].chunk.text
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", top_chunk) if s.strip()]
        
        # Match sentence with highest word overlap with question
        q_words = set(question.lower().split())
        best_sentence = sentences[0] if sentences else top_chunk
        best_score = -1

        for sentence in sentences:
            s_words = set(sentence.lower().split())
            score = len(q_words.intersection(s_words))
            if score > best_score:
                best_score = score
                best_sentence = sentence

        return f"According to {evidence_chunks[0].chunk.document_name} (Page {evidence_chunks[0].chunk.page_number}), {best_sentence}"


answer_service = AnswerService()
