import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from backend.ingestion.article_chunker import chunk_document
from backend.runtime.retrieval.vector_search import LocalVectorIndex, cosine_scores


class FakeEmbedder:
    def embed_passages(self, texts, batch_size=32):
        return np.asarray(
            [[0.0, 1.0] if "հարկային" in text else [1.0, 0.0] for text in texts],
            dtype=np.float32,
        )

    def embed_query(self, query):
        return np.asarray([1.0, 0.0], dtype=np.float32)

    @property
    def dimension(self):
        return 2

    def configuration(self):
        return {"model_name": "fake", "dimension": 2, "normalize_embeddings": True, "query_prefix": "query: ", "passage_prefix": "passage: "}


class RetrievalTests(unittest.TestCase):
    def test_article_chunk_metadata(self):
        chunks = list(chunk_document({
            "act_id": "1", "title": "Օրենք", "source_url": "https://example.test/1",
            "text": "Նախաբան\nՀոդված 1. Առաջին տեքստ\nՀոդված 2. Երկրորդ տեքստ",
        }))
        self.assertEqual([chunk["article_number"] for chunk in chunks], [None, "1", "2"])

    def test_returns_ranked_result_and_persists_index(self):
        chunks = [
            {"text": "աշխատանքային իրավունք", "act_title": "Աշխատանքային օրենսգիրք", "act_type": "Օրենսգիրք", "article_number": "1", "source_url": "https://example.test/1", "valid_from": "2020-01-01", "valid_to": None},
            {"text": "հարկային պարտավորություն", "act_title": "Հարկային օրենսգիրք", "act_type": "Օրենսգիրք", "article_number": "2", "source_url": "https://example.test/2", "valid_from": "2020-01-01", "valid_to": None},
        ]
        embedder = FakeEmbedder()
        index = LocalVectorIndex.build(chunks, embedder)
        with tempfile.TemporaryDirectory() as directory:
            index.save(directory)
            loaded = LocalVectorIndex.load(directory)
            results = loaded.search("աշխատանք", embedder, top_k=1, target_date=date(2023, 1, 1))
        self.assertEqual(results[0].act_title, "Աշխատանքային օրենսգիրք")
        self.assertEqual(results[0].article_number, "1")
        self.assertEqual(results[0].similarity_score, 1.0)

    def test_filters_by_date_before_ranking(self):
        chunks = [
            {"text": "աշխատանքային իրավունք", "act_title": "Expired", "act_type": "Օրենք", "article_number": "1", "source_url": None, "valid_from": "2019-01-01", "valid_to": "2020-01-01"},
            {"text": "աշխատանքային պարտավորություն", "act_title": "Valid", "act_type": "Օրենք", "article_number": "2", "source_url": None, "valid_from": "2020-01-01", "valid_to": None},
        ]
        index = LocalVectorIndex.build(chunks, FakeEmbedder())
        results = index.search("աշխատանք", FakeEmbedder(), top_k=2, target_date=date(2021, 1, 1))
        self.assertEqual([result.act_title for result in results], ["Valid"])

    def test_requires_target_date(self):
        chunk = {"text": "աշխատանքային իրավունք", "act_title": "Law", "valid_from": "2020-01-01"}
        index = LocalVectorIndex.build([chunk], FakeEmbedder())
        with self.assertRaisesRegex(ValueError, "target_date"):
            index.search("աշխատանք", FakeEmbedder())

    def test_cosine_similarity_is_numerically_correct(self):
        matrix = np.asarray([[2.0, 0.0], [1.0, 1.0], [-3.0, 0.0]], dtype=np.float32)
        scores = cosine_scores(matrix, np.asarray([1.0, 0.0], dtype=np.float32))
        np.testing.assert_allclose(scores, [1.0, 2 ** -0.5, -1.0], rtol=1e-6)

    def test_manifest_rejects_incompatible_embedder(self):
        chunks = [{"text": "աշխատանք", "act_title": "Օրենք", "valid_from": "2020-01-01"}]
        index = LocalVectorIndex.build(chunks, FakeEmbedder())
        index.manifest["embedding"]["model_name"] = "different"
        with self.assertRaisesRegex(ValueError, "model_name"):
            index.search("աշխատանք", FakeEmbedder(), target_date=date(2023, 1, 1))

    def test_hybrid_prefers_exact_legal_term_over_dense_false_positive(self):
        chunks = [
            {"text": "Հոդված 92. Փորձաշրջանի ժամկետը չի կարող գերազանցել երեք ամիսը", "act_title": "ՀՀ աշխատանքային օրենսգիրք", "act_type": "Օրենսգիրք", "article_number": "92", "valid_from": "2020-01-01"},
            {"text": "Նավակի հաշվառման վարչական ժամկետ", "act_title": "Նավակների մասին որոշում", "act_type": "Որոշում", "article_number": "4", "valid_from": "2020-01-01"},
        ]
        index = LocalVectorIndex.build(chunks, FakeEmbedder())
        results = index.search("աշխատողի փորձաշրջանի առավելագույն ժամկետը", FakeEmbedder(), top_k=2, target_date=date(2023, 1, 1))
        self.assertEqual(results[0].article_number, "92")
        self.assertNotIn("Նավակ", results[0].act_title)


if __name__ == "__main__":
    unittest.main()
