"""Detect whether a question needs a reference date before it can be answered."""

from __future__ import annotations

from backend.runtime.clarification.rules import (
    has_date_conditional_language,
    matches_date_dependent_topic,
)
from backend.runtime.retrieval.schemas import RetrievalResult


def needs_reference_date(
    question: str, results: list[RetrievalResult]
) -> bool:
    if matches_date_dependent_topic(question):
        return True
    return any(has_date_conditional_language(result.text) for result in results)
