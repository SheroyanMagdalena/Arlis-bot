import unittest
from datetime import date

from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.rental_tax import calculate_2019_rental_tax
from backend.runtime.verification.confidence_checker import ConfidenceLevel


QUESTION = (
    "Ես բնակարանս վարձակալության եմ տվել և տարվա ընթացքում ստացել եմ 70 միլիոն "
    "դրամ վարձակալական վճար։ 2019 թվականի դեկտեմբերի 15-ի դրությամբ որքա՞ն "
    "եկամտային հարկ պետք է վճարեի"
)


class RentalTaxTests(unittest.TestCase):
    def test_2019_threshold_and_tax_are_exact(self):
        result = calculate_2019_rental_tax(QUESTION, date(2019, 12, 15))
        self.assertIsNotNone(result)
        self.assertEqual(result.gross_income, 70_000_000)
        self.assertEqual(result.threshold, 58_350_000)
        self.assertEqual(result.tax_due, 8_165_000)

    def test_pipeline_returns_verified_article_150_answer_without_search(self):
        answer = run_rollback(
            QUESTION,
            index=None,
            embedder=None,
            reference_date=date(2019, 12, 15),
        )
        self.assertEqual(answer.confidence_level, ConfidenceLevel.VERIFIED)
        self.assertIn("8,165,000", answer.answer)
        self.assertEqual(answer.citations[0].article_number, "150, մաս 7")

    def test_rule_does_not_apply_to_other_years(self):
        self.assertIsNone(calculate_2019_rental_tax(QUESTION, date(2020, 1, 1)))


if __name__ == "__main__":
    unittest.main()
