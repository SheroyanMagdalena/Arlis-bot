import unittest
from unittest.mock import patch

from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.verification.confidence_checker import is_confident


def _result(similarity_score: float, text: str = "Աշխատանքային իրավունքի մասին տեքստ") -> RetrievalResult:
    return RetrievalResult(
        text=text,
        act_title="Օրենք",
        article_number="1",
        source_url="https://example.test/1",
        similarity_score=similarity_score,
    )


_MOD = "backend.runtime.verification.confidence_checker.check_relevance"


class ConfidenceCheckerTests(unittest.TestCase):
    def test_empty_results_are_not_confident(self):
        self.assertFalse(is_confident("Աշխատանքային իրավունք", [], threshold=0.75))

    def test_score_below_threshold_is_not_confident_without_calling_llm(self):
        with patch(_MOD) as mock_relevance:
            result = is_confident("Հարց", [_result(0.5)], threshold=0.75)
        mock_relevance.assert_not_called()
        self.assertFalse(result)

    def test_llm_confirms_relevant_is_confident(self):
        with patch(_MOD, return_value=True):
            result = is_confident("Ի՞նչ է աշխատանքային իրավունքը", [_result(0.9)], threshold=0.75)
        self.assertTrue(result)

    def test_llm_denies_relevance_is_not_confident(self):
        # Real bug found live: "Ես ստանում եմ 150.000 դրամ աշխատավարձ, արդյոք
        # կարող եմ օգտվել առողջապահական ապահովագրությունից" (health insurance)
        # matched a drunk-driving penalty article at 0.825 similarity, and even
        # passed a lexical-overlap check on coincidentally shared word roots
        # ("աշխատավարձ" as a generic fine unit, "առողջապահության" referring to a
        # government ministry, not health insurance). Only genuine relevance
        # judgment catches this.
        with patch(_MOD, return_value=False):
            result = is_confident(
                "Ես ստանում եմ 150.000 դրամ աշխատավարձ, արդյոք կարող եմ օգտվել "
                "առողջապահական ապահովագրությունից",
                [_result(0.825)],
                threshold=0.75,
            )
        self.assertFalse(result)

    def test_llm_unavailable_falls_back_to_lexical_overlap_when_relevant(self):
        question = "Ինչքա՞ն է նվազագույն ամսական աշխատավարձը"
        relevant_text = (
            "Միջին ամսական աշխատավարձը որոշվում է աշխատողին փաստացի կատարած "
            "աշխատանքի համար հաշվարկված նվազագույն աշխատավարձի հիման վրա"
        )
        with patch(_MOD, return_value=None):
            result = is_confident(question, [_result(0.86, relevant_text)], threshold=0.75)
        self.assertTrue(result)

    def test_llm_unavailable_falls_back_to_lexical_overlap_when_not_relevant(self):
        question = (
            "Ես ստանում եմ 150.000 դրամ աշխատավարձ, արդյոք կարող եմ օգտվել "
            "առողջապահական ապահովագրությունից"
        )
        unrelated_text = (
            "Վարորդների կողմից տրանսպորտային միջոցները ոչ սթափ վիճակում վարելը "
            "առաջացնում է վարելու իրավունքից զրկում"
        )
        with patch(_MOD, return_value=None):
            result = is_confident(question, [_result(0.8, unrelated_text)], threshold=0.75)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
