import unittest

from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.verification.confidence_checker import is_confident


def _result(similarity_score: float) -> RetrievalResult:
    return RetrievalResult(
        text="text",
        act_title="Օրենք",
        article_number="1",
        source_url="https://example.test/1",
        similarity_score=similarity_score,
    )


class ConfidenceCheckerTests(unittest.TestCase):
    def test_empty_results_are_not_confident(self):
        self.assertFalse(is_confident([], threshold=0.75))

    def test_score_at_threshold_is_confident(self):
        self.assertTrue(is_confident([_result(0.75)], threshold=0.75))

    def test_score_below_threshold_is_not_confident(self):
        self.assertFalse(is_confident([_result(0.74)], threshold=0.75))

    def test_score_above_threshold_is_confident(self):
        self.assertTrue(is_confident([_result(0.9)], threshold=0.75))


if __name__ == "__main__":
    unittest.main()
