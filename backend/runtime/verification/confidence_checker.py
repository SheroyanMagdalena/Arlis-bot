"""Confidence tiers attached to every rollback-pipeline answer."""

from __future__ import annotations

from enum import Enum

from backend.runtime.retrieval.schemas import RetrievalResult
from backend.shared.config import RAG_HIGH_CONFIDENCE_THRESHOLD


class ConfidenceLevel(str, Enum):
    VERIFIED = "VERIFIED"
    GROUNDED_BUT_DATED = "GROUNDED_BUT_DATED"
    EXTERNAL_UNVERIFIED = "EXTERNAL_UNVERIFIED"
    NO_ANSWER = "NO_ANSWER"


DISCLAIMERS: dict[ConfidenceLevel, str] = {
    ConfidenceLevel.VERIFIED: "",
    ConfidenceLevel.GROUNDED_BUT_DATED: (
        "This answer reflects the ARLIS database snapshot from April 2023. If the "
        "law changed after that date, this may be outdated — verify against the "
        "official source."
    ),
    ConfidenceLevel.EXTERNAL_UNVERIFIED: (
        "We are not 100% sure — this answer was not found in the verified ARLIS "
        "legal database and comes from a general external source. Please confirm "
        "independently before relying on it."
    ),
    ConfidenceLevel.NO_ANSWER: (
        "We could not find a reliable answer. Please rephrase your question or "
        "consult an official ARLIS source directly."
    ),
}


def is_confident(
    results: list[RetrievalResult],
    threshold: float = RAG_HIGH_CONFIDENCE_THRESHOLD,
) -> bool:
    return bool(results) and results[0].similarity_score >= threshold
