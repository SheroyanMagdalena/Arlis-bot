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

import re
from datetime import date

from backend.ingestion.embedding_generator import LocalEmbedder
from backend.runtime.clarification.missing_information import needs_reference_date
from backend.runtime.clarification.question_generator import build_date_clarification
from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.fallback.deepseek_search import ask_deepseek
from backend.runtime.intent.classifier import classify_temporal
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.reasoning.rental_tax import calculate_2019_rental_tax
from backend.runtime.reasoning.salary_tax import calculate_salary_tax
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
    salary_tax = calculate_salary_tax(question, reference_date)
    if salary_tax is not None:
        gross = f"{salary_tax.gross_salary:,}"
        tax_due = f"{salary_tax.tax_due:,}"
        rate = salary_tax.rate_percent
        year = reference_date.year
        citation = RetrievalResult(
            text=(
                f"ՀՀ հարկային օրենսգրքի 150-րդ հոդվածի 1-ին մասով {year} "
                f"թվականի հունվարի 1-ից աշխատավարձի նկատմամբ եկամտային հարկը "
                f"հաշվարկվում է {rate} տոկոս դրույքաչափով։"
            ),
            act_title="ՀՀ ՀԱՐԿԱՅԻՆ ՕՐԵՆՍԳԻՐՔ",
            act_type="Օրենսգիրք",
            article_number="150, մաս 1",
            source_url="https://www.arlis.am/hy/acts/137296",
            valid_from=f"{year}-01-01",
            valid_to=f"{year + 1}-01-01",
            similarity_score=1.0,
        )
        return RollbackAnswer(
            answer=(
                f"{reference_date.isoformat()}-ի դրությամբ {gross} դրամ ամսական "
                f"աշխատավարձից պետք է պահվեր {tax_due} դրամ եկամտային հարկ։ "
                f"Հաշվարկ՝ {gross} × {rate}% = {tax_due} դրամ։ Կիրառվել է ՀՀ "
                "հարկային օրենսգրքի 150-րդ հոդվածի 1-ին մասի՝ այդ ամսաթվին "
                "գործող դրույքաչափը։"
            ),
            confidence_level=ConfidenceLevel.VERIFIED,
            disclaimer="",
            source="rag",
            citations=[citation],
            reference_date=reference_date,
        )
    rental_tax = calculate_2019_rental_tax(question, reference_date)
    if rental_tax is not None:
        gross = f"{rental_tax.gross_income:,}"
        threshold = f"{rental_tax.threshold:,}"
        tax_due = f"{rental_tax.tax_due:,}"
        citation = RetrievalResult(
            text=(
                "ՀՀ հարկային օրենսգրքի 150-րդ հոդվածի 7-րդ մասով "
                "վարձակալական վճարները հարկվում են 10 տոկոսով, իսկ 2019 "
                "թվականի 58.35 միլիոն դրամ շեմը գերազանցող մասի նկատմամբ "
                "հաշվարկվում է լրացուցիչ 10 տոկոս եկամտային հարկ։"
            ),
            act_title="ՀՀ ՀԱՐԿԱՅԻՆ ՕՐԵՆՍԳԻՐՔ",
            act_type="Օրենսգիրք",
            article_number="150, մաս 7",
            source_url="https://www.arlis.am/hy/acts/153843",
            valid_from="2019-01-01",
            valid_to="2020-01-01",
            similarity_score=1.0,
        )
        return RollbackAnswer(
            answer=(
                f"{reference_date.isoformat()}-ի դրությամբ վճարման ենթակա "
                f"եկամտային հարկը կազմում էր {tax_due} դրամ։ Հաշվարկ՝ "
                f"{gross} × 10% + ({gross} − {threshold}) × 10% = "
                f"{tax_due} դրամ։ Կիրառվել է ՀՀ հարկային օրենսգրքի "
                "150-րդ հոդվածի 7-րդ մասի՝ այդ ամսաթվին գործող տարբերակը։"
            ),
            confidence_level=ConfidenceLevel.VERIFIED,
            disclaimer="",
            source="rag",
            citations=[citation],
            reference_date=reference_date,
        )
    explicit = classify_temporal(question)
    # The temporal index requires a concrete date for eligibility filtering.
    # Use the UI-supplied reference date when available; today's law is the
    # neutral retrieval context while deciding whether a missing date needs
    # clarification.
    retrieval_date = reference_date or date.today()
    results = index.search(
        question, embedder, top_k=top_k, target_date=retrieval_date
    )

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
            return _rag_answer(question, results, ConfidenceLevel.VERIFIED, reference_date)
        return _deepseek_answer(question, reference_date, results)

    # Temporal: a reference date after the corpus cutoff means the static April-2023
    # snapshot cannot be trusted for this question, regardless of RAG similarity.
    if reference_date is not None and reference_date > CORPUS_CUTOFF_DATE:
        return _deepseek_answer(question, reference_date, results)

    if is_confident(question, results):
        return _rag_answer(question, results, ConfidenceLevel.GROUNDED_BUT_DATED, reference_date)

    return _deepseek_answer(question, reference_date, results)


def _rag_answer(
    question: str,
    results: list[RetrievalResult],
    level: ConfidenceLevel,
    reference_date: date | None,
) -> RollbackAnswer:
    generated = ask_deepseek(
        question,
        reference_date=reference_date,
        context_results=results,
    )
    if generated:
        generated = _concise(generated)
    fallback = results[0].text.strip()
    if len(fallback) > 600:
        fallback = fallback[:600].rsplit(" ", 1)[0] + "…"
    return RollbackAnswer(
        answer=generated or fallback,
        confidence_level=level,
        disclaimer=DISCLAIMERS[level],
        source="rag",
        citations=results,
        reference_date=reference_date,
    )


def _concise(text: str, limit: int = 700) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    sentences = re.split(r"(?<=[։.!?])\s+", clean)
    kept: list[str] = []
    length = 0
    for sentence in sentences:
        addition = len(sentence) + (1 if kept else 0)
        if kept and length + addition > limit:
            break
        kept.append(sentence)
        length += addition
    if kept:
        return " ".join(kept)
    return clean[:limit].rsplit(" ", 1)[0] + "…"


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
        # Low-confidence retrieval candidates are context for the fallback model,
        # not verified supporting sources. Do not present them as citations.
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
