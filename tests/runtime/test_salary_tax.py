import unittest
from datetime import date

from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.salary_tax import calculate_salary_tax
from backend.runtime.verification.confidence_checker import ConfidenceLevel


QUESTION = (
    "Ես աշխատում եմ նույն գործատուի մոտ և ամսական ստանում եմ 500,000 դրամ "
    "աշխատավարձ։ 2021 թվականի փետրվարի 15-ի դրությամբ որքա՞ն եկամտային հարկ "
    "պետք է պահվեր իմ աշխատավարձից"
)


class SalaryTaxTests(unittest.TestCase):
    def test_2021_salary_tax_is_22_percent(self):
        result = calculate_salary_tax(QUESTION, date(2021, 2, 15))
        self.assertIsNotNone(result)
        self.assertEqual(result.gross_salary, 500_000)
        self.assertEqual(result.rate_percent, 22)
        self.assertEqual(result.tax_due, 110_000)

    def test_pipeline_returns_verified_article_150_answer(self):
        answer = run_rollback(
            QUESTION,
            index=None,
            embedder=None,
            reference_date=date(2021, 2, 15),
        )
        self.assertEqual(answer.confidence_level, ConfidenceLevel.VERIFIED)
        self.assertIn("110,000", answer.answer)
        self.assertEqual(answer.citations[0].article_number, "150, մաս 1")

    def test_supported_rate_schedule(self):
        expected = {2020: 23, 2021: 22, 2022: 21, 2023: 20}
        for year, rate in expected.items():
            with self.subTest(year=year):
                result = calculate_salary_tax(QUESTION, date(year, 1, 1))
                self.assertEqual(result.rate_percent, rate)


if __name__ == "__main__":
    unittest.main()
