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
    act_type: str = ""
    valid_from: str = ""
    valid_to: str | None = None
    final_score: float = 0.0
    dense_rank: int | None = None
    bm25_score: float = 0.0
    bm25_rank: int | None = None
    rrf_score: float = 0.0
    reranker_score: float = 0.0
    matched_query_terms: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, str | float | None]:
        return {
            "text": self.text,
            "act_title": self.act_title,
            "act_type": self.act_type,
            "article_number": self.article_number,
            "source_url": self.source_url,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "similarity_score": self.similarity_score,
            "final_score": self.final_score,
            "dense_score": self.similarity_score,
            "dense_rank": self.dense_rank,
            "bm25_score": self.bm25_score,
            "bm25_rank": self.bm25_rank,
            "rrf_score": self.rrf_score,
            "reranker_score": self.reranker_score,
            "matched_query_terms": list(self.matched_query_terms),
        }
