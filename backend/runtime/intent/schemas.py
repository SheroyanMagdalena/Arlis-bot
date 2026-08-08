"""Temporal-intent detection result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemporalDetection:
    is_temporal: bool
    matched_terms: list[str] = field(default_factory=list)
    detected_dates: list[str] = field(default_factory=list)
