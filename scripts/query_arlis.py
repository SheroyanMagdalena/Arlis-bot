"""Look up ARLIS documents by act number from the compressed dump."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.parser import find_by_act_number


DEFAULT_DUMP = Path("data/raw/arlis_documents.jsonl.xz")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("act_number", nargs="?", help='Act number, for example "N 218"')
    parser.add_argument("--all", action="store_true", help="Return every matching record")
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP, help="Path to JSONL or JSONL.XZ dump")
    parser.add_argument("--full-text", action="store_true", help="Print the complete act text")
    parser.add_argument("--preview-length", type=int, default=500, help="Text preview length (default: 500)")
    args = parser.parse_args()

    act_number = args.act_number or input("Act number: ").strip()
    records = list(find_by_act_number(args.dump, act_number, first_only=not args.all))
    if not records:
        print(json.dumps({"error": "act_not_found", "act_number": act_number}, ensure_ascii=False, indent=2))
        return 1

    if not args.full_text:
        for record in records:
            text = record.get("text") or ""
            if len(text) > args.preview_length:
                record["text"] = text[: args.preview_length].rstrip() + "..."

    output: object = records if args.all else records[0]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
