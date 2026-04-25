from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .models import DiaryEntry
from .skills import infer_skills
from .validators import raise_for_invalid_entries


def _trim_text(value: str, max_length: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def _round_hours(value: Any) -> float:
    decimal_value = Decimal(str(value))
    rounded = (decimal_value * 4).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 4
    return float(rounded)


def _join_reference_links(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def transform_source_entry(raw: dict[str, Any]) -> DiaryEntry:
    combined_text = " ".join(
        str(part or "")
        for part in (
            raw.get("workSummary", ""),
            raw.get("learnings", ""),
            raw.get("blockersRisks", ""),
            " ".join(raw.get("referenceLinks", []) if isinstance(raw.get("referenceLinks"), list) else []),
        )
    )
    skills = infer_skills(list(raw.get("skillsUsed", [])), combined_text)
    return DiaryEntry(
        date=str(raw["date"]),
        work_summary=_trim_text(str(raw.get("workSummary", "")), 2000),
        hours_worked=_round_hours(raw.get("hoursWorked", 0)),
        reference_links=_trim_text(_join_reference_links(raw.get("referenceLinks", "")), 5000),
        learnings=_trim_text(str(raw.get("learnings", "")), 2000),
        blockers=_trim_text(str(raw.get("blockersRisks", "")), 1000),
        skills=skills,
    )


def load_source_entries(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_diary_entries(path: Path) -> list[DiaryEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = [DiaryEntry.from_dict(item) for item in payload]
    raise_for_invalid_entries(entries)
    return entries


def write_diary_entries(path: Path, entries: list[DiaryEntry]) -> None:
    path.write_text(
        json.dumps([entry.to_dict() for entry in entries], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def transform_file(source_path: Path, output_path: Path) -> list[DiaryEntry]:
    entries = [transform_source_entry(item) for item in load_source_entries(source_path)]
    raise_for_invalid_entries(entries)
    write_diary_entries(output_path, entries)
    return entries
