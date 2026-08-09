"""Shared Armenian-safe text normalization and retrieval query preparation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any


TOKEN_RE = re.compile(r"[0-9A-Za-z\u0531-\u0556\u0561-\u0587]+(?:[.][0-9]+)*", re.UNICODE)
ARMENIAN_SUFFIXES = tuple(
    sorted(
        {
            "ների", "ներով", "ներից", "ներում", "ության", "ությունների",
            "ությունից", "ությանը", "ությունները", "ություններ",
            "ական", "ային", "ավոր", "ավորության", "ից", "ով", "ում",
            "ին", "ի", "ը", "ն", "եր", "ներ",
        },
        key=len,
        reverse=True,
    )
)

QUERY_STOPWORDS = {
    "ես", "դու", "նա", "մենք", "դուք", "նրանք", "եմ", "է", "ենք", "են",
    "բայց", "չեմ", "ունեմ",
    "արդյոք", "ինչ", "ինչպես", "որքան", "որը", "որ", "ստանում",
    "մեկ", "երկու", "երեք", "չորս", "հինգ", "վեց", "յոթ", "ութ", "ինը", "տաս",
    "հարյուր", "հազար", "միլիոն", "հիսուն",
}

ELIGIBILITY_MARKERS = {"օգտվել", "իրավասու", "շահառու", "ընդգրկվել"}
ELIGIBILITY_EVIDENCE = {"իրավունք", "իրավասու", "շահառու", "ընդգրկվել", "պայման", "չափանիշ"}
DISMISSAL_MARKERS = {"ազատել", "ազատվել", "ազատում"}

# Small domain lexicon that maps citizens' wording to recurring statutory wording.
# It is retrieval-only and never changes the question shown to the answer model.
LEGAL_CONCEPT_EXPANSIONS = {
    "ազատվել": ("աշխատանքային պայմանագիր", "պայմանագրի լուծում", "գործատուի նախաձեռնությամբ", "աշխատանքային օրենսգիրք"),
    "ազատել": ("աշխատանքային պայմանագիր", "պայմանագրի լուծում", "գործատուի նախաձեռնությամբ", "աշխատանքային օրենսգիրք"),
    "ազատում": ("աշխատանքային պայմանագիր", "պայմանագրի լուծում", "գործատուի նախաձեռնությամբ", "աշխատանքային օրենսգիրք"),
    "վերջնահաշվարկ": ("աշխատավարձ", "վճարում", "պայմանագրի լուծում", "գործատու"),
}


def normalize_text(value: str) -> str:
    """Normalize Unicode/whitespace without changing citation text."""
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    return re.sub(r"\s+", " ", text).strip().casefold()


def _light_stem(token: str) -> str:
    """Conservative Armenian suffix removal for lexical matching only."""
    if not any("\u0531" <= char <= "\u0587" for char in token):
        return token
    for suffix in ARMENIAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 5:
            return token[: -len(suffix)]
    return token


def tokenize(value: str) -> list[str]:
    tokens = TOKEN_RE.findall(normalize_text(value))
    return [_light_stem(token) for token in tokens if len(token) > 1]


def lexical_tokens(value: str) -> list[str]:
    """Unigrams plus ordered bigrams for exact legal-phrase evidence."""
    words = tokenize(value)
    return [*words, *(f"__phrase__{left}_{right}" for left, right in zip(words, words[1:]))]


def prepare_query(query: str) -> tuple[str, list[str]]:
    """Preserve the query while adding reusable lexical phrase/concept signals."""
    normalized = normalize_text(query)
    stopwords = {_light_stem(token) for token in QUERY_STOPWORDS}
    words = [token for token in tokenize(normalized) if token not in stopwords]
    expanded_words = list(words)
    for word in words:
        for expansion in LEGAL_CONCEPT_EXPANSIONS.get(word, ()):
            expanded_words.extend(tokenize(expansion))
    words = list(dict.fromkeys(expanded_words))
    # Adjacent content-word phrases strengthen legal multi-word concepts without
    # maintaining a question-specific synonym table.
    terms = [*words, *(f"__phrase__{left}_{right}" for left, right in zip(words, words[1:]))]
    return normalized, list(dict.fromkeys(terms))


def query_intent_terms(query: str) -> set[str]:
    """Return reusable evidence terms required by recognizable legal intents."""
    words = set(tokenize(query))
    if words & ELIGIBILITY_MARKERS:
        return {_light_stem(term) for term in ELIGIBILITY_EVIDENCE}
    if "գործատու" in words and words & DISMISSAL_MARKERS:
        return {"__phrase__գործատու_նախաձեռնությամբ"}
    return set()


def searchable_text(chunk: Mapping[str, Any]) -> str:
    """Build retrieval-only context; original ``text`` remains untouched."""
    article = chunk.get("article_number")
    header = "\n".join(
        part
        for part in (
            str(chunk.get("act_title") or "").strip(),
            str(chunk.get("act_type") or "").strip(),
            f"Հոդված {article}" if article else "",
            str(chunk.get("article_heading") or "").strip(),
        )
        if part
    )
    return f"{header}\n{chunk.get('text') or ''}".strip()
