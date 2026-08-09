"""Deterministic salary income-tax calculations for curated historical rates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class SalaryTaxCalculation:
    gross_salary: int
    rate_percent: int
    tax_due: int


_RATES = {2020: 23, 2021: 22, 2022: 21, 2023: 20}
_AMOUNT_PATTERN = re.compile(
    r"(?P<amount>\d{1,3}(?:[,.\s]\d{3})+|\d+)\s*(?P<scale>միլիոն|հազար)?\s*դրամ",
    re.IGNORECASE,
)


def calculate_salary_tax(
    question: str, reference_date: date | None
) -> SalaryTaxCalculation | None:
    if reference_date is None or reference_date.year not in _RATES:
        return None
    normalized = question.casefold()
    if "աշխատավարձ" not in normalized or "եկամտ" not in normalized:
        return None
    match = _AMOUNT_PATTERN.search(normalized)
    if not match:
        return None
    raw_amount = re.sub(r"[,.\s]", "", match.group("amount"))
    amount = Decimal(raw_amount)
    scale = match.group("scale")
    if scale == "միլիոն":
        amount *= Decimal(1_000_000)
    elif scale == "հազար":
        amount *= Decimal(1_000)
    gross = int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    rate = _RATES[reference_date.year]
    tax_due = int(
        (Decimal(gross) * Decimal(rate) / Decimal(100)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    return SalaryTaxCalculation(gross, rate, tax_due)
