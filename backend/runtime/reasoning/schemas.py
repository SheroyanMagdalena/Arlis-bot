"""Final tagged answer produced by the rollback pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from backend.runtime.retrieval.schemas import RetrievalResult
from backend.runtime.verification.confidence_checker import ConfidenceLevel


@dataclass(frozen=True)
class RollbackAnswer:
    answer: str
    confidence_level: ConfidenceLevel
    disclaimer: str
    source: Literal["rag", "deepseek", "none"]
    citations: list[RetrievalResult] = field(default_factory=list)
    reference_date: date | None = None
