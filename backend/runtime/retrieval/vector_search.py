"""Small local cosine-similarity vector index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from backend.ingestion.embedding_generator import LocalEmbedder
from backend.runtime.retrieval.schemas import RetrievalResult


class LocalVectorIndex:
    def __init__(self, embeddings: np.ndarray, chunks: list[dict[str, Any]]) -> None:
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
            raise ValueError("Embeddings and chunk metadata have incompatible shapes")
        self.embeddings = embeddings
        self.chunks = chunks

    @classmethod
    def build(
        cls,
        chunks: Sequence[dict[str, Any]],
        embedder: LocalEmbedder,
        *,
        batch_size: int = 32,
    ) -> "LocalVectorIndex":
        chunk_list = list(chunks)
        if not chunk_list:
            raise ValueError("Cannot build an index without chunks")
        embeddings = embedder.embed_passages(
            [str(chunk["text"]) for chunk in chunk_list], batch_size=batch_size
        )
        return cls(embeddings, chunk_list)

    def save(self, directory: str | Path) -> None:
        index_dir = Path(directory)
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "embeddings.npy", self.embeddings)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as stream:
            for chunk in self.chunks:
                stream.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, directory: str | Path) -> "LocalVectorIndex":
        index_dir = Path(directory)
        embeddings = np.load(index_dir / "embeddings.npy")
        with (index_dir / "chunks.jsonl").open(encoding="utf-8") as stream:
            chunks = [json.loads(line) for line in stream if line.strip()]
        return cls(embeddings, chunks)

    def search(
        self,
        query: str,
        embedder: LocalEmbedder,
        *,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        if not query.strip() or top_k <= 0 or not self.chunks:
            return []
        query_vector = embedder.embed_query(query)
        scores = np.asarray(self.embeddings @ query_vector)
        count = min(top_k, len(scores))
        indices = np.argpartition(scores, -count)[-count:]
        indices = indices[np.argsort(scores[indices])[::-1]]
        return [
            RetrievalResult(
                text=str(self.chunks[index]["text"]),
                act_title=str(self.chunks[index]["act_title"]),
                article_number=self.chunks[index].get("article_number"),
                source_url=self.chunks[index].get("source_url"),
                similarity_score=round(float(scores[index]), 6),
            )
            for index in indices
        ]
