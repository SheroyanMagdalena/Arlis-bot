"""Local multilingual embedding generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


DEFAULT_MODEL = "intfloat/multilingual-e5-small"


class LocalEmbedder:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "sentence-transformers is required; install requirements.txt"
            ) from error
        self.model_name = model_name
        try:
            self.model: Any = SentenceTransformer(model_name, local_files_only=True)
        except OSError:
            # First use downloads the free model; subsequent use is fully offline.
            self.model = SentenceTransformer(model_name)

    def embed_passages(self, texts: Sequence[str], batch_size: int = 32) -> np.ndarray:
        return self._encode([f"passage: {text}" for text in texts], batch_size)

    def embed_query(self, query: str) -> np.ndarray:
        return self._encode([f"query: {query}"], 1)[0]

    @property
    def dimension(self) -> int:
        getter = getattr(self.model, "get_embedding_dimension", self.model.get_sentence_embedding_dimension)
        return int(getter())

    def configuration(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "normalize_embeddings": True,
            "query_prefix": "query: ",
            "passage_prefix": "passage: ",
            "pooling": str(self.model[1]) if len(self.model) > 1 else "model-defined",
        }

    def _encode(self, texts: Sequence[str], batch_size: int) -> np.ndarray:
        vectors = self.model.encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > batch_size,
        )
        return np.asarray(vectors, dtype=np.float32)
