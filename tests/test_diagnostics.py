import json
import os
import tempfile
import unittest

from diagnostics import (
    FAILURE_REASONS,
    RUN_LOG_SCHEMA_VERSION,
    ScrapeRunLog,
    classify_empty_result,
    record_event,
    run_selector_diagnostics,
    save_run_log,
)
from run_models import ExitCode, RunStatus


class FakeDriver:
    current_url = "https://x.com/example"

    def __init__(self, counts=None, errors=None):
        self.counts = counts or {}
        self.errors = errors or {}

    def find_elements(self, by, selector):
        key = (by, selector)
        if key in self.errors:
            raise self.errors[key]
        return [object()] * self.counts.get(key, 0)


class DiagnosticsTests(unittest.TestCase):
    def test_all_runtime_failure_reasons_are_registered(self):
        expected = {
            "manual_login_session_missing",
            "browser_start_failed",
            "tweet_date_unavailable",
            "user_cancelled",
            "export_failed",
        }

        self.assertTrue(expected.issubset(FAILURE_REASONS))

    def test_first_failure_is_preserved_and_warning_cannot_overwrite_it(self):
        run_log = ScrapeRunLog(target="example")
        record_event(run_log, "auth", "error", "missing", reason="manual_login_session_missing")
        record_event(run_log, "timeline", "warning", "empty", reason="timeline_empty")
        record_event(run_log, "export", "error", "disk", reason="export_failed")

        self.assertEqual(run_log.failure_reason, "manual_login_session_missing")

    def test_finalize_sets_status_exit_and_completed_timestamp_only_once(self):
        run_log = ScrapeRunLog(target="example")
        run_log.finalize(RunStatus.PARTIAL, ExitCode.PARTIAL)
        completed_at = run_log.completed_at
        run_log.finalize(RunStatus.FAILED, ExitCode.FAILED)

        payload = run_log.to_dict()
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["exit_code"], 3)
        self.assertEqual(run_log.completed_at, completed_at)

    def test_sensitive_values_and_fields_are_redacted_from_events(self):
        profile = r"C:\Users\name\.sessions\x-scraper"
        run_log = ScrapeRunLog(target="example", redactions=[profile])
        record_event(
            run_log,
            "browser",
            "error",
            f"Could not open {profile}",
            reason="browser_start_failed",
            browser_profile=profile,
            auth_token="secret-token",
        )

        payload = run_log.to_dict()
        serialized = json.dumps(payload)
        self.assertNotIn(profile, serialized)
        self.assertNotIn("secret-token", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_run_log_serializes_failure_reason_details(self):
        run_log = ScrapeRunLog(
            target="@Example", scrape_type="profile", mode="count", run_id="abc123"
        )
        event = record_event(
            run_log,
            "profile_navigation",
            "error",
            "Profile did not load",
            reason="profile_navigation_failed",
            selector="//article",
        )

        self.assertIsNotNone(event)
        payload = run_log.to_dict()
        self.assertEqual(payload["schema_version"], RUN_LOG_SCHEMA_VERSION)
        self.assertEqual(payload["failure_reason"], "profile_navigation_failed")
        self.assertEqual(
            payload["events"][0]["reason_detail"],
            "The profile page did not expose tweet timeline selectors.",
        )

    def test_selector_diagnostics_reports_required_missing(self):
        checks = [
            {
                "name": "tweet_article",
                "stage": "timeline_loading",
                "type": "xpath",
                "selector": "//article",
                "required": True,
            },
            {
                "name": "tweet_text",
                "stage": "tweet_parsing",
                "type": "css",
                "selector": "[data-testid='tweetText']",
                "required": False,
            },
        ]
        diagnostics = run_selector_diagnostics(FakeDriver(), checks)

        self.assertFalse(diagnostics["ok"])
        self.assertEqual(diagnostics["missing_required"], ["tweet_article"])
        self.assertEqual(diagnostics["checks"][0]["stage"], "timeline_loading")

    def test_selector_diagnostics_uses_counts(self):
        checks = [
            {
                "name": "tweet_article",
                "stage": "timeline_loading",
                "type": "xpath",
                "selector": "//article",
                "required": True,
            }
        ]
        diagnostics = run_selector_diagnostics(
            FakeDriver(counts={("xpath", "//article"): 3}),
            checks,
        )

        self.assertTrue(diagnostics["ok"])
        self.assertEqual(diagnostics["checks"][0]["count"], 3)

    def test_save_run_log_writes_under_target_logs_directory(self):
        run_log = ScrapeRunLog(target="../@bad:user", run_id="run1")
        record_event(run_log, "timeline_loading", "error", "No tweets", reason="timeline_empty")

        with tempfile.TemporaryDirectory() as tmp:
            path = save_run_log(run_log, tmp)
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(os.path.basename(os.path.dirname(path)), "logs")
            self.assertEqual(os.path.basename(os.path.dirname(os.path.dirname(path))), "bad_user")

            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

        self.assertEqual(payload["failure_reason"], "timeline_empty")
        self.assertEqual(payload["status"], "failed")

    def test_empty_result_classification(self):
        self.assertEqual(classify_empty_result("profile"), "timeline_empty")
        self.assertEqual(
            classify_empty_result("bookmarks", navigated=False), "bookmarks_navigation_failed"
        )


if __name__ == "__main__":
    unittest.main()
