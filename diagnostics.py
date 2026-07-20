"""
Scrape diagnostics and run-log helpers.

The code here is intentionally small and mostly browser-independent. Selenium is
only needed when a caller asks to inspect selectors on a live driver.
"""

import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from config import CORE_SELECTOR_CHECKS
from export_schema import atomic_write_json, safe_path_segment


RUN_LOG_SCHEMA_VERSION = "0.3"


FAILURE_REASONS = {
    "login_failed": "Login did not complete successfully.",
    "manual_login_timeout": "Manual login was not confirmed before the timeout.",
    "manual_login_session_missing": "No authenticated X session was found in the selected Chrome profile.",
    "browser_start_failed": "Chrome or ChromeDriver could not be started.",
    "browser_navigation_timeout": "Chrome did not finish navigating before the configured timeout.",
    "profile_navigation_failed": "The profile page did not expose tweet timeline selectors.",
    "bookmarks_navigation_failed": "The bookmarks page did not expose tweet timeline selectors.",
    "timeline_empty": "No tweet articles were detected in the loaded timeline.",
    "timeline_stalled": "The timeline stopped advancing before the requested amount was collected.",
    "partial_target_not_met": "The scrape ended with fewer items than requested.",
    "browser_window_closed": "The browser window closed or ChromeDriver lost the active web view during scraping.",
    "tweet_parse_failed": "A tweet article was detected but required fields could not be parsed.",
    "tweet_date_unavailable": "A tweet was preserved without a fabricated timestamp.",
    "full_text_failed": "A long tweet was detected but full text extraction returned no content.",
    "article_extraction_failed": "An X Article was detected but article content extraction returned no content.",
    "export_failed": "Export saving failed.",
    "user_cancelled": "The user interrupted the scrape.",
    "invalid_input": "The supplied command input failed validation.",
    "unknown_error": "An unexpected scraper error occurred.",
}

_SENSITIVE_FIELD_MARKERS = (
    "password",
    "cookie",
    "token",
    "authorization",
    "browser_profile",
    "profile_path",
    "page_source",
)


@dataclass
class ScrapeEvent:
    stage: str
    level: str
    message: str
    reason: Optional[str] = None
    selector: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["reason_detail"] = FAILURE_REASONS.get(self.reason) if self.reason else None
        return data


class ScrapeRunLog:
    """Collects structured events for one scrape or diagnostics run."""

    def __init__(
        self,
        target: str = "export",
        scrape_type: str = "profile",
        mode: Optional[str] = None,
        run_id: Optional[str] = None,
        redactions: Optional[Iterable[str]] = None,
    ):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.target = str(target or "export").lstrip("@")
        self.scrape_type = scrape_type
        self.mode = mode
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.status = "running"
        self.events: List[ScrapeEvent] = []
        self.failure_reason: Optional[str] = None
        self.exit_code: Optional[int] = None
        self._redactions = [str(value) for value in (redactions or []) if value]

    def _sanitize(self, value: Any, key: Optional[str] = None) -> Any:
        if key and any(marker in key.lower() for marker in _SENSITIVE_FIELD_MARKERS):
            return "[REDACTED]"
        if isinstance(value, dict):
            return {item_key: self._sanitize(item, item_key) for item_key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            sanitized = value
            for secret in self._redactions:
                sanitized = sanitized.replace(secret, "[REDACTED]")
            return sanitized
        return value

    def add_event(
        self,
        stage: str,
        level: str,
        message: str,
        reason: Optional[str] = None,
        selector: Optional[str] = None,
        **details: Any,
    ) -> ScrapeEvent:
        if reason is not None and reason not in FAILURE_REASONS:
            raise ValueError(f"unregistered failure reason: {reason}")
        event = ScrapeEvent(
            stage=stage,
            level=level,
            message=self._sanitize(message),
            reason=reason,
            selector=selector,
            details={
                key: self._sanitize(value, key)
                for key, value in details.items()
                if value is not None
            },
        )
        self.events.append(event)
        if level in {"error", "critical"} and reason and self.failure_reason is None:
            self.failure_reason = reason
            self.status = "failed"
        return event

    def mark_completed(self, status: str = "completed") -> None:
        default_exit_codes = {
            "completed": 0,
            "failed": 1,
            "invalid_input": 2,
            "partial": 3,
            "cancelled": 130,
        }
        self.finalize(status, default_exit_codes.get(str(status), 1))

    def finalize(self, status: Any, exit_code: Any) -> None:
        """Finalize once so later warnings or cleanup cannot change the outcome."""
        if self.completed_at is not None:
            return
        normalized_status = str(status)
        allowed = {"completed", "partial", "cancelled", "failed", "invalid_input"}
        if normalized_status not in allowed:
            raise ValueError(f"unsupported run status: {normalized_status}")
        self.status = normalized_status
        self.exit_code = int(exit_code)
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        measured_at = self.completed_at or datetime.now(timezone.utc)
        return {
            "schema_version": RUN_LOG_SCHEMA_VERSION,
            "run_id": self.run_id,
            "target": self.target,
            "scrape_type": self.scrape_type,
            "mode": self.mode,
            "status": self.status,
            "exit_code": self.exit_code,
            "failure_reason": self.failure_reason,
            "failure_detail": FAILURE_REASONS.get(self.failure_reason)
            if self.failure_reason
            else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round((measured_at - self.started_at).total_seconds(), 3),
            "events": [event.to_dict() for event in self.events],
        }


def record_event(
    run_log: Optional[ScrapeRunLog],
    stage: str,
    level: str,
    message: str,
    reason: Optional[str] = None,
    selector: Optional[str] = None,
    **details: Any,
) -> Optional[ScrapeEvent]:
    if run_log is None:
        return None
    return run_log.add_event(stage, level, message, reason, selector, **details)


def classify_empty_result(scrape_type: str, navigated: bool = True) -> str:
    if not navigated:
        return (
            "bookmarks_navigation_failed"
            if scrape_type == "bookmarks"
            else "profile_navigation_failed"
        )
    return "timeline_empty"


def _driver_find_count(driver: Any, by: str, selector: str) -> int:
    elements = driver.find_elements(by, selector)
    return len(elements)


def run_selector_diagnostics(
    driver: Any,
    checks: Optional[Iterable[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Check configured selectors against the current live browser page."""
    checks = list(checks or CORE_SELECTOR_CHECKS)
    results = []

    for check in checks:
        selector_type = check.get("type", "xpath")
        selector = check["selector"]
        by = "xpath" if selector_type == "xpath" else "css selector"
        started = time.perf_counter()
        count = 0
        error = None

        try:
            count = _driver_find_count(driver, by, selector)
        except Exception as exc:
            error = str(exc)

        results.append(
            {
                "name": check["name"],
                "stage": check.get("stage", "unknown"),
                "required": bool(check.get("required", False)),
                "type": selector_type,
                "selector": selector,
                "count": count,
                "ok": error is None and (count > 0 or not check.get("required", False)),
                "error": error,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )

    required = [item for item in results if item["required"]]
    missing_required = [item["name"] for item in required if not item["ok"]]

    return {
        "schema_version": RUN_LOG_SCHEMA_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "current_url": getattr(driver, "current_url", None),
        "ok": not missing_required,
        "missing_required": missing_required,
        "checks": results,
    }


def add_diagnostics_to_log(
    run_log: Optional[ScrapeRunLog],
    diagnostics: Dict[str, Any],
    stage: str = "selector_diagnostics",
) -> None:
    if run_log is None:
        return
    level = "info" if diagnostics.get("ok") else "warning"
    run_log.add_event(
        stage=stage,
        level=level,
        message="Selector diagnostics completed",
        reason=None if diagnostics.get("ok") else "timeline_empty",
        missing_required=diagnostics.get("missing_required", []),
        checks=diagnostics.get("checks", []),
        current_url=diagnostics.get("current_url"),
    )


def save_run_log(
    run_log: ScrapeRunLog,
    base_output_dir: str,
    output_dir: Optional[str] = None,
) -> str:
    """Save a run log under output/<target>/logs/ atomically."""
    if run_log.completed_at is None:
        status = run_log.status if run_log.status != "running" else "failed"
        run_log.mark_completed(status)

    filename = f"{run_log.run_id}_{run_log.status}_run_log.json"
    base_dir = os.path.abspath(output_dir or base_output_dir)
    log_dir = os.path.join(base_dir, safe_path_segment(run_log.target, "export"), "logs")
    path = os.path.join(log_dir, filename)
    atomic_write_json(path, run_log.to_dict())
    return path
