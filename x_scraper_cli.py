"""Browser-free command parsing and validation for the X scraper CLI."""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from chrome_auth import (
    default_browser_profile,
    is_prepared_profile,
    open_chrome_for_x_login,
)
from diagnostics import ScrapeRunLog, record_event, save_run_log
from document_generator import (
    create_csv_document,
    create_json_document,
    create_markdown_document,
    create_word_document,
    default_output_dir,
)
from run_models import ExitCode, RunStatus
from scraper import XScraper
from time_utils import (
    deduplicate_tweets,
    ensure_utc,
    filter_tweets_by_range,
    tweet_sort_key,
    utc_day_range,
    utc_now,
)
from version import __version__

ALLOWED_DIAGNOSTICS_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}
OUTPUT_FORMATS = ("json", "md", "docx", "csv")
VERSION = __version__
MAX_POST_COUNT = 10_000
MAX_DAY_RANGE = 3_650


class CliValidationError(ValueError):
    """Raised when a command cannot safely start a browser session."""


@dataclass(frozen=True)
class ScrapeRequest:
    target_username: str
    scrape_type: str
    mode_config: dict[str, Any]
    output_file: str
    output_format: str
    output_dir: str | None
    browser_profile: str | None
    headless: bool
    exclude_promotional_posts: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="x-scraper",
        description="Archive public X posts or your authorized bookmarks.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subcommands = parser.add_subparsers(dest="command")

    scrape = subcommands.add_parser("scrape", help="run one validated scrape")
    scrape.add_argument("--profile", help="public X handle to archive")
    scrape.add_argument("--bookmarks", action="store_true", help="archive your own bookmarks")
    scrape.add_argument("--count", type=int, help="number of posts to collect")
    scrape.add_argument("--days", type=int, help="collect posts from the last N days")
    scrape.add_argument("--from", dest="start_date", help="oldest ISO date (YYYY-MM-DD)")
    scrape.add_argument("--to", dest="end_date", help="newest ISO date (YYYY-MM-DD)")
    scrape.add_argument("--format", choices=OUTPUT_FORMATS, default="json")
    scrape.add_argument("--output", help="output filename, without a directory")
    scrape.add_argument("--output-dir", help="base directory for exports")
    scrape.add_argument("--browser-profile", help="local Chrome profile directory to reuse")
    scrape.add_argument("--headless", action="store_true", help="run Chrome without a window")
    scrape.add_argument(
        "--exclude-promotional-posts",
        action="store_true",
        help="exclude posts matching the documented promotional phrase list",
    )

    login = subcommands.add_parser("login", help="prepare an X session in normal Chrome")
    login.add_argument(
        "--browser-profile",
        default=default_browser_profile(),
        help="local Chrome profile directory to prepare",
    )

    diagnostics = subcommands.add_parser("diagnostics", help="check X selectors on a page")
    diagnostics.add_argument("--url", default="https://x.com/home", help="X page to inspect")
    subcommands.add_parser("paths", help="show browser-free default local paths")
    return parser


def _validated_handle(value: str) -> str:
    handle = (value or "").strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
        raise CliValidationError(
            "profile handle must contain 1-15 letters, numbers, or underscores"
        )
    return handle


def _parse_iso_date(value: str, label: str) -> datetime:
    try:
        start, _ = utc_day_range(value, value)
        return start
    except (TypeError, ValueError) as exc:
        raise CliValidationError(f"{label} must use YYYY-MM-DD") from exc


def _mode_config(namespace: argparse.Namespace) -> dict[str, Any]:
    has_count = namespace.count is not None
    has_days = namespace.days is not None
    has_date_range = bool(namespace.start_date or namespace.end_date)

    if has_date_range and not (namespace.start_date and namespace.end_date):
        raise CliValidationError("--from and --to must be supplied together")
    if sum((has_count, has_days, has_date_range)) != 1:
        raise CliValidationError("choose exactly one scrape mode")
    if has_count:
        if namespace.count <= 0:
            raise CliValidationError("--count must be greater than zero")
        if namespace.count > MAX_POST_COUNT:
            raise CliValidationError(f"--count maximum is {MAX_POST_COUNT}")
        return {"mode": "count", "count": namespace.count}
    if has_days:
        if namespace.days <= 0:
            raise CliValidationError("--days must be greater than zero")
        if namespace.days > MAX_DAY_RANGE:
            raise CliValidationError(f"--days maximum is {MAX_DAY_RANGE}")
        return {"mode": "days", "days": namespace.days}

    start = _parse_iso_date(namespace.start_date, "start date")
    _, end = utc_day_range(namespace.end_date, namespace.end_date)
    if start > end:
        raise CliValidationError("start date must not be after end date")
    return {"mode": "date_range", "start": start, "end": end}


def _browser_profile(value: str | None) -> str | None:
    if not value:
        return None
    profile = Path(value).expanduser().resolve()
    if profile.exists() and not profile.is_dir():
        raise CliValidationError("--browser-profile must identify a directory")
    return str(profile)


def request_from_namespace(namespace: argparse.Namespace) -> ScrapeRequest:
    has_profile = bool(namespace.profile)
    has_bookmarks = bool(namespace.bookmarks)
    if has_profile == has_bookmarks:
        raise CliValidationError("choose exactly one source: --profile or --bookmarks")

    scrape_type = "bookmarks" if has_bookmarks else "profile"
    target_username = "bookmarks" if has_bookmarks else _validated_handle(namespace.profile)
    browser_profile = _browser_profile(namespace.browser_profile or default_browser_profile())
    if namespace.headless and (
        browser_profile is None or not is_prepared_profile(Path(browser_profile))
    ):
        raise CliValidationError(
            "--headless requires --browser-profile pointing to an existing directory "
            "with an authorized session"
        )

    mode_config = _mode_config(namespace)
    extension = namespace.format
    if namespace.output and Path(namespace.output).name != namespace.output:
        raise CliValidationError("--output must be a filename without a directory")
    output_file = namespace.output or f"{target_username}_tweets.{extension}"
    return ScrapeRequest(
        target_username=target_username,
        scrape_type=scrape_type,
        mode_config=mode_config,
        output_file=output_file,
        output_format=namespace.format,
        output_dir=namespace.output_dir,
        browser_profile=browser_profile,
        headless=namespace.headless,
        exclude_promotional_posts=namespace.exclude_promotional_posts,
    )


def parse_scrape_request(argv: list[str]) -> ScrapeRequest:
    parser = build_parser()
    try:
        namespace = parser.parse_args(argv)
    except SystemExit as exc:
        raise CliValidationError("invalid command line arguments") from exc
    if namespace.command != "scrape":
        raise CliValidationError("expected the scrape command")
    return request_from_namespace(namespace)


def validate_diagnostics_url(value: str) -> str:
    parsed = urlparse((value or "").strip())
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DIAGNOSTICS_HOSTS:
        raise CliValidationError("diagnostics URL must be an https x.com or twitter.com URL")
    if parsed.username or parsed.password or parsed.port:
        raise CliValidationError("diagnostics URL must not include credentials or a port")
    return parsed.geturl()


def validate_output_directory(value: str | None) -> Path:
    """Create and probe the selected export root before Chrome starts."""
    path = Path(value).expanduser().resolve() if value else Path(default_output_dir())
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise OSError("selected output root is not a directory")
        descriptor, probe = tempfile.mkstemp(prefix=".x-scraper-probe-", dir=path)
        os.close(descriptor)
        os.unlink(probe)
    except OSError as exc:
        raise CliValidationError("output directory must be a writable directory") from exc
    return path


def _save_run_log(
    run_log: ScrapeRunLog,
    status: RunStatus,
    exit_code: ExitCode,
    output_dir: str | None,
) -> str:
    run_log.finalize(status, exit_code)
    return save_run_log(run_log, default_output_dir(), output_dir=output_dir)


def _collect_request_tweets(scraper: XScraper, request: ScrapeRequest, run_log: ScrapeRunLog):
    mode = request.mode_config
    if request.scrape_type == "bookmarks":
        if not scraper.navigate_to_bookmarks():
            record_event(
                run_log,
                "bookmarks_navigation",
                "error",
                "Bookmarks navigation failed",
                reason="bookmarks_navigation_failed",
            )
            return []
        if mode["mode"] == "count":
            return scraper.scrape_bookmarks(count=int(mode["count"]))
        tweets = scraper.scrape_bookmarks(get_all=True)
        if mode["mode"] == "days":
            cutoff = utc_now() - timedelta(days=int(mode["days"]))
            return [tweet for tweet in tweets if tweet.date and ensure_utc(tweet.date) >= cutoff]
        filtered, missing = filter_tweets_by_range(tweets, mode["start"], mode["end"])
        if missing:
            record_event(
                run_log,
                "date_filtering",
                "warning",
                "Bookmarks with unavailable timestamps were excluded from the date range",
                reason="tweet_date_unavailable",
                count=len(missing),
            )
        return filtered

    if not scraper.navigate_to_profile(request.target_username):
        record_event(
            run_log,
            "profile_navigation",
            "error",
            "Profile navigation failed",
            reason="profile_navigation_failed",
        )
        return []
    if mode["mode"] == "count":
        return scraper.scrape_by_count(int(mode["count"]))
    if mode["mode"] == "days":
        return scraper.scrape_last_n_days(int(mode["days"]))
    return scraper.scrape_by_date(mode["start"], mode["end"])


def _write_export(tweets, request: ScrapeRequest) -> str:
    if request.output_format == "json":
        return create_json_document(
            tweets,
            request.output_file,
            request.target_username,
            output_dir=request.output_dir,
            scrape_type=request.scrape_type,
        )
    if request.output_format == "md":
        return create_markdown_document(
            tweets,
            request.output_file,
            request.target_username,
            output_dir=request.output_dir,
        )
    if request.output_format == "csv":
        return create_csv_document(
            tweets,
            request.output_file,
            request.target_username,
            output_dir=request.output_dir,
        )
    return create_word_document(
        tweets,
        request.output_file,
        request.target_username,
        output_dir=request.output_dir,
    )


def run_cli_scrape(request: ScrapeRequest, scraper_factory=XScraper) -> int:
    """Run one validated scrape and keep export, log, and exit outcomes aligned."""
    run_log = ScrapeRunLog(
        target=request.target_username,
        scrape_type=request.scrape_type,
        mode=str(request.mode_config["mode"]),
        redactions=[request.browser_profile] if request.browser_profile else None,
    )
    scraper = scraper_factory(
        headless=request.headless,
        run_log=run_log,
        browser_profile=request.browser_profile,
        exclude_promotional_posts=request.exclude_promotional_posts,
    )
    try:
        scraper.start()
        if not scraper.manual_login():
            record_event(
                run_log,
                "manual_login",
                "error",
                "Manual login did not complete",
                reason="manual_login_timeout",
            )
            _save_run_log(run_log, RunStatus.FAILED, ExitCode.FAILED, request.output_dir)
            return int(ExitCode.FAILED)

        tweets = deduplicate_tweets(_collect_request_tweets(scraper, request, run_log))
        if not tweets:
            record_event(
                run_log,
                "timeline_loading",
                "error",
                "Scrape completed without collected tweets",
                reason="timeline_empty",
            )
            _save_run_log(run_log, RunStatus.FAILED, ExitCode.NO_RESULTS, request.output_dir)
            return int(ExitCode.NO_RESULTS)

        tweets.sort(key=tweet_sort_key, reverse=True)
        output_path = _write_export(tweets, request)
        record_event(
            run_log,
            "export_saving",
            "info",
            "Export saved",
            path=output_path,
            format=request.output_format,
            total_tweets=len(tweets),
        )
        requested_count = (
            int(request.mode_config["count"]) if request.mode_config["mode"] == "count" else None
        )
        collection_complete = bool(getattr(scraper, "last_collection_complete", True))
        partial = (requested_count is not None and len(tweets) < requested_count) or (
            requested_count is None and not collection_complete
        )
        if partial:
            record_event(
                run_log,
                "timeline_loading",
                "warning",
                "The requested collection boundary was not reached",
                reason=(
                    "partial_target_not_met" if requested_count is not None else "timeline_stalled"
                ),
                requested=requested_count,
                collected=len(tweets),
            )
            _save_run_log(run_log, RunStatus.PARTIAL, ExitCode.PARTIAL, request.output_dir)
            progress = (
                f"{len(tweets)}/{requested_count} posts"
                if requested_count is not None
                else f"{len(tweets)} posts; chronological boundary not confirmed"
            )
            print(f"Partial export saved ({progress}): {output_path}")
            return int(ExitCode.PARTIAL)

        _save_run_log(run_log, RunStatus.COMPLETED, ExitCode.COMPLETED, request.output_dir)
        print(f"Completed: saved {len(tweets)} posts to: {output_path}")
        return int(ExitCode.COMPLETED)
    except KeyboardInterrupt:
        tweets = list(getattr(scraper, "tweets_collected", []) or [])
        if tweets:
            tweets.sort(key=tweet_sort_key, reverse=True)
            try:
                output_path = _write_export(tweets, request)
            except OSError as exc:
                record_event(
                    run_log,
                    "export_saving",
                    "error",
                    f"Cancelled-run export failed: {exc}",
                    reason="export_failed",
                )
                _save_run_log(run_log, RunStatus.FAILED, ExitCode.FAILED, request.output_dir)
                return int(ExitCode.FAILED)
            record_event(
                run_log,
                "export_saving",
                "warning",
                "Collected posts were saved after user cancellation",
                path=output_path,
                total_tweets=len(tweets),
            )
        record_event(
            run_log,
            "cli_scrape",
            "warning",
            "Scrape cancelled by user",
            reason="user_cancelled",
            collected=len(tweets),
        )
        _save_run_log(run_log, RunStatus.CANCELLED, ExitCode.CANCELLED, request.output_dir)
        print("Cancelled by user.", file=sys.stderr)
        return int(ExitCode.CANCELLED)
    except Exception as exc:
        reason = "export_failed" if isinstance(exc, OSError) else "unknown_error"
        record_event(
            run_log,
            "cli_scrape",
            "error",
            f"Scrape failed: {exc}",
            reason=reason,
        )
        _save_run_log(run_log, RunStatus.FAILED, ExitCode.FAILED, request.output_dir)
        print(f"error: scrape failed: {exc}", file=sys.stderr)
        return int(ExitCode.FAILED)
    finally:
        scraper.stop()


def run_cli(
    argv: list[str] | None = None,
    *,
    scrape_runner=None,
    diagnostics_runner=None,
) -> int:
    """Run a command without starting Chrome until its inputs are validated."""
    args = list(argv or [])
    if args == ["--diagnostics"]:
        args = ["diagnostics"]
    parser = build_parser()
    try:
        namespace = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else int(ExitCode.FAILED)

    try:
        if namespace.command == "login":
            profile = _browser_profile(namespace.browser_profile)
            return open_chrome_for_x_login(profile or default_browser_profile())
        if namespace.command == "scrape":
            request = request_from_namespace(namespace)
            validate_output_directory(request.output_dir)
            if request.browser_profile is None or not is_prepared_profile(
                Path(request.browser_profile)
            ):
                raise CliValidationError(
                    "no prepared X session was found; run `x-scraper login` first "
                    "or provide a prepared --browser-profile"
                )
            return int((scrape_runner or run_cli_scrape)(request))
        if namespace.command == "diagnostics":
            url = validate_diagnostics_url(namespace.url)
            if diagnostics_runner is None:
                raise CliValidationError("diagnostics execution is not configured")
            return int(diagnostics_runner(url))
        if namespace.command == "paths":
            print(f"output_dir={default_output_dir()}")
            print(f"browser_profile={default_browser_profile()}")
            return int(ExitCode.COMPLETED)
        parser.print_help()
        return 2
    except CliValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
