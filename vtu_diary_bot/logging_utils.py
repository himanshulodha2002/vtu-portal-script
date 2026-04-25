from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import RunEntryResult


def build_summary(results: list[RunEntryResult]) -> dict[str, int]:
    summary = {"total": len(results), "successful": 0, "failed": 0, "skipped": 0}
    for result in results:
        if result.status == "success":
            summary["successful"] += 1
        elif result.status == "skipped":
            summary["skipped"] += 1
        else:
            summary["failed"] += 1
    return summary


def save_run_log(path: Path, results: list[RunEntryResult]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": build_summary(results),
        "results": [result.to_dict() for result in results],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def print_summary(results: list[RunEntryResult], log_path: Path) -> None:
    summary = build_summary(results)
    print("===== DIARY BOT SUMMARY =====")
    print(f"Total entries:   {summary['total']}")
    print(f"Successful:      {summary['successful']}")
    print(f"Failed:          {summary['failed']}")
    print(f"Skipped:         {summary['skipped']}")
    print()
    print("Failed entries:")
    failures = [result for result in results if result.status == "failed"]
    if failures:
        for failure in failures:
            print(f"  - {failure.date}  (reason: {failure.reason})")
    else:
        print("  - None")
    print()
    print(f"Log saved to: {log_path.name}")
    print("==============================")

