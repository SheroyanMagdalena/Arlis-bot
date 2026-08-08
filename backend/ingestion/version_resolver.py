"""Selection and deduplication rules for the baseline legal corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ACTIVE_ARMENIAN = "Գործում է"
LAW_TYPE = "Օրենք"
TEMPORAL_ACT_TYPES = {
    "Օրենք", "Օրենսգիրք", "Որոշում", "Հրաման", "Հրամանագիր",
    "Կարգադրություն", "Համատեղ հրաման",
}


def is_recommended_record(record: dict[str, Any]) -> bool:
    """Return whether metadata belongs in the active Armenian legal baseline."""
    if record.get("language") != "AM" or record.get("ActStatus") != ACTIVE_ARMENIAN:
        return False
    title = str(record.get("title") or "").casefold()
    return record.get("ActType") == LAW_TYPE or "օրենսգիրք" in title


def _identity(record: dict[str, Any]) -> tuple[str, ...]:
    """Group dump snapshots of the same legal act without merging reused numbers."""
    return tuple(
        str(record.get(field) or "").strip().casefold()
        for field in ("ActNumber", "title", "EnactmentDate", "EnactmentOrgan", "language")
    )


def _version_order(record: dict[str, Any]) -> tuple[int, str]:
    value = str(record.get("uniqid") or "")
    return (int(value) if value.isdigit() else -1, value)


def select_recommended_act_ids(metadata_path: str | Path) -> set[str]:
    """Select newest active Armenian law/code snapshot for each legal identity."""
    selected: dict[tuple[str, ...], dict[str, Any]] = {}
    with Path(metadata_path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid metadata JSON on line {line_number}: {error}") from error
            if not is_recommended_record(record):
                continue
            key = _identity(record)
            current = selected.get(key)
            if current is None or _version_order(record) > _version_order(current):
                selected[key] = record
    return {str(record["uniqid"]) for record in selected.values()}


def select_temporal_act_ids(metadata_path: str | Path) -> set[str]:
    """Select every dated Armenian legal version supported by temporal search."""
    selected: set[str] = set()
    with Path(metadata_path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid metadata JSON on line {line_number}: {error}") from error
            if (
                record.get("language") == "AM"
                and record.get("ActType") in TEMPORAL_ACT_TYPES
                and record.get("EffectiveDate")
                and record.get("uniqid") is not None
            ):
                selected.add(str(record["uniqid"]))
    return selected
