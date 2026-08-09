"""Deterministic historical rental-income tax calculations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class RentalTaxCalculation:
    gross_income: int
    threshold: int
    tax_due: int


_AMOUNT_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<scale>միլիոն|հազար)?\s*դրամ",
    re.IGNORECASE,
)


def calculate_2019_rental_tax(
    question: str, reference_date: date | None
) -> RentalTaxCalculation | None:
    """Return the Article 150(7) calculation for a 2019 rental-payment question."""
    if reference_date is None or reference_date.year != 2019:
        return None
    normalized = question.casefold()
    if "վարձակալ" not in normalized or "եկամտ" not in normalized:
        return None
    match = _AMOUNT_PATTERN.search(normalized)
    if not match:
        return None
    amount = Decimal(match.group("amount").replace(",", "."))
    scale = match.group("scale")
    if scale == "միլիոն":
        amount *= Decimal(1_000_000)
    elif scale == "հազար":
        amount *= Decimal(1_000)
    gross = int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    threshold = 58_350_000
    base_tax = Decimal(gross) * Decimal("0.10")
    excess_tax = Decimal(max(gross - threshold, 0)) * Decimal("0.10")
    tax_due = int((base_tax + excess_tax).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return RentalTaxCalculation(gross, threshold, tax_due)
