"""Small manually-labelled Armenian legal retrieval evaluation."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.retrieval.vector_search import LocalVectorIndex


CASES = [
    ("Սովորական աշխատանքային պայմանագրով աշխատողի փորձաշրջանի առավելագույն ժամկետը որքա՞ն է", "աշխատանքային օրենսգիրք", "92"),
    ("ես ստանում եմ հարյուր հիսուն հազար աշխատավարձ կարող եմ օգտվել առողջության ապահովագրությունից", "առողջ", None),
    ("Քանի՞ օր է ամենամյա նվազագույն արձակուրդը", "աշխատանքային օրենսգիրք", "159"),
    ("Կարո՞ղ են աշխատողին ազատել առանց նախազգուշացման", "աշխատանքային օրենսգիրք", "115"),
    ("Ինչպե՞ս է գրանցվում սահմանափակ պատասխանատվությամբ ընկերությունը", "սահմանափակ պատասխանատվությամբ ընկերությունների մասին", None),
    ("Վարձակալը պարտավո՞ր է վճարել բնակարանի վերանորոգման համար", "քաղաքացիական օրենսգիրք", None),
    ("Ժառանգությունն ընդունելու ժամկետը որքա՞ն է", "քաղաքացիական օրենսգիրք", None),
    ("Ամուսնալուծության համար ո՞ւր պետք է դիմել", "ընտանեկան օրենսգիրք", None),
    ("Եկամտային հարկի դրույքաչափը որքա՞ն է", "հարկային օրենսգիրք", None),
    ("Սպառողը կարո՞ղ է վերադարձնել անորակ ապրանքը", "սպառողների իրավունքների պաշտպանության մասին", None),
]


def relevant(result, expected_title: str, expected_article: str | None) -> bool:
    title_ok = expected_title.casefold() in result.act_title.casefold()
    return title_ok and (expected_article is None or result.article_number == expected_article)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--date", default="2023-04-01")
    parser.add_argument("--allow-legacy-index", action="store_true")
    args = parser.parse_args()
    embedder = LocalEmbedder(args.model)
    index = LocalVectorIndex.load(args.index, allow_legacy=args.allow_legacy_index)
    target = date.fromisoformat(args.date)
    hits5 = hits10 = reciprocal_sum = 0.0
    labelled = 0
    for query, title, article in CASES:
        results = index.search(query, embedder, top_k=10, target_date=target)
        rank = next((rank for rank, result in enumerate(results, 1) if relevant(result, title, article)), None)
        if title == "առողջ" and rank is None:
            print(f"MISS/NO-PROVISION | {query}")
            continue
        labelled += 1
        hits5 += bool(rank and rank <= 5)
        hits10 += bool(rank and rank <= 10)
        reciprocal_sum += 1 / rank if rank else 0
        print(f"rank={rank or '-':>2} | {query}")
    denominator = max(labelled, 1)
    print(f"Recall@5={hits5 / denominator:.3f} Recall@10={hits10 / denominator:.3f} MRR={reciprocal_sum / denominator:.3f} labelled={labelled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
