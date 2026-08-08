import unittest

from backend.runtime.intent.classifier import classify_temporal


class TemporalClassifierTests(unittest.TestCase):
    def test_detects_armenian_temporal_keyword(self):
        detection = classify_temporal("Այսօր ի՞նչ իրավունքներ ունեմ աշխատանքից ազատվելու դեպքում")
        self.assertTrue(detection.is_temporal)
        self.assertIn("այսօր", detection.matched_terms)

    def test_detects_english_temporal_keyword(self):
        detection = classify_temporal("What is the minimum wage today?")
        self.assertTrue(detection.is_temporal)
        self.assertIn("today", detection.matched_terms)

    def test_detects_russian_temporal_keyword(self):
        detection = classify_temporal("Какая сейчас минимальная зарплата?")
        self.assertTrue(detection.is_temporal)
        self.assertIn("сейчас", detection.matched_terms)

    def test_detects_explicit_date(self):
        detection = classify_temporal("Ինչպիսի՞ն էր օրենքը 2019 թ.")
        self.assertTrue(detection.is_temporal)
        self.assertTrue(detection.detected_dates)

    def test_plain_legal_question_is_not_temporal(self):
        detection = classify_temporal("Ի՞նչ է աշխատանքային օրենսգիրքը")
        self.assertFalse(detection.is_temporal)
        self.assertEqual(detection.matched_terms, [])
        self.assertEqual(detection.detected_dates, [])

    def test_does_not_false_positive_on_substring(self):
        # "know" contains the substring "now"; must not match as a whole word.
        detection = classify_temporal("Do you know the rules for parental leave?")
        self.assertFalse(detection.is_temporal)


if __name__ == "__main__":
    unittest.main()
