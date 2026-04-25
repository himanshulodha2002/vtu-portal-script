from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .models import DiaryEntry
from .skills import ALLOWED_SKILL_SET


def _is_quarter_hour(value: float) -> bool:
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation:
        return False
    return (decimal_value * 4) % 1 == 0


def validate_entries(entries: Iterable[DiaryEntry]) -> list[str]:
    errors: list[str] = []
    seen_dates: set[str] = set()
    for entry in entries:
        prefix = f"{entry.date}:"
        try:
            parsed_date = date.fromisoformat(entry.date)
        except ValueError:
            errors.append(f"{prefix} invalid ISO date")
            continue

        if parsed_date.weekday() >= 5:
            errors.append(f"{prefix} not a weekday")
        if entry.date in seen_dates:
            errors.append(f"{prefix} duplicate date")
        seen_dates.add(entry.date)

        if len(entry.work_summary) > 2000:
            errors.append(f"{prefix} work_summary exceeds 2000 characters")
        if len(entry.learnings) > 2000:
            errors.append(f"{prefix} learnings exceeds 2000 characters")
        if len(entry.blockers) > 1000:
            errors.append(f"{prefix} blockers exceeds 1000 characters")
        if not (0 <= entry.hours_worked <= 24):
            errors.append(f"{prefix} hours_worked must be between 0 and 24")
        if not _is_quarter_hour(entry.hours_worked):
            errors.append(f"{prefix} hours_worked must be divisible by 0.25")
        if not entry.skills:
            errors.append(f"{prefix} at least one skill is required")
        invalid_skills = [skill for skill in entry.skills if skill not in ALLOWED_SKILL_SET]
        if invalid_skills:
            errors.append(f"{prefix} invalid skills: {', '.join(invalid_skills)}")
    return errors


def raise_for_invalid_entries(entries: Iterable[DiaryEntry]) -> None:
    errors = validate_entries(entries)
    if errors:
        raise ValueError("\n".join(errors))

