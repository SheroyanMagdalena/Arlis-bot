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
from backend.runtime.temporal import detect_target_date, parse_target_date
from backend.runtime.retrieval.vector_search import LocalVectorIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="Natural-language search query")
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--date", help="Target legal date (YYYY-MM-DD or DD.MM.YYYY)")
    parser.add_argument("--candidate-k", type=int, default=50)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--allow-legacy-index", action="store_true", help="Explicitly accept an index without a model manifest")
    args = parser.parse_args()

    query = args.query or input("Search: ").strip()
    temporal = detect_target_date(query)
    if args.date:
        target_date = parse_target_date(args.date)
        date_source = "--date"
    elif temporal.target_date:
        target_date = temporal.target_date
        date_source = temporal.reference_text or "question"
    else:
        target_date = parse_target_date(input("Target date (YYYY-MM-DD): ").strip())
        date_source = "user_selection"
    embedder = LocalEmbedder(args.model)
    index = LocalVectorIndex.load(args.index, allow_legacy=args.allow_legacy_index)
    results = index.search(
        query, embedder, top_k=args.top_k, target_date=target_date, candidate_k=args.candidate_k
    )
    output = {
        "target_date": target_date.isoformat(),
        "date_source": date_source,
        "status": "ok" if results else "no_sufficiently_relevant_legal_provision_found",
        "results": [result.as_dict() for result in results],
    }
    if not args.debug:
        hidden = {"final_score", "dense_rank", "bm25_score", "bm25_rank", "rrf_score", "reranker_score", "matched_query_terms"}
        output["results"] = [{key: value for key, value in item.items() if key not in hidden} for item in output["results"]]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
