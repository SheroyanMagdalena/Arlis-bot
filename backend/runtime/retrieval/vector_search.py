"""Local temporal hybrid (dense + BM25 + RRF) legal retrieval."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from backend.ingestion.embedding_generator import LocalEmbedder
from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.retrieval.text import ELIGIBILITY_MARKERS, lexical_tokens, prepare_query, query_intent_terms, searchable_text, tokenize


INDEX_FORMAT_VERSION = 2
RRF_K = 60
DENSE_RRF_WEIGHT = 1.0
BM25_RRF_WEIGHT = 5.0


def cosine_scores(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Return mathematically explicit cosine similarity for every matrix row."""
    matrix = np.asarray(matrix, dtype=np.float32)
    query = np.asarray(query, dtype=np.float32)
    if matrix.ndim != 2 or query.ndim != 1 or matrix.shape[1] != query.shape[0]:
        raise ValueError("Cosine inputs have incompatible shapes")
    row_norms = np.linalg.norm(matrix, axis=1)
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0 or np.any(row_norms == 0):
        raise ValueError("Cosine similarity is undefined for zero vectors")
    return (matrix @ query) / (row_norms * query_norm)


class BM25Index:
    def __init__(self, texts: Sequence[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.documents = [lexical_tokens(text) for text in texts]
        self.lengths = np.asarray([len(doc) for doc in self.documents], dtype=np.float32)
        self.average_length = float(self.lengths.mean()) if len(self.lengths) else 1.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for index, document in enumerate(self.documents):
            for term, frequency in Counter(document).items():
                self.postings[term].append((index, frequency))

    def scores(self, terms: Sequence[str], eligible: np.ndarray) -> np.ndarray:
        scores = np.zeros(len(self.documents), dtype=np.float32)
        corpus_size = len(self.documents)
        for term in dict.fromkeys(terms):
            posting = self.postings.get(term, ())
            if not posting:
                continue
            idf = math.log(1.0 + (corpus_size - len(posting) + 0.5) / (len(posting) + 0.5))
            for index, frequency in posting:
                if not eligible[index]:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * self.lengths[index] / max(self.average_length, 1.0)
                )
                scores[index] += idf * frequency * (self.k1 + 1) / denominator
        return scores


class LocalVectorIndex:
    def __init__(
        self,
        embeddings: np.ndarray,
        chunks: list[dict[str, Any]],
        manifest: dict[str, Any] | None = None,
        *,
        allow_legacy: bool = False,
    ) -> None:
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
            raise ValueError("Embeddings and chunk metadata have incompatible shapes")
        if manifest is None and not allow_legacy:
            raise ValueError(
                "Index has no model manifest and may be embedding-incompatible. "
                "Rebuild it, or explicitly use allow_legacy=True for migration/testing."
            )
        self.embeddings = embeddings
        self.chunks = chunks
        self.manifest = manifest
        self.search_texts = [searchable_text(chunk) for chunk in chunks]
        self.bm25 = BM25Index(self.search_texts)

    @classmethod
    def build(cls, chunks: Sequence[dict[str, Any]], embedder: LocalEmbedder, *, batch_size: int = 32) -> "LocalVectorIndex":
        chunk_list = list(chunks)
        if not chunk_list:
            raise ValueError("Cannot build an index without chunks")
        texts = [searchable_text(chunk) for chunk in chunk_list]
        embeddings = embedder.embed_passages(texts, batch_size=batch_size)
        manifest = {
            "format_version": INDEX_FORMAT_VERSION,
            "embedding": embedder.configuration(),
            "searchable_representation": "act_title+act_type+article_number+text:v1",
        }
        return cls(embeddings, chunk_list, manifest)

    def save(self, directory: str | Path) -> None:
        index_dir = Path(directory)
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "embeddings.npy", self.embeddings)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as stream:
            for chunk in self.chunks:
                stream.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        (index_dir / "index_manifest.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: str | Path, *, allow_legacy: bool = False) -> "LocalVectorIndex":
        index_dir = Path(directory)
        embeddings = np.load(index_dir / "embeddings.npy")
        with (index_dir / "chunks.jsonl").open(encoding="utf-8") as stream:
            chunks = [json.loads(line) for line in stream if line.strip()]
        metadata_cache = index_dir / "temporal_metadata.json"
        if chunks and not chunks[0].get("valid_from") and metadata_cache.exists():
            metadata = json.loads(metadata_cache.read_text(encoding="utf-8"))
            for chunk in chunks:
                chunk.update(metadata.get(str(chunk.get("act_id")), {}))
        manifest_path = index_dir / "index_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
        return cls(embeddings, chunks, manifest, allow_legacy=allow_legacy)

    def _validate_embedder(self, embedder: LocalEmbedder) -> None:
        if self.embeddings.shape[1] != embedder.dimension:
            raise ValueError(f"Embedding dimension mismatch: index={self.embeddings.shape[1]}, query={embedder.dimension}")
        if self.manifest:
            expected = self.manifest.get("embedding", {})
            actual = embedder.configuration()
            for key in ("model_name", "dimension", "normalize_embeddings", "query_prefix", "passage_prefix"):
                if expected.get(key) != actual.get(key):
                    raise ValueError(f"Embedding configuration mismatch for {key}: index={expected.get(key)!r}, query={actual.get(key)!r}")

    def search(self, query: str, embedder: LocalEmbedder, *, top_k: int = 5, target_date: date | None = None, candidate_k: int = 50) -> list[RetrievalResult]:
        if target_date is None:
            raise ValueError("target_date must be resolved before legal retrieval")
        if not query.strip() or top_k <= 0 or not self.chunks:
            return []
        self._validate_embedder(embedder)
        eligible = np.fromiter((self._is_valid_on(chunk, target_date) for chunk in self.chunks), dtype=bool, count=len(self.chunks))
        eligible_indices = np.flatnonzero(eligible)
        if not len(eligible_indices):
            return []

        normalized_query, query_terms = prepare_query(query)
        required_intent_terms = query_intent_terms(query)
        unigram_query_terms = [term for term in query_terms if not term.startswith("__phrase__")]
        intent_anchors: set[str] = set()
        if required_intent_terms and set(tokenize(query)) & ELIGIBILITY_MARKERS:
            generic_intent = set(tokenize(" ".join(ELIGIBILITY_MARKERS))) | required_intent_terms
            topic_terms = [term for term in unigram_query_terms if term not in generic_intent]
            by_rarity = sorted(
                topic_terms,
                key=lambda term: (len(self.bm25.postings.get(term, ())), term),
            )
            intent_anchors = set(by_rarity[:3])
        query_vector = embedder.embed_query(normalized_query)
        dense_values = cosine_scores(self.embeddings[eligible_indices], query_vector)
        dense_order = eligible_indices[np.argsort(dense_values)[::-1][:candidate_k]]
        dense_score = {int(index): float(score) for index, score in zip(eligible_indices, dense_values)}
        dense_rank = {int(index): rank for rank, index in enumerate(dense_order, 1)}

        bm25_values = self.bm25.scores(query_terms, eligible)
        bm25_nonzero = eligible_indices[bm25_values[eligible_indices] > 0]
        bm25_order = bm25_nonzero[np.argsort(bm25_values[bm25_nonzero])[::-1][:candidate_k]]
        bm25_rank = {int(index): rank for rank, index in enumerate(bm25_order, 1)}

        candidates = set(dense_rank) | set(bm25_rank)
        ranked: list[tuple[float, int, float, tuple[str, ...]]] = []
        for index in candidates:
            rrf = (DENSE_RRF_WEIGHT / (RRF_K + dense_rank[index]) if index in dense_rank else 0) + (BM25_RRF_WEIGHT / (RRF_K + bm25_rank[index]) if index in bm25_rank else 0)
            document_terms = set(self.bm25.documents[index])
            matched = tuple(term for term in query_terms if term in document_terms and not term.startswith("__phrase__"))
            unigram_terms = {term for term in query_terms if not term.startswith("__phrase__")}
            overlap = len(matched) / max(len(unigram_terms), 1)
            title_terms = set(tokenize(str(self.chunks[index].get("act_title") or "")))
            title_overlap = len(unigram_terms & title_terms) / max(len(unigram_terms), 1)
            heading = "\n".join(str(self.chunks[index].get("text") or "").splitlines()[:2])
            heading_terms = set(tokenize(heading))
            heading_overlap = len(unigram_terms & heading_terms) / max(len(unigram_terms), 1)
            # Transparent relevance-only reranker; RRF stays the dominant signal.
            reranker = 0.50 * overlap + 0.20 * title_overlap + 0.30 * heading_overlap
            final = rrf * (1.0 + reranker)
            ranked.append((final, index, reranker, matched))
        ranked.sort(reverse=True)

        accepted = []
        unigram_count = sum(not term.startswith("__phrase__") for term in set(query_terms))
        minimum_matches = 2 if unigram_count >= 4 else 1
        for final, index, reranker, matched in ranked:
            has_lexical = bm25_values[index] > 0 and len(set(matched)) >= minimum_matches
            has_two_channels = index in dense_rank and index in bm25_rank
            intent_supported = not required_intent_terms or bool(required_intent_terms & set(self.bm25.documents[index]))
            anchor_matches = len(intent_anchors & set(self.bm25.documents[index]))
            anchors_supported = not intent_anchors or anchor_matches == len(intent_anchors)
            if has_lexical and intent_supported and anchors_supported and (has_two_channels or reranker >= 0.20):
                accepted.append((final, index, reranker, matched))
            if len(accepted) >= top_k:
                break

        return [self._result(index, final, reranker, matched, dense_score, dense_rank, bm25_values, bm25_rank) for final, index, reranker, matched in accepted]

    def _result(self, index: int, final: float, reranker: float, matched: tuple[str, ...], dense_score: dict[int, float], dense_rank: dict[int, int], bm25_values: np.ndarray, bm25_rank: dict[int, int]) -> RetrievalResult:
        d_rank, b_rank = dense_rank.get(index), bm25_rank.get(index)
        rrf = (DENSE_RRF_WEIGHT / (RRF_K + d_rank) if d_rank else 0) + (BM25_RRF_WEIGHT / (RRF_K + b_rank) if b_rank else 0)
        chunk = self.chunks[index]
        article_text = self._complete_article_text(index)
        return RetrievalResult(
            text=article_text, act_title=str(chunk.get("act_title") or ""), act_type=str(chunk.get("act_type") or ""),
            article_number=chunk.get("article_number"), source_url=chunk.get("source_url"), valid_from=str(chunk["valid_from"]), valid_to=chunk.get("valid_to"),
            similarity_score=round(dense_score.get(index, 0.0), 6), final_score=round(final, 8), dense_rank=d_rank,
            bm25_score=round(float(bm25_values[index]), 6), bm25_rank=b_rank, rrf_score=round(rrf, 8),
            reranker_score=round(reranker, 6), matched_query_terms=matched,
        )

    def _complete_article_text(self, index: int) -> str:
        """Join contiguous chunks belonging to the same act article."""
        chunk = self.chunks[index]
        article = chunk.get("article_number")
        act_id = chunk.get("act_id")
        if not article:
            return str(chunk["text"])
        start = index
        while start > 0:
            previous = self.chunks[start - 1]
            if previous.get("act_id") != act_id or previous.get("article_number") != article:
                break
            start -= 1
        end = index + 1
        while end < len(self.chunks):
            following = self.chunks[end]
            if following.get("act_id") != act_id or following.get("article_number") != article:
                break
            end += 1
        return "\n".join(str(part["text"]) for part in self.chunks[start:end])

    @staticmethod
    def _is_valid_on(chunk: dict[str, Any], target_date: date) -> bool:
        valid_from = chunk.get("valid_from")
        if not valid_from:
            return False
        start = date.fromisoformat(str(valid_from))
        valid_to = chunk.get("valid_to")
        return start <= target_date and (not valid_to or target_date < date.fromisoformat(str(valid_to)))
