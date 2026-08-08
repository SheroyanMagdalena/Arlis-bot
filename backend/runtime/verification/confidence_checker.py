"""Confidence tiers attached to every rollback-pipeline answer."""

from __future__ import annotations

import re
from enum import Enum

from backend.runtime.fallback.deepseek_search import check_relevance
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
        "We are not 100% sure — the ARLIS legal database did not return a "
        "high-confidence match, so this answer combines any relevant excerpts we "
        "found with general external knowledge. Please confirm independently "
        "before relying on it."
    ),
    ConfidenceLevel.NO_ANSWER: (
        "We could not find a reliable answer. Please rephrase your question or "
        "consult an official ARLIS source directly."
    ),
}


# Cosine similarity on Armenian legal text can score misleadingly high between
# topically unrelated articles, because formal legal boilerplate register overlaps a
# lot in embedding space (observed live: a health-insurance question matched a
# drunk-driving penalty clause at 0.825 similarity, and even shared word roots like
# "աշխատավարձ" used generically as a fine-calculation unit). Lexical overlap alone
# cannot reliably tell relevance apart from coincidence in a language this densely
# root-derived, so the LLM itself judges relevance; the lexical check below is only a
# fallback for when that call is unavailable (no API key, network failure).
_STOPWORDS = {
    "այս", "այն", "որ", "որը", "որի", "եմ", "ես", "դու", "նա", "մենք", "դուք", "նրանք",
    "է", "էի", "էին", "իմ", "քո", "նրա", "մեր", "ձեր", "նրանց", "ի", "մեջ", "վրա",
    "դեպքում", "համար", "մասին", "և", "կամ", "բայց", "որովհետև", "եթե", "ապա", "այլ",
    "նաև", "the", "is", "are", "of", "in", "for", "and", "or", "to", "a", "an",
    "this", "that",
}
_MIN_WORD_LENGTH = 4
_PREFIX_LENGTH = 6


def _significant_word_prefixes(text: str) -> set[str]:
    words = re.findall(r"\w+", text.lower())
    return {
        word[:_PREFIX_LENGTH]
        for word in words
        if len(word) >= _MIN_WORD_LENGTH and word not in _STOPWORDS
    }


def _shares_lexical_overlap(question: str, text: str) -> bool:
    question_prefixes = _significant_word_prefixes(question)
    if not question_prefixes:
        return True
    text_prefixes = _significant_word_prefixes(text)
    required = min(2, len(question_prefixes))
    return len(question_prefixes & text_prefixes) >= required


def is_confident(
    question: str,
    results: list[RetrievalResult],
    threshold: float = RAG_HIGH_CONFIDENCE_THRESHOLD,
) -> bool:
    if not results or results[0].similarity_score < threshold:
        return False
    top_text = results[0].text
    relevance = check_relevance(question, top_text)
    if relevance is not None:
        return relevance
    return _shares_lexical_overlap(question, top_text)
