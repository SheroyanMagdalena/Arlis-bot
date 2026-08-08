"""Build a local ARLIS vector index from the compressed dump."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.article_chunker import chunk_document
from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.ingestion.parser import iter_records
from backend.ingestion.version_resolver import select_recommended_act_ids
from backend.runtime.retrieval.vector_search import LocalVectorIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, default=Path("data/raw/arlis_documents.jsonl.xz"))
    parser.add_argument("--output", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--metadata", type=Path, default=Path("data/raw/arlis_metadata.jsonl"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-documents", type=int, default=0, help="Optional development limit")
    parser.add_argument(
        "--corpus",
        choices=("recommended", "all"),
        default="recommended",
        help="Recommended selects deduplicated active Armenian laws and codes",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    limit = args.max_documents or None
    act_ids = (
        select_recommended_act_ids(args.metadata)
        if args.corpus == "recommended"
        else None
    )
    if act_ids is not None:
        print(f"Selected {len(act_ids)} deduplicated active Armenian laws/codes")
    chunks = [
        chunk
        for document in iter_records(args.dump, limit=limit, act_ids=act_ids)
        for chunk in chunk_document(document)
    ]
    print(f"Embedding {len(chunks)} chunks from {limit or 'all'} documents...")
    embedder = LocalEmbedder(args.model)
    index = LocalVectorIndex.build(chunks, embedder, batch_size=args.batch_size)
    index.save(args.output)
    print(f"Saved local index to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
