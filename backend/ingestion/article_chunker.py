"""Article-aware chunking for normalized ARLIS documents."""

from __future__ import annotations

import re
from typing import Any, Iterator, Mapping


ARTICLE_PATTERN = re.compile(
    r"(?im)^\s*(?:ՀՈԴՎԱԾ|Հոդված|СТАТЬЯ|Статья|ARTICLE|Article)\s+"
    r"(?P<number>\d+(?:\.\d+)*)\s*[.։:]?\s*"
)


def _split_long_text(text: str, max_chars: int, overlap_chars: int) -> Iterator[str]:
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        if end >= len(text):
            return
        start = max(end - overlap_chars, start + 1)


def chunk_document(
    document: Mapping[str, Any],
    *,
    max_chars: int = 1800,
    overlap_chars: int = 200,
) -> Iterator[dict[str, Any]]:
    """Split a parsed document by article, then by size when an article is long."""
    if max_chars <= 0 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Expected max_chars > overlap_chars >= 0")

    text = str(document.get("text") or "").strip()
    if not text:
        return
    matches = list(ARTICLE_PATTERN.finditer(text))
    sections: list[tuple[str | None, str]] = []
    if not matches:
        sections.append((None, text))
    else:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections.append((match.group("number"), text[match.start():end].strip()))

    chunk_index = 0
    for article_number, section in sections:
        article_heading = section.splitlines()[0].strip() if article_number else ""
        for part in _split_long_text(section, max_chars, overlap_chars):
            yield {
                "chunk_id": f"{document['act_id']}:{chunk_index}",
                "act_id": document["act_id"],
                "act_title": document.get("title") or "",
                "act_type": document.get("act_type") or "",
                "article_number": article_number,
                "article_heading": article_heading,
                "valid_from": document.get("effective_date"),
                "valid_to": document.get("interruption_date"),
                "status": document.get("status"),
                "source_url": document.get("source_url"),
                "text": part,
            }
            chunk_index += 1
