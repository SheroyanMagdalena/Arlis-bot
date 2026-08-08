import unittest
from pathlib import Path

from backend.ingestion.parser import find_by_act_number, iter_records, parse_record


class ArlisParserTests(unittest.TestCase):
    def test_maps_dump_fields_to_target_schema(self) -> None:
        parsed = parse_record({
            "uniqid": "12345",
            "title": "ՀՀ աշխատանքային օրենսգիրք",
            "ActType": "Օրենսգիրք",
            "ActStatus": "Գործում է",
            "EffectiveDate": "21.06.2005",
            "EnactmentDate": "09.11.2004",
            "pdf_link": "https://pdf.arlis.am/12345",
            "body": "<div><p>Առաջին հոդված</p><p>Երկրորդ հոդված</p></div>",
        })
        self.assertEqual(parsed, {
            "act_id": "12345",
            "title": "ՀՀ աշխատանքային օրենսգիրք",
            "act_type": "Օրենսգիրք",
            "status": "active",
            "effective_date": "2005-06-21",
            "interruption_date": None,
            "enactment_date": "2004-11-09",
            "source_url": "https://pdf.arlis.am/12345",
            "text": "Առաջին հոդված\nԵրկրորդ հոդված",
        })

    def test_parses_records_from_real_compressed_dump(self) -> None:
        dump = Path("data/raw/arlis_documents.jsonl.xz")
        if not dump.exists():
            self.skipTest(f"Real dump is not available: {dump}")
        records = list(iter_records(dump, limit=3))
        self.assertEqual(len(records), 3)
        for record in records:
            self.assertEqual(set(record), {"act_id", "title", "act_type", "status", "effective_date", "interruption_date", "enactment_date", "source_url", "text"})
            self.assertTrue(record["act_id"])
            self.assertTrue(record["title"])
            self.assertTrue(record["text"])
            self.assertTrue(record["source_url"])

    def test_finds_n_218_in_real_dump(self) -> None:
        dump = Path("data/raw/arlis_documents.jsonl.xz")
        if not dump.exists():
            self.skipTest(f"Real dump is not available: {dump}")
        record = next(find_by_act_number(dump, "  n   218  "))
        self.assertEqual(record["act_id"], "6611")
        self.assertEqual(record["status"], "active")
        self.assertEqual(record["effective_date"], "1998-04-02")


if __name__ == "__main__":
    unittest.main()
