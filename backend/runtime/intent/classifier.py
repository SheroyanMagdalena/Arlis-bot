"""Rule-based detection of explicit temporal references in a question.

Deliberately keyword/regex-based rather than an LLM call: it needs to be fast and
deterministic for a live demo, and "does this sentence mention a date" does not need
a model.
"""

from __future__ import annotations

import re

from backend.runtime.intent.schemas import TemporalDetection

# Armenian, English, and Russian temporal keywords/phrases. The demo may mix
# languages, so all three are checked.
TEMPORAL_KEYWORDS = [
    # Armenian
    "այսօր", "երեկ", "վաղը", "հիմա", "ներկայումս", "ընթացիկ",
    "այս տարի", "անցյալ տարի", "հաջորդ տարի", "այս ամիս", "անցյալ ամիս",
    "մինչ օրս", "ներկա պահին", "արդեն",
    # English
    "today", "yesterday", "tomorrow", "currently", "current", "now",
    "this year", "last year", "next year", "this month", "last month",
    "as of", "at present",
    # Russian
    "сегодня", "вчера", "завтра", "сейчас", "в настоящее время",
    "в этом году", "в прошлом году", "на данный момент",
]

# Explicit dates: DD.MM.YYYY / DD/MM/YYYY, bare 4-digit years, and the Armenian
# year-abbreviation pattern "2023 թ." / "2023թ.".
DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"),
    re.compile(r"\b(19|20)\d{2}\s*թ\.?"),
    re.compile(r"\b(19|20)\d{2}\b"),
]


_KEYWORD_PATTERNS = [
    (keyword, re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"))
    for keyword in TEMPORAL_KEYWORDS
]


def classify_temporal(question: str) -> TemporalDetection:
    normalized = question.lower()

    matched_terms = [
        keyword for keyword, pattern in _KEYWORD_PATTERNS if pattern.search(normalized)
    ]

    detected_dates: list[str] = []
    for pattern in DATE_PATTERNS:
        detected_dates.extend(match.group(0) for match in pattern.finditer(question))

    is_temporal = bool(matched_terms) or bool(detected_dates)
    return TemporalDetection(
        is_temporal=is_temporal,
        matched_terms=matched_terms,
        detected_dates=detected_dates,
    )
