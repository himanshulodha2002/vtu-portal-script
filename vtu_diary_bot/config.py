from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_URL = "https://vtu.internyet.in"
LOGIN_URL = f"{BASE_URL}/sign-in"
STUDENT_DIARY_URL = f"{BASE_URL}/dashboard/student/student-diary"
CREATE_DIARY_ENTRY_URL = f"{BASE_URL}/dashboard/student/create-diary-entry"
DIARY_ENTRIES_URL = f"{BASE_URL}/dashboard/student/diary-entries"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_JSON = PROJECT_ROOT.parent / "internship_diary.json"
DEFAULT_TRANSFORMED_JSON = PROJECT_ROOT / "diary_entries.json"
DEFAULT_LOG_JSON = PROJECT_ROOT / "diary_log.json"
DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(slots=True)
class BotConfig:
    email: str
    password: str
    internship_name: str
    headless: bool = False
    slow_mo_ms: int = 100
    navigation_timeout_ms: int = 90_000
    action_timeout_ms: int = 45_000
    entry_retry_attempts: int = 5
    step_retry_attempts: int = 3
    retry_delay_seconds: float = 3.0
    min_entry_delay_seconds: float = 0.0
    max_entry_delay_seconds: float = 0.0
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR

    @classmethod
    def from_env(cls) -> "BotConfig":
        load_dotenv(PROJECT_ROOT / ".env")
        email = os.getenv("VTU_EMAIL", "").strip()
        password = os.getenv("VTU_PASSWORD", "")
        internship_name = os.getenv("VTU_INTERNSHIP_NAME", "Backend Intern — Happyfox").strip()
        if not email:
            raise ValueError("VTU_EMAIL is required in .env")
        if not password:
            raise ValueError("VTU_PASSWORD is required in .env")
        if not internship_name:
            raise ValueError("VTU_INTERNSHIP_NAME is required in .env")
        return cls(
            email=email,
            password=password,
            internship_name=internship_name,
            headless=_env_bool("HEADLESS", False),
            slow_mo_ms=int(os.getenv("SLOW_MO_MS", "100")),
            navigation_timeout_ms=int(os.getenv("NAVIGATION_TIMEOUT_MS", "90000")),
            action_timeout_ms=int(os.getenv("ACTION_TIMEOUT_MS", "45000")),
            entry_retry_attempts=int(os.getenv("ENTRY_RETRY_ATTEMPTS", "5")),
            step_retry_attempts=int(os.getenv("STEP_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=float(os.getenv("RETRY_DELAY_SECONDS", "3.0")),
            min_entry_delay_seconds=float(os.getenv("MIN_ENTRY_DELAY_SECONDS", "0")),
            max_entry_delay_seconds=float(os.getenv("MAX_ENTRY_DELAY_SECONDS", "0")),
            artifacts_dir=Path(os.getenv("ARTIFACTS_DIR", str(DEFAULT_ARTIFACTS_DIR))),
        )
