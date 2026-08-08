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
5. Non-temporal questions the corpus can't confidently answer also fall back to
   DeepSeek (EXTERNAL_UNVERIFIED / NO_ANSWER) rather than giving up immediately —
   DeepSeek is always consulted before the pipeline reports NO_ANSWER. Whatever RAG
   retrieved (even below the confidence threshold) is passed along as candidate
   source material, so DeepSeek can ground the answer in real ARLIS excerpts and
   cite them rather than answering from general knowledge alone.

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

    # Whether the QUESTION is temporal is a property of the question and the
    # matched content alone -- it must not depend on whether a caller happens to
    # supply a reference_date. Some callers (e.g. a UI that always collects a date
    # up front) pass one on every request, including for non-temporal questions;
    # if presence-of-date alone flipped is_temporal, every such question would be
    # wrongly routed as temporal and the VERIFIED tier would never fire.
    implicit_temporal = not explicit.is_temporal and needs_reference_date(question, results)

    if reference_date is None and implicit_temporal:
        return build_date_clarification()

    is_temporal = explicit.is_temporal or implicit_temporal

    if not is_temporal:
        if is_confident(question, results):
            return _rag_answer(results, ConfidenceLevel.VERIFIED, reference_date)
        return _deepseek_answer(question, reference_date, results)

    # Temporal: a reference date after the corpus cutoff means the static April-2023
    # snapshot cannot be trusted for this question, regardless of RAG similarity.
    if reference_date is not None and reference_date > CORPUS_CUTOFF_DATE:
        return _deepseek_answer(question, reference_date, results)

    if is_confident(question, results):
        return _rag_answer(results, ConfidenceLevel.GROUNDED_BUT_DATED, reference_date)

    return _deepseek_answer(question, reference_date, results)


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


def _deepseek_answer(
    question: str,
    reference_date: date | None,
    results: list[RetrievalResult],
) -> RollbackAnswer:
    answer = ask_deepseek(question, reference_date=reference_date, context_results=results)
    if answer is None:
        return _no_answer(reference_date)
    return RollbackAnswer(
        answer=answer,
        confidence_level=ConfidenceLevel.EXTERNAL_UNVERIFIED,
        disclaimer=DISCLAIMERS[ConfidenceLevel.EXTERNAL_UNVERIFIED],
        source="deepseek",
        citations=results,
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
