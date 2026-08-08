"""External fallback search via the DeepSeek chat-completion API.

Used only when the local ARLIS corpus cannot confidently answer a time-sensitive
question. Any failure (missing key, network error, bad response) degrades to
`None` so the pipeline can fall back to a LEVEL 4 "no answer" instead of crashing.
"""

from __future__ import annotations

from datetime import date

import requests

from backend.shared.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL

_SYSTEM_PROMPT = (
    "You are a legal-research assistant for Armenian law. Answer briefly and "
    "factually. If you are not confident of the current, up-to-date answer, say so "
    "explicitly instead of guessing."
)

_TIMEOUT_SECONDS = 15


def ask_deepseek(question: str, *, reference_date: date | None = None) -> str | None:
    if not DEEPSEEK_API_KEY:
        return None

    user_content = question
    if reference_date is not None:
        user_content = f"As of {reference_date.isoformat()}: {question}"

    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
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
