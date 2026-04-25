# VTU Internyet Diary Bot

Playwright-based automation for filling VTU Internyet internship diary entries from JSON.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Commands

Transform the source internship diary into VTU-ready JSON:

```bash
python -m vtu_diary_bot transform
```

Run the browser automation on `diary_entries.json`:

```bash
python -m vtu_diary_bot run
```

Add short randomized pauses between entries with environment variables:

```bash
MIN_ENTRY_DELAY_SECONDS=15 MAX_ENTRY_DELAY_SECONDS=30 python -m vtu_diary_bot run
```

Do both in one command:

```bash
python -m vtu_diary_bot all
```

Use `--limit 1` on `run` or `all` for a safe first pass.
