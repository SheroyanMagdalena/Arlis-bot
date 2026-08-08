"""Append curated demo provisions to an existing local vector index."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.retrieval.text import searchable_text
from backend.runtime.retrieval.vector_search import INDEX_FORMAT_VERSION, LocalVectorIndex


DEFAULT_VALID_FROM = {"arlis-224417": "2026-01-01"}


def _exclusive_end(value: str | None) -> str | None:
    """Convert the demo file's inclusive end date to the index's exclusive boundary."""
    return (date.fromisoformat(value) + timedelta(days=1)).isoformat() if value else None


def _to_chunk(provision: dict[str, object]) -> dict[str, object]:
    act_id = str(provision["act_id"])
    valid_from = provision.get("valid_from") or DEFAULT_VALID_FROM.get(act_id)
    if not valid_from:
        raise ValueError(f"No valid_from date for {provision.get('version_id')}")
    article_label = str(provision.get("article_label_hy") or "")
    article_number = article_label.removeprefix("Հոդված").strip() or None
    labels = " · ".join(
        str(value) for value in (article_label, provision.get("paragraph_label_hy")) if value
    )
    return {
        "chunk_id": f"demo:{provision['version_id']}",
        "act_id": act_id,
        "act_title": str(provision.get("act_title_hy") or ""),
        "act_type": "Օրենք",
        "article_number": article_number,
        "article_heading": labels,
        "valid_from": str(valid_from),
        "valid_to": _exclusive_end(provision.get("valid_to")),
        "status": "demo_curated",
        "source_url": provision.get("source_url"),
        "text": f"{labels}\n{provision.get('text_hy') or ''}".strip(),
        "demo_version_id": str(provision["version_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/demo_provisions.json"))
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    usable = [
        item for item in payload["provisions"]
        if not str(item.get("text_hy") or "").startswith("TODO_MANUAL_EXTRACTION")
    ]
    demo_chunks = [_to_chunk(item) for item in usable]
    existing = LocalVectorIndex.load(args.index, allow_legacy=True)
    demo_ids = {chunk["demo_version_id"] for chunk in demo_chunks}
    keep_indices = [
        index for index, chunk in enumerate(existing.chunks)
        if chunk.get("demo_version_id") not in demo_ids
    ]

    model_name = (existing.manifest or {}).get("embedding", {}).get("model_name", DEFAULT_MODEL)
    embedder = LocalEmbedder(model_name)
    if existing.manifest:
        existing._validate_embedder(embedder)
    elif existing.embeddings.shape[1] != embedder.dimension:
        raise ValueError(
            f"Legacy index dimension {existing.embeddings.shape[1]} does not match {embedder.dimension}"
        )
    demo_embeddings = embedder.embed_passages(
        [searchable_text(chunk) for chunk in demo_chunks], batch_size=args.batch_size
    )
    embeddings = np.concatenate((existing.embeddings[keep_indices], demo_embeddings), axis=0)
    chunks = [existing.chunks[index] for index in keep_indices] + demo_chunks
    manifest = existing.manifest or {
        "format_version": INDEX_FORMAT_VERSION,
        "embedding": embedder.configuration(),
        "searchable_representation": "act_title+act_type+article_number+text:v1",
    }
    updated = LocalVectorIndex(embeddings, chunks, manifest)

    next_dir = args.index.with_name(f"{args.index.name}.next")
    backup_dir = args.index.with_name(f"{args.index.name}.before_demo")
    if next_dir.exists():
        shutil.rmtree(next_dir)
    updated.save(next_dir)
    LocalVectorIndex.load(next_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    args.index.rename(backup_dir)
    next_dir.rename(args.index)
    skipped = len(payload["provisions"]) - len(demo_chunks)
    print(f"Imported {len(demo_chunks)} demo provisions; skipped {skipped} TODO placeholder(s)")
    print(f"Active index now has {len(chunks)} chunks")
    print(f"Previous index retained at {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
