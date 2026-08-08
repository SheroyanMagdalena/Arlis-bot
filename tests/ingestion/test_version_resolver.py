import json
import tempfile
import unittest
from pathlib import Path

from backend.ingestion.version_resolver import select_recommended_act_ids, select_temporal_act_ids


class VersionResolverTests(unittest.TestCase):
    def test_selects_latest_active_armenian_law_snapshot(self):
        records = [
            {"uniqid": "10", "language": "AM", "ActStatus": "Գործում է", "ActType": "Օրենք", "ActNumber": "ՀՕ-1", "title": "Օրենք", "EnactmentDate": "01.01.2020", "EnactmentOrgan": "ԱԺ"},
            {"uniqid": "20", "language": "AM", "ActStatus": "Գործում է", "ActType": "Օրենք", "ActNumber": "ՀՕ-1", "title": "Օրենք", "EnactmentDate": "01.01.2020", "EnactmentOrgan": "ԱԺ"},
            {"uniqid": "30", "language": "AM", "ActStatus": "Չի գործում", "ActType": "Օրենք", "ActNumber": "ՀՕ-2", "title": "Հին օրենք", "EnactmentDate": "01.01.2010", "EnactmentOrgan": "ԱԺ"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.jsonl"
            path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")
            selected = select_recommended_act_ids(path)
        self.assertEqual(selected, {"20"})

    def test_temporal_corpus_keeps_dated_supported_versions(self):
        records = [
            {"uniqid": "10", "language": "AM", "ActType": "Օրենք", "EffectiveDate": "01.01.2020"},
            {"uniqid": "11", "language": "AM", "ActType": "Որոշում", "EffectiveDate": "01.01.2018", "InterruptDate": "01.01.2020"},
            {"uniqid": "12", "language": "RU", "ActType": "Օրենք", "EffectiveDate": "01.01.2020"},
            {"uniqid": "13", "language": "AM", "ActType": "Համաձայնագիր", "EffectiveDate": "01.01.2020"},
            {"uniqid": "14", "language": "AM", "ActType": "Հրաման"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.jsonl"
            path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")
            selected = select_temporal_act_ids(path)
        self.assertEqual(selected, {"10", "11"})


if __name__ == "__main__":
    unittest.main()
