"""Slot-filling clarification request types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ClarificationRequest:
    field: str
    prompt: str
    input_type: Literal["date_picker"]
