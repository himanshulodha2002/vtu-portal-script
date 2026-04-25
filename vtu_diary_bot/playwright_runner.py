from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, TypeVar

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .config import CREATE_DIARY_ENTRY_URL, DIARY_ENTRIES_URL, LOGIN_URL, STUDENT_DIARY_URL, BotConfig
from .models import DiaryEntry, RunEntryResult

T = TypeVar("T")

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _ordinal_suffix(day: int) -> str:
    if 10 <= day % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


class EntrySkipped(Exception):
    pass


class StepFailed(Exception):
    pass


@dataclass(slots=True)
class RuntimeState:
    internship_name: str


class DiaryAutomationRunner:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run(self, entries: list[DiaryEntry]) -> list[RunEntryResult]:
        results: list[RunEntryResult] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self.config.headless,
                slow_mo=self.config.slow_mo_ms,
            )
            context = browser.new_context(viewport={"width": 1440, "height": 960})
            page = context.new_page()
            page.set_default_timeout(self.config.action_timeout_ms)
            page.set_default_navigation_timeout(self.config.navigation_timeout_ms)
            self._login(page)

            runtime = RuntimeState(internship_name=self.config.internship_name)
            for index, entry in enumerate(entries):
                results.append(self._process_entry(page, runtime, entry))
                if index < len(entries) - 1:
                    self._pause_between_entries()

            context.close()
            browser.close()
        return results

    def _pause_between_entries(self) -> None:
        minimum = self.config.min_entry_delay_seconds
        maximum = self.config.max_entry_delay_seconds
        if minimum <= 0 and maximum <= 0:
            return
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        delay = minimum if minimum == maximum else random.uniform(minimum, maximum)
        time.sleep(max(0.0, delay))

    def _process_entry(self, page: Page, runtime: RuntimeState, entry: DiaryEntry) -> RunEntryResult:
        last_reason: str | None = None
        for attempt in range(1, self.config.entry_retry_attempts + 1):
            try:
                self._navigate_to_checker(page)
                self._select_internship(page, runtime.internship_name)
                self._select_date(page, entry.date)
                self._continue_to_entry(page)
                if CREATE_DIARY_ENTRY_URL not in page.url:
                    if "/edit-diary-entry/" not in page.url:
                        raise StepFailed(f"unexpected page after Continue: {page.url}")
                self._fill_entry_form(page, entry)
                self._submit_entry(page)
                return RunEntryResult(date=entry.date, status="success", attempts=attempt)
            except EntrySkipped as exc:
                return RunEntryResult(date=entry.date, status="skipped", attempts=attempt, reason=str(exc))
            except Exception as exc:  # noqa: BLE001
                last_reason = f"{type(exc).__name__}: {exc}"
                self._capture_failure(page, entry.date, attempt)
                if attempt < self.config.entry_retry_attempts:
                    time.sleep(self.config.retry_delay_seconds * attempt)
                else:
                    return RunEntryResult(date=entry.date, status="failed", attempts=attempt, reason=last_reason)
        return RunEntryResult(date=entry.date, status="failed", attempts=self.config.entry_retry_attempts, reason=last_reason)

    def _login(self, page: Page) -> None:
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        self._wait_for_network_idle(page)
        email = self._first_visible(page, [
            "input[autocomplete='email']",
            "input[type='email']",
            "input[placeholder*='email' i]",
        ])
        password = self._first_visible(page, [
            "input[type='password']",
        ])
        email.fill(self.config.email)
        password.fill(self.config.password)
        page.locator("button[type='submit']").click()
        page.wait_for_url(re.compile(r".*/dashboard/.*"), timeout=self.config.navigation_timeout_ms)
        self._wait_for_network_idle(page)

    def _navigate_to_checker(self, page: Page) -> None:
        page.goto(STUDENT_DIARY_URL, wait_until="domcontentloaded")
        self._wait_for_network_idle(page)
        self._retry("checker ready", lambda: page.locator("#check-diary-form").wait_for(state="visible"))

    def _select_internship(self, page: Page, internship_name: str) -> None:
        dropdown = self._first_visible(page, [
            "button#internship_id",
            "[id='internship_id']",
            "button[aria-haspopup='listbox']",
        ])
        current_text = dropdown.inner_text().strip()
        if internship_name.lower() in current_text.lower():
            return
        dropdown.click()
        options = page.locator("[role='option']")
        options.first.wait_for(state="visible")

        target = options.filter(has_text=re.compile(re.escape(internship_name), re.IGNORECASE))
        if target.count():
            target.first.click()
            return
        if options.count() == 1:
            options.first.click()
            return
        visible_text = [options.nth(index).inner_text().strip() for index in range(min(options.count(), 10))]
        raise StepFailed(f"internship '{internship_name}' not found in options: {visible_text}")

    def _select_date(self, page: Page, iso_date: str) -> None:
        target = date.fromisoformat(iso_date)
        trigger = self._first_visible(page, [
            "button[aria-haspopup='dialog']",
            "button[data-slot='popover-trigger']",
        ])
        trigger.click()
        calendar = page.locator("[role='dialog']").last
        calendar.wait_for(state="visible")

        for _ in range(24):
            displayed = self._read_calendar_month(calendar)
            if displayed.year == target.year and displayed.month == target.month:
                break
            if (displayed.year, displayed.month) > (target.year, target.month):
                self._calendar_nav(calendar, direction="previous", current_month=displayed)
            else:
                self._calendar_nav(calendar, direction="next", current_month=displayed)
        else:
            raise StepFailed(f"could not reach calendar month for {iso_date}")

        month_name = target.strftime("%B")
        suffix = _ordinal_suffix(target.day)
        exact_date_pattern = re.compile(
            rf"\b{month_name} {target.day}{suffix}, {target.year}\b",
            flags=re.IGNORECASE,
        )
        day_button = calendar.get_by_role("button", name=exact_date_pattern).first
        if day_button.count() == 0:
            raise StepFailed(f"calendar day button not found for {iso_date}")
        day_button.click()
        page.wait_for_timeout(300)

    def _continue_to_entry(self, page: Page) -> None:
        page.get_by_role("button", name="Continue").click()
        page.wait_for_url(re.compile(r".*/dashboard/student/(create|edit)-diary-entry.*"), timeout=self.config.navigation_timeout_ms)
        self._wait_for_network_idle(page)

    def _fill_entry_form(self, page: Page, entry: DiaryEntry) -> None:
        form = page.locator("#student-diary-form")
        form.wait_for(state="visible")
        form.locator("textarea[name='description']").fill(entry.work_summary)
        self._first_visible(form, [
            "input[type='number']",
            "input[placeholder='e.g. 6.5']",
        ]).fill(str(entry.hours_worked))
        form.locator("textarea[name='links']").fill(entry.reference_links)
        form.locator("textarea[name='learnings']").fill(entry.learnings)
        form.locator("textarea[name='blockers']").fill(entry.blockers)
        self._select_skills(page, form, entry.skills)

    def _select_skills(self, page: Page, form: Locator, skills: list[str]) -> None:
        self._clear_selected_skills(form)
        for skill in skills:
            combo = self._first_visible(form, [
                "input[placeholder='Add skills']",
                "input[placeholder='Loading...']",
                "[role='combobox'] input",
                "input[aria-autocomplete='list']",
            ])
            combo.click()
            combo.fill("")
            combo.type(skill, delay=35)
            option = page.locator("[role='option']").filter(has_text=re.compile(fr"^{re.escape(skill)}$", re.IGNORECASE)).first
            option.wait_for(state="visible", timeout=self.config.action_timeout_ms)
            option.click()
            page.wait_for_timeout(250)

    def _clear_selected_skills(self, form: Locator) -> None:
        remove_buttons = form.locator("[aria-label^='Remove ']")
        count = remove_buttons.count()
        for _ in range(count):
            remove_buttons.first.click()
            time.sleep(0.15)

    def _submit_entry(self, page: Page) -> None:
        button = page.locator("button:has-text('Save'):not([disabled])")
        button.wait_for(state="visible")
        button.click()
        try:
            page.wait_for_url(f"{DIARY_ENTRIES_URL}", timeout=self.config.navigation_timeout_ms)
        except PlaywrightTimeoutError as exc:
            if "saved successfully" not in page.locator("body").inner_text().lower():
                raise StepFailed("save did not redirect to diary entries") from exc
        self._wait_for_network_idle(page)

    def _read_calendar_month(self, calendar: Locator) -> date:
        caption = ""
        status = calendar.locator("[role='status']").first
        if status.count():
            caption = status.inner_text().strip()
        if not caption:
            grid = calendar.locator("[role='grid']").first
            caption = (grid.get_attribute("aria-label") or "").strip()
        text = caption or calendar.inner_text()
        match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            raise StepFailed("calendar month label not found")
        month = MONTHS[match.group(1).lower()]
        year = int(match.group(2))
        return date(year, month, 1)

    def _calendar_nav(self, calendar: Locator, direction: str, current_month: date) -> None:
        if direction == "previous":
            button = self._first_visible(calendar, [
                "button[aria-label='Go to the Previous Month']",
                "button[aria-label*='Previous Month' i]",
                "button[aria-label*='Previous' i]",
                "button[name='previous-month']",
            ])
        else:
            button = self._first_visible(calendar, [
                "button[aria-label='Go to the Next Month']",
                "button[aria-label*='Next Month' i]",
                "button[aria-label*='Next' i]",
                "button[name='next-month']",
            ])

        button.click()
        for _ in range(8):
            time.sleep(0.2)
            updated_month = self._read_calendar_month(calendar)
            if updated_month == current_month:
                continue
            if direction == "previous" and updated_month < current_month:
                return
            if direction == "next" and updated_month > current_month:
                return
            raise StepFailed(
                f"calendar moved in wrong direction: {current_month.isoformat()} -> {updated_month.isoformat()}"
            )
        raise StepFailed(f"calendar did not change month after clicking {direction}")

    def _capture_failure(self, page: Page, iso_date: str, attempt: int) -> None:
        safe_date = iso_date.replace("-", "")
        screenshot_path = self.config.artifacts_dir / f"{safe_date}_attempt{attempt}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:  # noqa: BLE001
            return

    def _wait_for_network_idle(self, page: Page) -> None:
        page.wait_for_load_state("networkidle", timeout=self.config.navigation_timeout_ms)
        page.wait_for_timeout(500)

    def _retry(self, label: str, operation: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.config.step_retry_attempts + 1):
            try:
                return operation()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.config.step_retry_attempts:
                    break
                time.sleep(self.config.retry_delay_seconds)
        raise StepFailed(f"{label} failed after {self.config.step_retry_attempts} retries: {last_error}") from last_error

    @staticmethod
    def _first_visible(root: Page | Locator, selectors: list[str]) -> Locator:
        for selector in selectors:
            locator = root.locator(selector).first
            try:
                locator.wait_for(state="visible", timeout=5_000)
                return locator
            except PlaywrightTimeoutError:
                continue
        raise StepFailed(f"no visible locator found for selectors: {selectors}")
