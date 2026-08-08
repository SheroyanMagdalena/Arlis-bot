"""Rollback pipeline: temporal detection -> RAG -> DeepSeek fallback.

Orchestrates the full "rollback" stage described in the team plan:

1. Detect explicit temporal wording in the question ("today", "last year", a date).
2. Always run the RAG search first — the matched content is needed to tell whether
   the topic is implicitly date-conditioned (e.g. "how much is child benefit?").
3. If the topic is date-dependent and no reference date has been supplied yet, stop
   and return a `ClarificationRequest` asking the caller to show a calendar.
4. Once temporal (explicitly or via a supplied reference date), decide whether the
   static April-2023 corpus can be trusted for that date, and either use the RAG
   match (GROUNDED_BUT_DATED) or fall back to DeepSeek (EXTERNAL_UNVERIFIED /
   NO_ANSWER).

This is a standalone integration point: it answers using RAG chunk text directly
until a teammate's `reasoning/answer_generator.py` exists to synthesize a real
answer from the same citations.
"""

from __future__ import annotations

from datetime import date

from backend.ingestion.embedding_generator import LocalEmbedder
from backend.runtime.clarification.missing_information import needs_reference_date
from backend.runtime.clarification.question_generator import build_date_clarification
from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.fallback.deepseek_search import ask_deepseek
from backend.runtime.intent.classifier import classify_temporal
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.retrieval.vector_search import LocalVectorIndex
from backend.runtime.verification.confidence_checker import (
    ConfidenceLevel,
    DISCLAIMERS,
    is_confident,
)
from backend.shared.config import CORPUS_CUTOFF_DATE


def run_rollback(
    question: str,
    index: LocalVectorIndex,
    embedder: LocalEmbedder,
    *,
    reference_date: date | None = None,
    top_k: int = 5,
) -> RollbackAnswer | ClarificationRequest:
    explicit = classify_temporal(question)
    results = index.search(question, embedder, top_k=top_k)

    if (
        reference_date is None
        and not explicit.is_temporal
        and needs_reference_date(question, results)
    ):
        return build_date_clarification()

    is_temporal = explicit.is_temporal or reference_date is not None

    if not is_temporal:
        if is_confident(results):
            return _rag_answer(results, ConfidenceLevel.VERIFIED, reference_date)
        return _no_answer(reference_date)

    # Temporal: a reference date after the corpus cutoff means the static April-2023
    # snapshot cannot be trusted for this question, regardless of RAG similarity.
    if reference_date is not None and reference_date > CORPUS_CUTOFF_DATE:
        return _deepseek_answer(question, reference_date)

    if is_confident(results):
        return _rag_answer(results, ConfidenceLevel.GROUNDED_BUT_DATED, reference_date)

    return _deepseek_answer(question, reference_date)


def _rag_answer(
    results: list[RetrievalResult],
    level: ConfidenceLevel,
    reference_date: date | None,
) -> RollbackAnswer:
    return RollbackAnswer(
        answer=results[0].text,
        confidence_level=level,
        disclaimer=DISCLAIMERS[level],
        source="rag",
        citations=results,
        reference_date=reference_date,
    )


def _deepseek_answer(question: str, reference_date: date | None) -> RollbackAnswer:
    answer = ask_deepseek(question, reference_date=reference_date)
    if answer is None:
        return _no_answer(reference_date)
    return RollbackAnswer(
        answer=answer,
        confidence_level=ConfidenceLevel.EXTERNAL_UNVERIFIED,
        disclaimer=DISCLAIMERS[ConfidenceLevel.EXTERNAL_UNVERIFIED],
        source="deepseek",
        citations=[],
        reference_date=reference_date,
    )


def _no_answer(reference_date: date | None) -> RollbackAnswer:
    return RollbackAnswer(
        answer="",
        confidence_level=ConfidenceLevel.NO_ANSWER,
        disclaimer=DISCLAIMERS[ConfidenceLevel.NO_ANSWER],
        source="none",
        citations=[],
        reference_date=reference_date,
    )
