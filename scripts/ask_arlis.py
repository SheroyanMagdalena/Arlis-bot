"""Run a question through the rollback pipeline end to end."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.vector_search import LocalVectorIndex


def _answer_to_dict(answer: RollbackAnswer) -> dict:
    return {
        "answer": answer.answer,
        "confidence_level": answer.confidence_level.value,
        "disclaimer": answer.disclaimer,
        "source": answer.source,
        "citations": [citation.as_dict() for citation in answer.citations],
        "reference_date": (
            answer.reference_date.isoformat() if answer.reference_date else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="Natural-language legal question")
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    query = args.query or input("Question: ").strip()
    index = LocalVectorIndex.load(args.index)
    embedder = LocalEmbedder(args.model)

    result = run_rollback(query, index, embedder, top_k=args.top_k)

    if isinstance(result, ClarificationRequest):
        raw_date = input(f"{result.prompt} (YYYY-MM-DD): ").strip()
        reference_date = date.fromisoformat(raw_date)
        result = run_rollback(
            query, index, embedder, reference_date=reference_date, top_k=args.top_k
        )

    print(json.dumps(_answer_to_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
