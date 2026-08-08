import unittest

from backend.runtime.clarification.missing_information import needs_reference_date
from backend.runtime.retrieval.schemas import RetrievalResult


def _result(text: str, similarity_score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        text=text,
        act_title="Օրենք",
        article_number="1",
        source_url="https://example.test/1",
        similarity_score=similarity_score,
    )


class MissingInformationTests(unittest.TestCase):
    def test_child_benefit_question_needs_reference_date(self):
        question = "Որքա՞ն է մանկական նպաստի չափը"
        results = [_result("Նպաստի չափը կախված է...")]
        self.assertTrue(needs_reference_date(question, results))

    def test_plain_question_does_not_need_reference_date(self):
        question = "Ի՞նչ է աշխատանքային օրենսգիրքը"
        results = [_result("Աշխատանքային օրենսգիրքը կարգավորում է...")]
        self.assertFalse(needs_reference_date(question, results))

    def test_date_conditional_chunk_text_triggers_even_without_topic_keyword(self):
        question = "Ի՞նչ իրավունքներ ունեմ"
        results = [_result("Իրավունքը գործում է 18 տարեկան հասակից մինչև 23 տարեկան հասակը")]
        self.assertTrue(needs_reference_date(question, results))

    def test_matches_inflected_forms_of_the_topic_noun(self):
        # Armenian case suffixes attach directly to the stem with no space, so the
        # dictionary form "նպաստ" (benefit) must still be caught in its genitive
        # ("նպաստի"), instrumental ("նպաստով"), ablative ("նպաստից"), and plural
        # ("նպաստներ") forms.
        results = [_result("Նպաստի չափը կախված է...")]
        for question in [
            "Ինչպե՞ս եմ ստանում մանկական նպաստով",
            "Ի՞նչ է փոխվում մանկական նպաստից",
            "Քանի՞ մանկական նպաստներ կան",
        ]:
            with self.subTest(question=question):
                self.assertTrue(needs_reference_date(question, results))

    def test_matches_topic_words_with_a_modifier_inserted_between_them(self):
        # Real-data finding: "նվազագույն ամսական աշխատավարձ" (minimum MONTHLY wage,
        # the real act's actual title) inserts "ամսական" between the two words of
        # the curated topic "նվազագույն աշխատավարձ". A literal contiguous-phrase
        # match misses this; matching must tolerate words in between.
        question = "Ինչքա՞ն է նվազագույն ամսական աշխատավարձը"
        results = [_result("Աշխատավարձի չափը սահմանվում է...")]
        self.assertTrue(needs_reference_date(question, results))

    def test_does_not_match_topic_as_a_fragment_of_an_unrelated_word(self):
        # Leading boundary must still prevent "կենսաթոշակ" (pension) from matching
        # when it's fused mid-word with no boundary before it, e.g. a fabricated
        # compound "մեծկենսաթոշակ" ("մեծ" + "կենսաթոշակ" with no space) — the
        # topic substring is present, but not as a real standalone occurrence.
        question = "մեծկենսաթոշակ ինչ-որ անհարկի բառ"
        results = [_result("Անկապ տեքստ")]
        self.assertFalse(needs_reference_date(question, results))


if __name__ == "__main__":
    unittest.main()
