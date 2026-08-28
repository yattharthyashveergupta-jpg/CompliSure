"""
Answer Generation Service for CompliSure.
Constructs strict grounding prompts and enforces zero-hallucination policies.
"""
from typing import List
import re
from backend.app.models.schemas import RetrievedChunk
from backend.app.config import settings
from backend.app.services.llm_client import genai_manager
from backend.app.utils.logging import logger

try:
    from google.genai import types
    HAS_TYPES = True
except ImportError:
    HAS_TYPES = False


STRICT_SYSTEM_INSTRUCTION = """
You are CompliSure, an evidence-grounded compliance assistant for regulated institutions.

CRITICAL OPERATING RULES:
1. Grounding Rule: Answer the user's question using ONLY the factual statements contained in the provided "Retrieved Evidence" passages.
2. Zero Hallucination: Do NOT use outside general knowledge, do NOT invent rules, deadlines, dollar/rupee figures, or procedures not explicitly stated in the evidence.
3. Unsupported Claims: If the provided evidence does not explicitly answer the question or if important details are missing, reply: "The provided compliance documents do not contain sufficient information to answer this question."
4. Citation Integrity: Do NOT make up page numbers or document titles. Only refer to the provided evidence sources.
5. Tone: Objective, professional, concise, compliance-oriented.
"""


class AnswerService:
    """Generates strictly grounded answers from verified compliance chunks."""

    def __init__(self):
        self.model_name = settings.GEMINI_MODEL

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
            return "The available source documents do not contain sufficient evidence to answer this question."

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

        if genai_manager.is_remote_active and HAS_TYPES:
            try:
                client = genai_manager.client
                response = client.models.generate_content(
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
                genai_manager.mark_remote_failed(e)

        # Deterministic extraction fallback for offline / test environments
        return self._extract_grounded_answer(question, evidence_chunks)

    def _generate_baseline(self, question: str) -> str:
        """Baseline LLM mode without any document retrieval context (susceptible to hallucination)."""
        prompt = (
            f"Answer this compliance/policy question as a general assistant:\n"
            f"{question}"
        )
        if genai_manager.is_remote_active and HAS_TYPES:
            try:
                client = genai_manager.client
                response = client.models.generate_content(
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
                genai_manager.mark_remote_failed(e)

        # Deterministic ungrounded baseline simulation: generates plausible standard answer
        return (
            f"Standard institutional policies typically allow standard expense and procedure claims. "
            f"For '{question}', typical allowances range depending on organizational department approval."
        )

    def _extract_grounded_answer(self, question: str, evidence_chunks: List[RetrievedChunk]) -> str:
        """Deterministic answer extraction from chunks for test suite and offline use."""
        top_chunk = evidence_chunks[0].chunk.text
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", top_chunk) if s.strip()]
        
        q_words = set(re.findall(r"\b[a-z0-9]+\b", question.lower()))
        best_sentence = sentences[0] if sentences else top_chunk
        best_score = -1

        for sentence in sentences:
            s_words = set(re.findall(r"\b[a-z0-9]+\b", sentence.lower()))
            score = len(q_words.intersection(s_words))
            if score > best_score:
                best_score = score
                best_sentence = sentence

        doc_name = evidence_chunks[0].chunk.document_name
        page_num = evidence_chunks[0].chunk.page_number
        return f"According to {doc_name} (Page {page_num}), {best_sentence}"


answer_service = AnswerService()
