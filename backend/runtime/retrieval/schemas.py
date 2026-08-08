"""Retrieval result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalResult:
    text: str
    act_title: str
    article_number: str | None
    source_url: str | None
    similarity_score: float

    def as_dict(self) -> dict[str, str | float | None]:
        return {
            "text": self.text,
            "act_title": self.act_title,
            "article_number": self.article_number,
            "source_url": self.source_url,
            "similarity_score": self.similarity_score,
        }
