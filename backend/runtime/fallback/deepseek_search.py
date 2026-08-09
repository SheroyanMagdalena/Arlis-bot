"""External fallback search via the DeepSeek chat-completion API.

Used only when the local ARLIS corpus cannot confidently answer a time-sensitive
question. Any failure (missing key, network error, bad response) degrades to
`None` so the pipeline can fall back to a LEVEL 4 "no answer" instead of crashing.
"""

from __future__ import annotations

from datetime import date

import requests

from backend.runtime.retrieval.schemas import RetrievalResult
from backend.shared.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

_SYSTEM_PROMPT = (
    "ROLE: Expert legal researcher specializing in Armenian law, consulted when "
    "the verified local ARLIS legal database could not confidently answer the "
    "question on its own.\n\n"
    "LANGUAGE: Respond in the same language the question was asked in.\n\n"
    "SOURCES: You may be given candidate excerpts retrieved from the ARLIS legal "
    "database that scored below the confidence threshold -- they are leads, not "
    "confirmed answers. Use any excerpt that is actually relevant, citing it by "
    "act title and article number. Where the excerpts are missing, insufficient, "
    "or irrelevant, fill the gap with general knowledge and say so explicitly. "
    "Prefer the current codified act over separate historical amending acts when "
    "they appear to conflict.\n\n"
    "OUTPUT STRUCTURE: 2-4 concise sentences, no headings or Markdown, and no more "
    "than 600 characters total.\n"
    "1. Direct answer — grounded in the provided ARLIS excerpts wherever they "
    "apply, supplemented by general knowledge where they don't.\n"
    "2. Legal basis — name the specific Armenian law or act that governs this, "
    "citing the excerpt's act/article number when you used one, or your general "
    "knowledge of Armenian law otherwise.\n"
    "3. Confidence — state plainly which parts came from the ARLIS excerpts "
    "(more reliable) versus general knowledge (less reliable, possibly "
    "outdated).\n\n"
    "CONSTRAINT: Read every supplied excerpt through its end before answering. "
    "Never claim that a legal basis is absent when it appears later in an excerpt. "
    "Never invent a specific number, date, or article citation you are not confident "
    "about — say it needs verification instead of guessing."
)

_RELEVANCE_SYSTEM_PROMPT = (
    "You judge whether a retrieved legal text actually answers a user's question. "
    "Word-overlap or shared legal boilerplate does not count as relevant -- the text "
    "must substantively address what the question is asking. Reply with exactly one "
    "word: YES or NO."
)

_TIMEOUT_SECONDS = 45


def _chat_completion(
    system_prompt: str, user_content: str, *, temperature: float = 0.3
) -> str | None:
    if not DEEPSEEK_API_KEY:
        return None
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "stream": False,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return content.strip() or None
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


_MAX_CONTEXT_EXCERPTS = 3
_MAX_EXCERPT_CHARS = 3000


def _format_context(results: list[RetrievalResult]) -> str:
    excerpts = []
    for i, result in enumerate(results[:_MAX_CONTEXT_EXCERPTS], start=1):
        heading = result.act_title
        if result.article_number:
            heading += f", Article {result.article_number}"
        text = result.text
        if len(text) > _MAX_EXCERPT_CHARS:
            text = text[:_MAX_EXCERPT_CHARS] + "..."
        excerpts.append(f"[{i}] {heading} (similarity {result.similarity_score:.2f}):\n{text}")
    return "\n\n".join(excerpts)


def ask_deepseek(
    question: str,
    *,
    reference_date: date | None = None,
    context_results: list[RetrievalResult] | None = None,
) -> str | None:
    user_content = question
    if reference_date is not None:
        user_content = (
            f"BINDING REFERENCE DATE: {reference_date.isoformat()}. Answer only "
            "under the law in force on that date. Do not substitute today's law "
            "or describe a later amendment as applicable. State the reference date "
            f"in the answer.\n\nQuestion: {question}"
        )
    if context_results:
        user_content = (
            f"{user_content}\n\n"
            "Candidate ARLIS excerpts (below the confidence threshold -- judge "
            f"relevance yourself):\n{_format_context(context_results)}"
        )
    return _chat_completion(_SYSTEM_PROMPT, user_content, temperature=0.3)


def check_relevance(question: str, text: str) -> bool | None:
    """Ask the LLM whether retrieved text actually answers the question.

    Returns True/False, or None if the check itself could not be performed (no
    API key, network failure, or an unparseable response) -- callers should treat
    None as "unknown" and fall back to their own heuristic rather than assuming
    relevance.
    """
    user_content = f"Question: {question}\n\nRetrieved text: {text}\n\nRelevant?"
    reply = _chat_completion(_RELEVANCE_SYSTEM_PROMPT, user_content, temperature=0.0)
    if reply is None:
        return None
    normalized = reply.strip().upper()
    if normalized.startswith("YES"):
        return True
    if normalized.startswith("NO"):
        return False
    return None
