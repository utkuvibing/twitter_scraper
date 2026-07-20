"""Console entry point and English interactive wizard for x-scraper."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from chrome_auth import (
    default_browser_profile,
    is_prepared_profile,
    open_chrome_for_x_login,
)
from diagnostics import ScrapeRunLog, record_event, save_run_log
from document_generator import default_output_dir
from run_models import ExitCode, RunStatus
from scraper import XScraper
from terminal_ui import TerminalUI
from time_utils import ensure_utc
from x_scraper_cli import (
    CliValidationError,
    ScrapeRequest,
    parse_scrape_request,
    run_cli_scrape,
    validate_diagnostics_url,
)


def save_cli_run_log(run_log: ScrapeRunLog, status: str = "completed") -> str:
    """Persist a diagnostics run log and print its location."""
    run_log.mark_completed(status)
    path = save_run_log(run_log, default_output_dir())
    print(f"Run log saved: {path}")
    if run_log.failure_reason:
        print(f"Failure reason: {run_log.failure_reason}")
    return path


def run_diagnostics_cli(url: str | None = None) -> int:
    """Open an approved X URL and report selector health."""
    run_log = ScrapeRunLog(
        target="diagnostics", scrape_type="diagnostics", mode="selector_check"
    )
    scraper: XScraper | None = None
    try:
        if url is None:
            url = (
                input("URL to inspect (blank for https://x.com/home): ").strip()
                or "https://x.com/home"
            )
        try:
            url = validate_diagnostics_url(url)
        except CliValidationError as exc:
            record_event(
                run_log,
                "selector_diagnostics",
                "error",
                f"Invalid diagnostics URL: {exc}",
                reason="invalid_input",
            )
            save_cli_run_log(run_log, RunStatus.INVALID_INPUT)
            print(f"Diagnostics input error: {exc}", file=sys.stderr)
            return int(ExitCode.INVALID_INPUT)

        scraper = XScraper(
            headless=False,
            run_log=run_log,
            browser_profile=default_browser_profile(),
        )
        scraper.start()
        scraper.driver.get(url)
        input("Press ENTER after the page has loaded...")
        diagnostics = scraper.run_selector_diagnostics()
        for check in diagnostics["checks"]:
            marker = "OK" if check["ok"] else "MISS"
            print(f"[{marker}] {check['name']}: {check['count']}")

        if diagnostics["ok"]:
            save_cli_run_log(run_log, RunStatus.COMPLETED)
            return int(ExitCode.COMPLETED)
        record_event(
            run_log,
            "selector_diagnostics",
            "error",
            "Required selector checks failed",
            reason="timeline_empty",
            missing_required=diagnostics["missing_required"],
        )
        save_cli_run_log(run_log, RunStatus.FAILED)
        return int(ExitCode.NO_RESULTS)
    except KeyboardInterrupt:
        save_cli_run_log(run_log, RunStatus.CANCELLED)
        return int(ExitCode.CANCELLED)
    except Exception as exc:
        record_event(
            run_log,
            "selector_diagnostics",
            "error",
            f"Diagnostics failed: {exc}",
            reason="unknown_error",
        )
        save_cli_run_log(run_log, RunStatus.FAILED)
        print(f"Diagnostics error: {exc}", file=sys.stderr)
        return int(ExitCode.FAILED)
    finally:
        if scraper:
            scraper.stop()


def _positive_integer(prompt: str) -> int:
    value = input(prompt).strip()
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CliValidationError("value must be a whole number") from exc
    if parsed <= 0:
        raise CliValidationError("value must be greater than zero")
    return parsed


def _interactive_config(*, include_banner: bool, include_session: bool) -> dict[str, Any]:
    ui = TerminalUI()
    if include_banner:
        ui.banner()
    if include_session:
        ui.section("Account session", 1)
        ui.status(
            "info",
            "x-scraper reuses its isolated local Chrome profile. Run `x-scraper login` to replace it.",
        )

    ui.section("Source", 2 if include_session else 1)
    ui.choice(1, "Profile posts", "archive posts from a public account")
    ui.choice(2, "Bookmarks", "archive bookmarks from your own account")
    source = input("Select (1/2): ").strip()
    if source == "2":
        scrape_type = "bookmarks"
        target = "bookmarks"
    elif source == "1":
        scrape_type = "profile"
        ui.section("Target profile")
        target = input("Handle (without @): ").strip().lstrip("@")
    else:
        raise CliValidationError("source must be 1 or 2")

    ui.section("Collection range")
    ui.choice(1, "Post count")
    ui.choice(2, "Last N days")
    ui.choice(3, "Date range")
    mode_choice = input("Select (1/2/3): ").strip()
    if mode_choice == "1":
        mode = {"mode": "count", "count": _positive_integer("Posts to collect: ")}
    elif mode_choice == "2":
        mode = {"mode": "days", "days": _positive_integer("Days to collect: ")}
    elif mode_choice == "3":
        print("Date format: DD.MM.YYYY (for example 01.01.2026)")
        try:
            start = ensure_utc(
                datetime.strptime(input("Start date: ").strip(), "%d.%m.%Y")
            )
            end = ensure_utc(
                datetime.strptime(input("End date: ").strip(), "%d.%m.%Y")
            ).replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError as exc:
            raise CliValidationError("dates must use DD.MM.YYYY") from exc
        if start > end:
            raise CliValidationError("start date must not be after end date")
        mode = {"mode": "date_range", "start": start, "end": end}
    else:
        raise CliValidationError("collection range must be 1, 2, or 3")

    ui.section("Export")
    ui.choice(1, "JSON", "recommended for data workflows")
    ui.choice(2, "Markdown (.md)")
    ui.choice(3, "Word (.docx)")
    ui.choice(4, "CSV (.csv)")
    format_choice = input("Select (1/2/3/4): ").strip()
    output_format, extension = {
        "1": ("json", ".json"),
        "2": ("md", ".md"),
        "3": ("docx", ".docx"),
        "4": ("csv", ".csv"),
    }.get(format_choice, (None, None))
    if output_format is None or extension is None:
        raise CliValidationError("export format must be 1, 2, 3, or 4")
    default_name = f"{target}_tweets{extension}"
    output_file = input(f"Filename (blank for {default_name}): ").strip() or default_name
    return {
        "target_username": target,
        "scrape_type": scrape_type,
        "mode_config": mode,
        "output_format": output_format,
        "output_file": output_file,
        "browser_profile": default_browser_profile(),
    }


def get_user_input() -> dict[str, Any]:
    """Collect one complete interactive request in English."""
    return _interactive_config(include_banner=True, include_session=True)


def get_scrape_config() -> dict[str, Any]:
    """Collect another request while reusing the current session."""
    return _interactive_config(include_banner=False, include_session=False)


def _request_from_interactive_config(config: dict[str, Any]) -> ScrapeRequest:
    args = ["scrape"]
    if config["scrape_type"] == "bookmarks":
        args.append("--bookmarks")
    else:
        args.extend(("--profile", config["target_username"]))

    mode = config["mode_config"]
    if mode["mode"] == "count":
        args.extend(("--count", str(mode["count"])))
    elif mode["mode"] == "days":
        args.extend(("--days", str(mode["days"])))
    else:
        args.extend(
            (
                "--from",
                mode["start"].strftime("%Y-%m-%d"),
                "--to",
                mode["end"].strftime("%Y-%m-%d"),
            )
        )
    args.extend(("--format", config["output_format"]))
    args.extend(("--output", config["output_file"]))
    args.extend(("--browser-profile", config["browser_profile"]))
    return parse_scrape_request(args)


def ask_continue() -> bool:
    """Ask whether to archive another source with the same session."""
    while True:
        answer = input("Archive another account? (Y/N): ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter Y for yes or N for no.")


def run_interactive() -> int:
    """Run the wizard through the same lifecycle as scripted commands."""
    profile = default_browser_profile()
    if not is_prepared_profile(Path(profile)):
        print("No prepared X session was found; opening normal Chrome for sign-in.")
        login_code = open_chrome_for_x_login(profile)
        if login_code != 0:
            return int(ExitCode.FAILED)

    last_code = int(ExitCode.COMPLETED)
    while True:
        try:
            config = get_user_input()
            request = _request_from_interactive_config(config)
        except (CliValidationError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return int(ExitCode.INVALID_INPUT)

        last_code = int(run_cli_scrape(request))
        if not ask_continue():
            return last_code


def main(argv: list[str] | None = None) -> int:
    """Dispatch arguments to the scripted CLI or start the wizard."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        from x_scraper_cli import run_cli as dispatch_cli

        return dispatch_cli(args, diagnostics_runner=run_diagnostics_cli)
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
