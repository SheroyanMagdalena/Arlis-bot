"""Runtime configuration for the rollback pipeline.

Values are read from environment variables (with a local .env file loaded via
python-dotenv for development) so the DeepSeek API key never has to be hardcoded.
"""

from __future__ import annotations

import os
from datetime import date

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# The organizers provision DeepSeek access via an OpenRouter-gated key (not a native
# DeepSeek API key) — see access-guide.md. Requests go to OpenRouter's chat-completions
# endpoint with the "deepseek/..." model slug; OpenRouter proxies to DeepSeek from there.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL", "https://openrouter.ai/api/v1/chat/completions"
)
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek/deepseek-v4-pro")

# A RetrievalResult at or above this similarity score is trusted as a confident match.
RAG_HIGH_CONFIDENCE_THRESHOLD = float(
    os.environ.get("RAG_HIGH_CONFIDENCE_THRESHOLD", "0.75")
)

# The ARLIS dump was last updated in April 2023 (see README). A reference date at or
# before this cutoff falls inside the corpus's known-valid window; a date after it
# means the local corpus cannot be trusted to reflect the current law.
CORPUS_CUTOFF_DATE = date(2023, 4, 30)
