"""Streaming parser for the ARLIS JSONL dumps."""

from __future__ import annotations

import json
import lzma
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator, Mapping, TextIO


STATUS_MAP = {
    "Գործում է": "active", "Действующий": "active", "Active": "active",
    "Գործում է մասնակի": "partially_active", "Действует частично": "partially_active",
    "Գործողությունը դադարեցված է": "suspended", "Действие приостановлено": "suspended",
    "Չի գործում": "inactive", "Не действующий": "inactive", "Passive": "inactive",
}

_BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "table", "td", "th", "tr"}


class ArlisParseError(ValueError):
    """Raised when a dump record cannot be converted to the target schema."""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str | None) -> str:
    """Convert an ARLIS HTML body into normalized readable text."""
    if not value:
        return ""
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_date(value: Any) -> str | None:
    """Normalize the dump's DD.MM.YYYY dates to ISO YYYY-MM-DD."""
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    for date_format in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            pass
    raise ArlisParseError(f"Unsupported ARLIS date: {text!r}")


def normalize_status(value: Any) -> str:
    """Map Armenian, Russian, and English source statuses to stable values."""
    if value is None or str(value).strip() == "":
        return "unknown"
    text = str(value).strip()
    return STATUS_MAP.get(text, text.casefold().replace(" ", "_"))


def normalize_act_number(value: Any) -> str:
    """Normalize spacing and case for act-number comparisons."""
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def parse_record(record: Mapping[str, Any]) -> dict[str, str | None]:
    """Convert one raw ARLIS object to the target document structure."""
    act_id = record.get("uniqid") or record.get("act_id")
    if act_id is None or str(act_id).strip() == "":
        raise ArlisParseError("Record is missing uniqid/act_id")
    body = record.get("body", record.get("text", ""))
    source_url = record.get("source_url") or record.get("pdf_link")
    return {
        "act_id": str(act_id).strip(),
        "title": str(record.get("title") or "").strip(),
        "status": normalize_status(record.get("ActStatus", record.get("status"))),
        "effective_date": normalize_date(record.get("EffectiveDate", record.get("effective_date"))),
        "source_url": str(source_url).strip() if source_url else None,
        "text": html_to_text(str(body)) if body else "",
    }


def _open_dump(path: Path) -> TextIO:
    if path.suffix.lower() == ".xz":
        return lzma.open(path, mode="rt", encoding="utf-8")
    return path.open(mode="rt", encoding="utf-8")


def iter_records(
    path: str | Path,
    limit: int | None = None,
    act_ids: set[str] | None = None,
) -> Iterator[dict[str, str | None]]:
    """Stream normalized records without loading the dump into memory."""
    dump_path = Path(path)
    with _open_dump(dump_path) as stream:
        emitted = 0
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                raw_record = json.loads(line)
                if not isinstance(raw_record, dict):
                    raise ArlisParseError("JSON value is not an object")
                if act_ids is not None and str(raw_record.get("uniqid")) not in act_ids:
                    continue
                yield parse_record(raw_record)
            except (json.JSONDecodeError, ArlisParseError) as error:
                raise ArlisParseError(f"Could not parse {dump_path} line {line_number}: {error}") from error
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def find_by_act_number(
    path: str | Path,
    act_number: str,
    *,
    first_only: bool = True,
) -> Iterator[dict[str, str | None]]:
    """Stream records whose ``ActNumber`` exactly matches the user's input."""
    wanted = normalize_act_number(act_number)
    if not wanted:
        raise ArlisParseError("Act number cannot be empty")

    dump_path = Path(path)
    with _open_dump(dump_path) as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                raw_record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ArlisParseError(
                    f"Could not parse {dump_path} line {line_number}: {error}"
                ) from error
            if not isinstance(raw_record, dict):
                raise ArlisParseError(
                    f"Could not parse {dump_path} line {line_number}: JSON value is not an object"
                )
            if normalize_act_number(raw_record.get("ActNumber")) != wanted:
                continue
            yield parse_record(raw_record)
            if first_only:
                return
