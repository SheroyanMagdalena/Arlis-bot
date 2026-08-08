import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.ingestion.article_chunker import chunk_document
from backend.runtime.retrieval.vector_search import LocalVectorIndex


class FakeEmbedder:
    vectors = {
        "passage: աշխատանքային իրավունք": [1.0, 0.0],
        "passage: հարկային պարտավորություն": [0.0, 1.0],
        "query: աշխատանք": [1.0, 0.0],
    }

    def embed_passages(self, texts, batch_size=32):
        return np.asarray([self.vectors[f"passage: {text}"] for text in texts], dtype=np.float32)

    def embed_query(self, query):
        return np.asarray(self.vectors[f"query: {query}"], dtype=np.float32)


class RetrievalTests(unittest.TestCase):
    def test_article_chunk_metadata(self):
        chunks = list(chunk_document({
            "act_id": "1", "title": "Օրենք", "source_url": "https://example.test/1",
            "text": "Նախաբան\nՀոդված 1. Առաջին տեքստ\nՀոդված 2. Երկրորդ տեքստ",
        }))
        self.assertEqual([chunk["article_number"] for chunk in chunks], [None, "1", "2"])

    def test_returns_ranked_result_and_persists_index(self):
        chunks = [
            {"text": "աշխատանքային իրավունք", "act_title": "Աշխատանքային օրենսգիրք", "article_number": "1", "source_url": "https://example.test/1"},
            {"text": "հարկային պարտավորություն", "act_title": "Հարկային օրենսգիրք", "article_number": "2", "source_url": "https://example.test/2"},
        ]
        embedder = FakeEmbedder()
        index = LocalVectorIndex.build(chunks, embedder)
        with tempfile.TemporaryDirectory() as directory:
            index.save(directory)
            loaded = LocalVectorIndex.load(directory)
            results = loaded.search("աշխատանք", embedder, top_k=1)
        self.assertEqual(results[0].act_title, "Աշխատանքային օրենսգիրք")
        self.assertEqual(results[0].article_number, "1")
        self.assertEqual(results[0].similarity_score, 1.0)


if __name__ == "__main__":
    unittest.main()
