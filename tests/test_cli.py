import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from main import get_user_input, main
from scraper import Tweet, XScraper
from x_scraper_cli import (
    CliValidationError,
    parse_scrape_request,
    run_cli_scrape,
    validate_diagnostics_url,
)


class FakeScraper:
    def __init__(self, tweets):
        self.tweets = tweets
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def manual_login(self):
        return True

    def navigate_to_profile(self, _target):
        return True

    def navigate_to_bookmarks(self):
        return True

    def scrape_by_count(self, _count):
        return self.tweets

    def scrape_last_n_days(self, _days):
        return self.tweets

    def scrape_by_date(self, _start, _end):
        return self.tweets

    def scrape_bookmarks(self, **_kwargs):
        return self.tweets


class RecordingScraperFactory:
    def __init__(self, tweets):
        self.tweets = tweets
        self.kwargs = None
        self.instance = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        self.instance = FakeScraper(self.tweets)
        return self.instance


class CliRequestTests(unittest.TestCase):
    def test_profile_count_request_supports_csv_and_output_directory(self):
        request = parse_scrape_request(
            [
                "scrape",
                "--profile",
                "example",
                "--count",
                "25",
                "--format",
                "csv",
                "--output-dir",
                "exports",
            ]
        )

        self.assertEqual(request.target_username, "example")
        self.assertEqual(request.scrape_type, "profile")
        self.assertEqual(request.mode_config, {"mode": "count", "count": 25})
        self.assertEqual(request.output_format, "csv")
        self.assertEqual(request.output_dir, "exports")

    def test_rejects_conflicting_sources(self):
        with self.assertRaisesRegex(CliValidationError, "exactly one source"):
            parse_scrape_request(
                ["scrape", "--profile", "example", "--bookmarks", "--count", "1"]
            )

    def test_rejects_headless_without_an_authorized_browser_profile(self):
        with self.assertRaisesRegex(CliValidationError, "--browser-profile"):
            parse_scrape_request(["scrape", "--profile", "example", "--count", "1", "--headless"])

    def test_rejects_headless_with_a_profile_directory_that_does_not_exist(self):
        missing_profile = Path("missing-authorized-profile").resolve()
        with self.assertRaisesRegex(CliValidationError, "existing directory"):
            parse_scrape_request(
                [
                    "scrape",
                    "--profile",
                    "example",
                    "--count",
                    "1",
                    "--format",
                    "csv",
                    "--headless",
                    "--browser-profile",
                    str(missing_profile),
                ]
            )

    def test_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(CliValidationError, "start date"):
            parse_scrape_request(
                [
                    "scrape",
                    "--profile",
                    "example",
                    "--from",
                    "2026-07-20",
                    "--to",
                    "2026-07-19",
                ]
            )

    def test_diagnostics_accepts_x_urls_and_rejects_other_hosts(self):
        self.assertEqual(
            validate_diagnostics_url("https://x.com/home"), "https://x.com/home"
        )
        with self.assertRaisesRegex(CliValidationError, "x.com"):
            validate_diagnostics_url("https://example.com")

    def test_main_dispatches_arguments_to_the_non_interactive_cli(self):
        with patch("x_scraper_cli.run_cli", return_value=7) as run_cli:
            self.assertEqual(main(["--help"]), 7)

        self.assertEqual(run_cli.call_args.args[0], ["--help"])
        self.assertIn("diagnostics_runner", run_cli.call_args.kwargs)

    @patch(
        "builtins.input",
        side_effect=["1", "1", "example", "1", "1", "4", ""],
    )
    def test_interactive_wizard_supports_csv_exports(self, _input):
        config = get_user_input()

        self.assertEqual(config["output_format"], "csv")
        self.assertTrue(config["output_file"].endswith(".csv"))

    def test_cli_scrape_forwards_profile_and_exports_collected_tweets(self):
        profile = Path("test-profile").resolve()
        tweet = Tweet(
            id="1",
            text="archived post",
            date=datetime(2026, 7, 20),
            date_str="July 20, 2026",
            media_urls=[],
            tweet_url="https://x.com/example/status/1",
        )
        with TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            request = parse_scrape_request(
                [
                    "scrape",
                    "--profile",
                    "example",
                    "--count",
                    "1",
                    "--format",
                    "csv",
                    "--browser-profile",
                    str(profile),
                    "--output-dir",
                    str(output_dir),
                ]
            )
            factory = RecordingScraperFactory([tweet])

            self.assertEqual(run_cli_scrape(request, scraper_factory=factory), 0)
            self.assertEqual(factory.kwargs["browser_profile"], str(profile))
            self.assertTrue(factory.instance.started)
            self.assertTrue(factory.instance.stopped)
            self.assertTrue((output_dir / "example" / "example_tweets.csv").exists())

    def test_cli_scrape_returns_two_when_no_tweets_are_collected(self):
        request = parse_scrape_request(["scrape", "--profile", "example", "--count", "1"])

        self.assertEqual(
            run_cli_scrape(request, scraper_factory=RecordingScraperFactory([])),
            2,
        )

    def test_setup_driver_uses_explicit_chrome_profile(self):
        profile = Path("test-profile").resolve()
        options = RecordingChromeOptions()
        driver = FakeChromeDriver()
        with (
            patch("scraper.Options", return_value=options),
            patch("scraper.ChromeDriverManager") as manager,
            patch("scraper.Service"),
            patch("scraper.webdriver.Chrome", return_value=driver),
        ):
            manager.return_value.install.return_value = "chromedriver"
            XScraper(browser_profile=str(profile))._setup_driver()

        self.assertIn(f"--user-data-dir={profile}", options.arguments)


class RecordingChromeOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, value):
        self.arguments.append(value)

    def add_experimental_option(self, *_args):
        pass


class FakeChromeDriver:
    def execute_cdp_cmd(self, *_args):
        pass

    def implicitly_wait(self, *_args):
        pass

    def set_page_load_timeout(self, *_args):
        pass


if __name__ == "__main__":
    unittest.main()
