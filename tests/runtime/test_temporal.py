import unittest
from datetime import date

from backend.runtime.temporal import (
    TemporalResolutionError,
    detect_target_date,
    parse_target_date,
)


class TemporalDetectorTests(unittest.TestCase):
    def test_detects_numeric_date_in_question(self):
        result = detect_target_date("Ի՞նչ էր ասում օրենքը 12.05.2021-ին")
        self.assertEqual(result.target_date, date(2021, 5, 12))
        self.assertFalse(result.requires_user_date)

    def test_detects_armenian_date_in_question(self):
        result = detect_target_date("Ի՞նչ էր գործում 12 մայիսի 2021-ին")
        self.assertEqual(result.target_date, date(2021, 5, 12))

    def test_resolves_relative_date(self):
        result = detect_target_date("Ի՞նչ օրենք է գործում այսօր", today=date(2026, 8, 8))
        self.assertEqual(result.target_date, date(2026, 8, 8))

    def test_missing_date_requires_user_selection(self):
        result = detect_target_date("Որքա՞ն է փորձաշրջանը")
        self.assertTrue(result.requires_user_date)

    def test_rejects_incomplete_date(self):
        with self.assertRaises(TemporalResolutionError):
            parse_target_date("2021")


if __name__ == "__main__":
    unittest.main()
