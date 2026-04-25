from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class DiaryEntry:
    date: str
    work_summary: str
    hours_worked: float
    reference_links: str
    learnings: str
    blockers: str
    skills: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiaryEntry":
        return cls(
            date=str(payload["date"]),
            work_summary=str(payload.get("work_summary", "")),
            hours_worked=float(payload.get("hours_worked", 0)),
            reference_links=str(payload.get("reference_links", "")),
            learnings=str(payload.get("learnings", "")),
            blockers=str(payload.get("blockers", "")),
            skills=[str(skill) for skill in payload.get("skills", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunEntryResult:
    date: str
    status: str
    attempts: int
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

