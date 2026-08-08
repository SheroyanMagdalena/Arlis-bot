"""Builds the calendar-prompt clarification request."""

from __future__ import annotations

from backend.runtime.clarification.schemas import ClarificationRequest


def build_date_clarification() -> ClarificationRequest:
    return ClarificationRequest(
        field="reference_date",
        prompt=(
            "This depends on a date — please select the date this question applies to."
        ),
        input_type="date_picker",
    )
