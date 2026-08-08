import unittest
from datetime import date
from unittest.mock import patch

from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.verification.confidence_checker import ConfidenceLevel


class FakeIndex:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def search(self, query, embedder, *, top_k=5):
        return self._results


def _result(similarity_score: float, text: str = "Հոդվածի տեքստ") -> RetrievalResult:
    return RetrievalResult(
        text=text,
        act_title="Օրենք",
        article_number="1",
        source_url="https://example.test/1",
        similarity_score=similarity_score,
    )


class RollbackPipelineTests(unittest.TestCase):
    def test_non_temporal_confident_question_is_verified(self):
        index = FakeIndex([_result(0.9)])
        result = run_rollback("Ի՞նչ է աշխատանքային օրենսգիրքը", index, embedder=None)
        self.assertIsInstance(result, RollbackAnswer)
        self.assertEqual(result.confidence_level, ConfidenceLevel.VERIFIED)
        self.assertEqual(result.source, "rag")

    def test_non_temporal_low_confidence_is_no_answer_without_deepseek(self):
        index = FakeIndex([_result(0.2)])
        with patch("backend.runtime.pipeline.ask_deepseek") as mock_ask:
            result = run_rollback("Ինչ-որ անհասկանալի հարց", index, embedder=None)
        mock_ask.assert_not_called()
        self.assertEqual(result.confidence_level, ConfidenceLevel.NO_ANSWER)
        self.assertEqual(result.source, "none")

    def test_child_benefit_question_first_asks_for_a_date(self):
        index = FakeIndex([_result(0.9, text="Նպաստի չափը կախված է ծննդյան տարեդարձից")])
        result = run_rollback("Որքա՞ն է մանկական նպաստի չափը", index, embedder=None)
        self.assertIsInstance(result, ClarificationRequest)
        self.assertEqual(result.field, "reference_date")
        self.assertEqual(result.input_type, "date_picker")

    def test_child_benefit_question_with_date_inside_corpus_window_is_grounded_but_dated(self):
        index = FakeIndex([_result(0.9)])
        result = run_rollback(
            "Որքա՞ն է մանկական նպաստի չափը",
            index,
            embedder=None,
            reference_date=date(2022, 1, 1),
        )
        self.assertIsInstance(result, RollbackAnswer)
        self.assertEqual(result.confidence_level, ConfidenceLevel.GROUNDED_BUT_DATED)
        self.assertEqual(result.source, "rag")

    def test_date_after_corpus_cutoff_skips_rag_and_calls_deepseek(self):
        index = FakeIndex([_result(0.95)])
        with patch(
            "backend.runtime.pipeline.ask_deepseek", return_value="External answer"
        ) as mock_ask:
            result = run_rollback(
                "Որքա՞ն է մանկական նպաստի չափը",
                index,
                embedder=None,
                reference_date=date(2024, 1, 1),
            )
        mock_ask.assert_called_once()
        self.assertEqual(result.confidence_level, ConfidenceLevel.EXTERNAL_UNVERIFIED)
        self.assertEqual(result.source, "deepseek")
        self.assertEqual(result.answer, "External answer")

    def test_temporal_question_low_confidence_falls_back_to_deepseek(self):
        index = FakeIndex([_result(0.1)])
        with patch(
            "backend.runtime.pipeline.ask_deepseek", return_value="Current answer"
        ):
            result = run_rollback("Ինչպիսի՞ն է օրենքը այսօր", index, embedder=None)
        self.assertEqual(result.confidence_level, ConfidenceLevel.EXTERNAL_UNVERIFIED)
        self.assertEqual(result.source, "deepseek")

    def test_temporal_question_deepseek_failure_is_no_answer(self):
        index = FakeIndex([_result(0.1)])
        with patch("backend.runtime.pipeline.ask_deepseek", return_value=None):
            result = run_rollback("Ինչպիսի՞ն է օրենքը այսօր", index, embedder=None)
        self.assertEqual(result.confidence_level, ConfidenceLevel.NO_ANSWER)
        self.assertEqual(result.source, "none")


if __name__ == "__main__":
    unittest.main()
