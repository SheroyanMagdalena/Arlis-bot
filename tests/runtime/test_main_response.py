import unittest

from backend.main import _answer_to_research_response
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.verification.confidence_checker import ConfidenceLevel


class MainResponseTests(unittest.TestCase):
    def test_grounded_answer_is_exposed_to_frontend(self):
        citation = RetrievalResult(
            text="Հոդված 113. Գործատուի նախաձեռնությամբ լուծումը",
            act_title="ՀՀ աշխատանքային օրենսգիրք",
            article_number="113",
            source_url="https://example.test/113",
            similarity_score=0.9,
        )
        answer = RollbackAnswer(
            answer=citation.text,
            confidence_level=ConfidenceLevel.VERIFIED,
            disclaimer="",
            source="rag",
            citations=[citation],
        )

        response = _answer_to_research_response(answer)

        self.assertEqual(response["simplified_answer"], citation.text)
        self.assertEqual(response["source_count"], 1)


if __name__ == "__main__":
    unittest.main()
