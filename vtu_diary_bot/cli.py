from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_LOG_JSON, DEFAULT_SOURCE_JSON, DEFAULT_TRANSFORMED_JSON, BotConfig
from .logging_utils import print_summary, save_run_log
from .playwright_runner import DiaryAutomationRunner
from .transformer import load_diary_entries, transform_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VTU Internyet diary automation bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    transform = subparsers.add_parser("transform", help="Transform internship_diary.json into diary_entries.json")
    transform.add_argument("--source", type=Path, default=DEFAULT_SOURCE_JSON)
    transform.add_argument("--output", type=Path, default=DEFAULT_TRANSFORMED_JSON)

    run = subparsers.add_parser("run", help="Run Playwright diary automation")
    run.add_argument("--input", type=Path, default=DEFAULT_TRANSFORMED_JSON)
    run.add_argument("--log", type=Path, default=DEFAULT_LOG_JSON)
    run.add_argument("--limit", type=int, default=0)

    all_cmd = subparsers.add_parser("all", help="Transform source JSON, then run automation")
    all_cmd.add_argument("--source", type=Path, default=DEFAULT_SOURCE_JSON)
    all_cmd.add_argument("--output", type=Path, default=DEFAULT_TRANSFORMED_JSON)
    all_cmd.add_argument("--log", type=Path, default=DEFAULT_LOG_JSON)
    all_cmd.add_argument("--limit", type=int, default=0)

    return parser


def _run_automation(input_path: Path, log_path: Path, limit: int) -> None:
    entries = load_diary_entries(input_path)
    if limit > 0:
        entries = entries[:limit]
    config = BotConfig.from_env()
    results = DiaryAutomationRunner(config).run(entries)
    save_run_log(log_path, results)
    print_summary(results, log_path)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "transform":
        entries = transform_file(args.source, args.output)
        print(f"Transformed {len(entries)} entries into {args.output}")
        return

    if args.command == "run":
        _run_automation(args.input, args.log, args.limit)
        return

    entries = transform_file(args.source, args.output)
    print(f"Transformed {len(entries)} entries into {args.output}")
    _run_automation(args.output, args.log, args.limit)

