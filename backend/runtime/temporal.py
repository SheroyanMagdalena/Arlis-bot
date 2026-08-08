"""Resolve a legal question to an explicit target date before retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta


_MONTHS = {
    "հունվար": 1, "հունվարի": 1, "փետրվար": 2, "փետրվարի": 2,
    "մարտ": 3, "մարտի": 3, "ապրիլ": 4, "ապրիլի": 4,
    "մայիս": 5, "մայիսի": 5, "հունիս": 6, "հունիսի": 6,
    "հուլիս": 7, "հուլիսի": 7, "օգոստոս": 8, "օգոստոսի": 8,
    "սեպտեմբեր": 9, "սեպտեմբերի": 9, "հոկտեմբեր": 10, "հոկտեմբերի": 10,
    "նոյեմբեր": 11, "նոյեմբերի": 11, "դեկտեմբեր": 12, "դեկտեմբերի": 12,
}
_MONTH_PATTERN = "|".join(map(re.escape, _MONTHS))
_ISO_DATE = re.compile(r"(?<!\d)(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)")
_NUMERIC_DATE = re.compile(r"(?<!\d)(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})(?!\d)")
_ARMENIAN_DATE = re.compile(
    rf"(?<!\d)(?P<day>\d{{1,2}})(?:-ին)?\s+(?P<month>{_MONTH_PATTERN})\s+"
    r"(?P<year>\d{4})(?:\s*թ(?:վական(?:ի|ին)?)?\.?|-ին)?", re.IGNORECASE,
)
_ARMENIAN_YEAR_FIRST = re.compile(
    rf"(?<!\d)(?P<year>\d{{4}})\s*թ(?:վական(?:ի|ին)?)?\.?\s+"
    rf"(?P<month>{_MONTH_PATTERN})\s+(?P<day>\d{{1,2}})(?:-ին)?", re.IGNORECASE,
)


@dataclass(frozen=True)
class TemporalResolution:
    target_date: date | None
    reference_text: str | None
    resolution: str

    @property
    def requires_user_date(self) -> bool:
        return self.target_date is None


class TemporalResolutionError(ValueError):
    """Raised when a date-like expression is incomplete or invalid."""


def parse_target_date(value: str) -> date:
    """Parse a complete CLI/UI target date without guessing missing parts."""
    text = value.strip()
    for pattern in (_ISO_DATE, _NUMERIC_DATE, _ARMENIAN_DATE, _ARMENIAN_YEAR_FIRST):
        match = pattern.fullmatch(text)
        if match:
            return _date_from_match(match)
    raise TemporalResolutionError("Expected a complete date such as 2023-05-12 or 12.05.2023")


def detect_target_date(question: str, *, today: date | None = None) -> TemporalResolution:
    """Detect explicit Armenian/numeric dates and simple relative references."""
    text = question.strip()
    today = today or date.today()
    for pattern, resolved, reason in (
        (r"այսօր|հիմա|ներկայումս|ներկա պահին|այս պահին", today, "relative_today"),
        (r"երեկ", today - timedelta(days=1), "relative_yesterday"),
        (r"վաղը", today + timedelta(days=1), "relative_tomorrow"),
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return TemporalResolution(resolved, match.group(0), reason)
    for pattern in (_ISO_DATE, _NUMERIC_DATE, _ARMENIAN_DATE, _ARMENIAN_YEAR_FIRST):
        match = pattern.search(text)
        if match:
            return TemporalResolution(_date_from_match(match), match.group(0), "explicit")
    return TemporalResolution(None, None, "missing")


def _date_from_match(match: re.Match[str]) -> date:
    parts = match.groupdict()
    month_text = parts["month"].casefold()
    month = _MONTHS.get(month_text, int(month_text) if month_text.isdigit() else 0)
    try:
        return date(int(parts["year"]), month, int(parts["day"]))
    except ValueError as error:
        raise TemporalResolutionError(f"Invalid date reference: {match.group(0)!r}") from error
