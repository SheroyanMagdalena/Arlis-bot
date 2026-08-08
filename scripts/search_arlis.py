"""Search the local ARLIS vector index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.retrieval.vector_search import LocalVectorIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="Natural-language search query")
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    query = args.query or input("Search: ").strip()
    index = LocalVectorIndex.load(args.index)
    results = index.search(query, LocalEmbedder(args.model), top_k=args.top_k)
    print(json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
