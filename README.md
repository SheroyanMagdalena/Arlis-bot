# ARLIS Assistant

ARLIS Assistant is a local-first Armenian legal-document retrieval project. It
reads the ARLIS JSONL dump, normalizes legal records, splits documents into
article-aware chunks, creates multilingual embeddings, and returns the five
most relevant chunks for a natural-language question.

The current project is a retrieval baseline. It retrieves source material but
does not yet generate legal advice or a final synthesized answer.

## Implemented pipeline

```text
ARLIS JSONL.XZ dump
    -> streaming parser
    -> active Armenian law/code selection
    -> version deduplication
    -> article-aware chunks
    -> multilingual E5 embeddings
    -> local NumPy vector index
    -> top-5 cosine-similarity results
```

Each retrieval result contains:

```json
{
  "text": "Relevant legal text...",
  "act_title": "ՀՀ ԱՇԽԱՏԱՆՔԱՅԻՆ ՕՐԵՆՍԳԻՐՔ",
  "article_number": "113",
  "source_url": "https://pdf.arlis.am/...",
  "similarity_score": 0.82
}
```

`article_number` is `null` when the source uses numbered clauses rather than
formal articles.

## Data

The project currently uses the following files under `data/raw/`:

- `arlis_documents.jsonl.xz` — complete compressed ARLIS document dump
- `arlis_metadata.jsonl` — expanded metadata dump
- `arlis_metadata.jsonl.xz` — original compressed metadata dump

The parser reads the full document dump directly from XZ, so the approximately
24.6 GB expanded file is not required.

The recommended retrieval corpus includes active Armenian laws and codes. It
currently resolves to:

- 4,845 deduplicated documents
- 64,924 chunks
- 59,473 article-labelled chunks

The raw dumps and generated vector indexes are local artifacts and are not
intended to be committed to GitHub.

## Setup

From PowerShell in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The embedding model is `intfloat/multilingual-e5-small`. It is free and runs
locally. The first use downloads the model; subsequent use can work offline.

If PowerShell prevents virtual-environment activation, run commands directly
with:

```powershell
.\.venv\Scripts\python.exe <command>
```

## Parse and look up an act

Look up an act by number:

```powershell
python scripts/query_arlis.py "N 218"
```

Interactive lookup:

```powershell
python scripts/query_arlis.py
```

Useful options:

```powershell
# Print the complete act text
python scripts/query_arlis.py "N 218" --full-text

# Return every matching record when an act number is reused
python scripts/query_arlis.py "N 218" --all
```

Act numbers are not unique. For example, `N 218` occurs in multiple years and
issuing bodies. The default lookup returns the first dump match; `--all`
returns all exact matches.

## Build a vector index

Build the recommended active-Armenian corpus:

```powershell
python scripts/rebuild_index.py --corpus recommended
```

Build a smaller development index:

```powershell
python scripts/rebuild_index.py `
  --corpus recommended `
  --max-documents 100 `
  --output data/structured/vector_index_demo
```

The full CPU build is long-running. The current implementation writes the
index only after embedding finishes and is not yet resumable. Do not rely on a
partial build surviving interruption. Incremental checkpointing is the next
planned improvement.

### Current index status

The full recommended index was built successfully and exists at:

```text
data/structured/vector_index
```

It contains 64,924 chunk records and a matching `64,924 x 384` embedding
matrix. A smaller 20-document demo index also exists at:

```text
data/structured/vector_index_demo
```

## Search

Search an existing full index:

```powershell
$env:PYTHONUTF8="1"
python scripts/search_arlis.py `
  "Կարո՞ղ է գործատուն ինձ ազատել աշխատանքից առանց նախազգուշացման։" `
  --index data/structured/vector_index
```

Search the current demo index:

```powershell
python scripts/search_arlis.py `
  "գարնանային զորակոչի կազմակերպում" `
  --index data/structured/vector_index_demo
```

Interactive search:

```powershell
$env:PYTHONUTF8="1"
python scripts/search_arlis.py --index data/structured/vector_index
```

At the `Question:` prompt, enter an Armenian legal question and press Enter.
The model and index remain loaded so additional questions can be tested in the
same session. Press `Ctrl+C` to stop. Setting `PYTHONUTF8` prevents Armenian
output errors in Windows PowerShell and the VS Code terminal.

Example questions:

```text
Եթե աշխատանքի ընթացքում վնասվածք եմ ստացել, ի՞նչ պետք է անեմ։
Որքա՞ն է փորձաշրջանի առավելագույն տևողությունը։
```

The demo index is useful for pipeline testing but does not contain enough law
to answer arbitrary legal questions reliably. Search quality should be judged
by checking whether the expected act and article appear in the top five, not
by the similarity score alone.

## Tests

Run the implemented parser and retrieval tests:

```powershell
python -m unittest `
  tests.ingestion.test_version_resolver `
  tests.retrieval.test_vector_search `
  tests.end_to_end.test_arlis_parser `
  -v
```

The test suite covers:

- target-schema parsing
- real compressed-dump parsing
- act-number lookup
- article-aware chunking
- active Armenian version selection
- vector-index persistence and ranking

## Important limitations

- The source dump was last updated in April 2023.
- The source contains duplicate snapshots and reused act numbers.
- Version selection currently uses a deterministic metadata identity and keeps
  the highest numeric ARLIS identifier.
- Similarity scores indicate semantic closeness, not legal correctness.
- Retrieved passages must be checked against the cited ARLIS source.
- The system does not yet generate answers, verify claims, or validate legal
  citations.
- The corpus is limited to the selected active Armenian laws and codes; it is
  not a comprehensive index of every court or administrative decision in the
  raw dump.

## Repository safety

Before committing or pushing, make sure Git excludes the local virtual
environment, API keys, raw ARLIS dumps, generated indexes, and build logs.
Never commit a populated `.env` or `.env.example` file. Keep only a sanitized
example containing placeholder values.
