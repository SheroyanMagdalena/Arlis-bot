"""Local demo UI for the rollback pipeline. Zero extra dependencies.

Loads the embedding model and vector index once at startup, then serves a
single-page UI over plain http.server. Run it and open the printed URL in a
browser -- no IDE, no separate frontend build step.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.vector_search import LocalVectorIndex

INDEX: LocalVectorIndex
EMBEDDER: LocalEmbedder

PAGE = """<!doctype html>
<html lang="hy">
<head>
<meta charset="utf-8">
<title>ARLIS Assistant -- Rollback Demo</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 780px; margin: 40px auto; padding: 0 16px; color: #1a1a1a; }
  h1 { font-size: 1.3rem; }
  textarea { width: 100%; height: 70px; font-size: 1rem; padding: 8px; box-sizing: border-box; }
  button { margin-top: 8px; padding: 8px 16px; font-size: 1rem; cursor: pointer; }
  #result { margin-top: 24px; }
  .badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.85rem; color: white; }
  .VERIFIED { background: #1e8e3e; }
  .GROUNDED_BUT_DATED { background: #e8a300; }
  .EXTERNAL_UNVERIFIED { background: #e8710a; }
  .NO_ANSWER { background: #c5221f; }
  .disclaimer { margin-top: 8px; font-style: italic; color: #555; }
  .answer { margin-top: 12px; white-space: pre-wrap; line-height: 1.5; background: #f6f6f6; padding: 12px; border-radius: 6px; }
  .citation { margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem; }
  .citation a { color: #1a56db; }
  #dateBox { display: none; margin-top: 12px; }
  #loading { display: none; margin-top: 12px; color: #555; }
</style>
</head>
<body>
<h1>ARLIS Assistant -- Rollback Demo</h1>
<p>Ask a legal question in Armenian, English, or Russian.</p>
<textarea id="question" placeholder="..."></textarea>
<br>
<button id="ask">Ask</button>
<div id="loading">Loading...</div>

<div id="dateBox">
  <p id="datePrompt"></p>
  <input type="date" id="referenceDate">
  <button id="submitDate">Submit date</button>
</div>

<div id="result"></div>

<script>
let lastQuestion = "";

async function ask(question, referenceDate) {
  document.getElementById("loading").style.display = "block";
  document.getElementById("dateBox").style.display = "none";
  document.getElementById("result").innerHTML = "";
  const body = { question };
  if (referenceDate) body.reference_date = referenceDate;
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  document.getElementById("loading").style.display = "none";

  if (data.type === "clarification") {
    lastQuestion = question;
    document.getElementById("datePrompt").textContent = data.prompt;
    document.getElementById("dateBox").style.display = "block";
    return;
  }
  render(data);
}

function render(data) {
  const citations = (data.citations || []).map(c => `
    <div class="citation">
      <strong>${c.act_title}</strong>${c.article_number ? " -- Article " + c.article_number : ""}<br>
      similarity: ${c.similarity_score}<br>
      ${c.source_url ? `<a href="${c.source_url}" target="_blank">${c.source_url}</a>` : ""}
    </div>`).join("");

  document.getElementById("result").innerHTML = `
    <span class="badge ${data.confidence_level}">${data.confidence_level}</span>
    <span style="margin-left:8px;color:#555;">source: ${data.source}${data.reference_date ? " | date: " + data.reference_date : ""}</span>
    ${data.disclaimer ? `<div class="disclaimer">${data.disclaimer}</div>` : ""}
    <div class="answer">${data.answer || "(no answer)"}</div>
    ${citations}
  `;
}

document.getElementById("ask").addEventListener("click", () => {
  const question = document.getElementById("question").value.trim();
  if (question) ask(question, null);
});

document.getElementById("submitDate").addEventListener("click", () => {
  const referenceDate = document.getElementById("referenceDate").value;
  if (referenceDate) ask(lastQuestion, referenceDate);
});
</script>
</body>
</html>
"""


def _clarification_to_dict(clarification: ClarificationRequest) -> dict:
    return {
        "type": "clarification",
        "field": clarification.field,
        "prompt": clarification.prompt,
        "input_type": clarification.input_type,
    }


def _answer_to_dict(answer: RollbackAnswer) -> dict:
    return {
        "type": "answer",
        "answer": answer.answer,
        "confidence_level": answer.confidence_level.value,
        "disclaimer": answer.disclaimer,
        "source": answer.source,
        "citations": [citation.as_dict() for citation in answer.citations],
        "reference_date": (
            answer.reference_date.isoformat() if answer.reference_date else None
        ),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/ask":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        question = str(payload.get("question", "")).strip()
        raw_date = payload.get("reference_date")
        reference_date = date.fromisoformat(raw_date) if raw_date else None

        if not question:
            self._send_json({"type": "answer", "answer": "", "confidence_level": "NO_ANSWER",
                              "disclaimer": "Empty question.", "source": "none",
                              "citations": [], "reference_date": None})
            return

        result = run_rollback(question, INDEX, EMBEDDER, reference_date=reference_date)
        if isinstance(result, ClarificationRequest):
            self._send_json(_clarification_to_dict(result))
        else:
            self._send_json(_answer_to_dict(result))

    def _send_json(self, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    global INDEX, EMBEDDER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("data/structured/vector_index_demo"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"Loading index from {args.index} ...")
    INDEX = LocalVectorIndex.load(args.index)
    print("Loading embedding model ...")
    EMBEDDER = LocalEmbedder(args.model)
    print(f"Ready. Open http://localhost:{args.port} in your browser.")

    server = ThreadingHTTPServer(("localhost", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
