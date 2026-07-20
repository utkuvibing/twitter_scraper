import unittest
from unittest.mock import patch

from main import main
from x_scraper_cli import CliValidationError, parse_scrape_request, validate_diagnostics_url


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


if __name__ == "__main__":
    unittest.main()
