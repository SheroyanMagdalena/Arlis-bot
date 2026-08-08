"""API server for the ARLIS Assistant frontend (apps/web).

Serves POST /api/research, matching the contract the React app already calls
(see apps/web/src/App.jsx and apps/web/vite.config.js, which proxies /api to
this server on port 8000). Zero extra dependencies -- stdlib http.server only,
consistent with the rest of this project's tooling.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.ingestion.embedding_generator import DEFAULT_MODEL, LocalEmbedder
from backend.runtime.clarification.schemas import ClarificationRequest
from backend.runtime.pipeline import run_rollback
from backend.runtime.reasoning.schemas import RollbackAnswer
from backend.runtime.retrieval.vector_search import LocalVectorIndex

INDEX: LocalVectorIndex
EMBEDDER: LocalEmbedder


def _result_to_frontend_shape(result_dict: dict) -> dict:
    return {
        "act_title": result_dict["act_title"],
        "article_number": result_dict["article_number"],
        "text": result_dict["text"],
        "act_type": None,
        "valid_from": None,
        "valid_to": None,
        "similarity_score": result_dict["similarity_score"],
        "source_url": result_dict["source_url"],
    }


def _answer_to_research_response(answer: RollbackAnswer) -> dict:
    results = [
        _result_to_frontend_shape(citation.as_dict()) for citation in answer.citations
    ]
    response: dict = {
        "results": results,
        "source_count": len(results),
        "confidence_level": answer.confidence_level.value,
    }
    if answer.source == "none":
        response["simplified_answer"] = None
        response["answer_error"] = answer.disclaimer
    elif answer.source == "deepseek":
        # Not grounded in a specific citation -- surface the pipeline's own answer
        # text as the simplified answer instead of a RAG chunk.
        response["simplified_answer"] = answer.answer or None
        if answer.disclaimer:
            response["warning"] = answer.disclaimer
    else:
        response["simplified_answer"] = None
        if answer.disclaimer:
            response["warning"] = answer.disclaimer
    return response


def _clarification_response(clarification: ClarificationRequest) -> dict:
    return {
        "results": [],
        "source_count": 0,
        "simplified_answer": None,
        "needs_date": True,
        "date_prompt": clarification.prompt,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        pass

    def do_POST(self) -> None:
        if self.path != "/api/research":
            self._send_json({"detail": "Not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            top_k = int(payload.get("top_k") or 5)
            raw_date = payload.get("target_date")
            reference_date = date.fromisoformat(raw_date) if raw_date else None

            if not question:
                self._send_json({"detail": "question is required"}, status=400)
                return

            result = run_rollback(
                question, INDEX, EMBEDDER, reference_date=reference_date, top_k=top_k
            )
            if isinstance(result, ClarificationRequest):
                self._send_json(_clarification_response(result))
            else:
                self._send_json(_answer_to_research_response(result))
        except Exception as error:  # noqa: BLE001 -- surface as a clean API error
            self._send_json({"detail": str(error)}, status=500)

    def _send_json(self, data: dict, *, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
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
    print(f"Ready. POST /api/research on http://127.0.0.1:{args.port}")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
