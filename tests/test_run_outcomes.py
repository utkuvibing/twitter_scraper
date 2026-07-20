from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from main import run_interactive
from run_models import ExitCode, RunStatus
from scraper import Tweet
from x_scraper_cli import ScrapeRequest, run_cli_scrape


def tweet(item_id: str = "1") -> Tweet:
    return Tweet(
        id=item_id,
        text="archived post",
        date=datetime(2026, 7, 20, tzinfo=timezone.utc),
        date_str="Jul 20",
        media_urls=[],
        tweet_url=f"https://x.com/example/status/{item_id}",
    )


def request(count: int = 1) -> ScrapeRequest:
    return ScrapeRequest(
        target_username="example",
        scrape_type="profile",
        mode_config={"mode": "count", "count": count},
        output_file="archive.json",
        output_format="json",
        output_dir=None,
        browser_profile=str(Path("prepared-profile").resolve()),
        headless=True,
    )


class OutcomeScraper:
    def __init__(self, tweets=None, interrupt=False):
        self.result = list(tweets or [])
        self.tweets_collected = list(tweets or [])
        self.interrupt = interrupt
        self.stopped = False

    def start(self):
        return None

    def stop(self):
        self.stopped = True

    def manual_login(self):
        return True

    def navigate_to_profile(self, _target):
        return True

    def scrape_by_count(self, _count):
        if self.interrupt:
            raise KeyboardInterrupt
        return self.result


class Factory:
    def __init__(self, scraper):
        self.scraper = scraper

    def __call__(self, **_kwargs):
        return self.scraper


def run_and_capture(scraper: OutcomeScraper, count: int = 1):
    finalized = []

    def save(run_log, status, exit_code, _output_dir):
        finalized.append((status, exit_code, run_log))
        return "run.json"

    with (
        patch("x_scraper_cli._write_export", return_value="archive.json"),
        patch("x_scraper_cli._save_run_log", side_effect=save),
    ):
        code = run_cli_scrape(request(count), scraper_factory=Factory(scraper))
    return code, finalized


def test_full_count_is_completed_with_exit_zero():
    code, finalized = run_and_capture(OutcomeScraper([tweet()]), count=1)

    assert code == ExitCode.COMPLETED
    assert finalized[0][:2] == (RunStatus.COMPLETED, ExitCode.COMPLETED)


def test_short_count_is_partial_with_exit_three_and_is_exported():
    code, finalized = run_and_capture(OutcomeScraper([tweet()]), count=3)

    assert code == ExitCode.PARTIAL
    assert finalized[0][:2] == (RunStatus.PARTIAL, ExitCode.PARTIAL)


def test_duplicate_post_ids_are_exported_once_and_do_not_fake_target_completion():
    finalized = []
    exported = []

    def save(run_log, status, exit_code, _output_dir):
        finalized.append((status, exit_code, run_log))
        return "run.json"

    def write(items, _request):
        exported.extend(items)
        return "archive.json"

    with (
        patch("x_scraper_cli._write_export", side_effect=write),
        patch("x_scraper_cli._save_run_log", side_effect=save),
    ):
        code = run_cli_scrape(
            request(2),
            scraper_factory=Factory(OutcomeScraper([tweet("1"), tweet("1")])),
        )

    assert code == ExitCode.PARTIAL
    assert [item.id for item in exported] == ["1"]


def test_zero_usable_results_exit_two_without_claiming_completion():
    code, finalized = run_and_capture(OutcomeScraper([]), count=3)

    assert code == ExitCode.NO_RESULTS
    assert finalized[0][:2] == (RunStatus.FAILED, ExitCode.NO_RESULTS)


def test_export_failure_is_failed_with_exit_one():
    finalized = []

    def save(run_log, status, exit_code, _output_dir):
        finalized.append((status, exit_code, run_log))
        return "run.json"

    with (
        patch("x_scraper_cli._write_export", side_effect=OSError("disk full")),
        patch("x_scraper_cli._save_run_log", side_effect=save),
    ):
        code = run_cli_scrape(request(), scraper_factory=Factory(OutcomeScraper([tweet()])))

    assert code == ExitCode.FAILED
    assert finalized[0][:2] == (RunStatus.FAILED, ExitCode.FAILED)
    assert finalized[0][2].failure_reason == "export_failed"


def test_keyboard_interrupt_saves_collected_data_and_exits_130():
    scraper = OutcomeScraper([tweet()], interrupt=True)
    code, finalized = run_and_capture(scraper, count=3)

    assert code == ExitCode.CANCELLED
    assert finalized[0][:2] == (RunStatus.CANCELLED, ExitCode.CANCELLED)
    assert scraper.stopped


def test_interactive_wizard_uses_the_same_orchestration_and_exit_status():
    answers = ["1", "example", "1", "3", "1", "", "n"]
    with (
        patch("builtins.input", side_effect=answers),
        patch("getpass.getpass", side_effect=AssertionError("password prompt used")),
        patch("main.is_prepared_profile", return_value=True, create=True),
        patch("main.run_cli_scrape", return_value=ExitCode.PARTIAL, create=True) as run,
    ):
        code = run_interactive()

    assert code == ExitCode.PARTIAL
    request_arg = run.call_args.args[0]
    assert request_arg.target_username == "example"
    assert request_arg.mode_config == {"mode": "count", "count": 3}
