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
    "profile_navigation_failed": "The profile page did not expose tweet timeline selectors.",
    "bookmarks_navigation_failed": "The bookmarks page did not expose tweet timeline selectors.",
    "timeline_empty": "No tweet articles were detected in the loaded timeline.",
    "timeline_stalled": "The timeline stopped advancing before the requested amount was collected.",
    "partial_target_not_met": "The scrape ended with fewer items than requested.",
    "browser_window_closed": "The browser window closed or ChromeDriver lost the active web view during scraping.",
    "tweet_parse_failed": "A tweet article was detected but required fields could not be parsed.",
    "full_text_failed": "A long tweet was detected but full text extraction returned no content.",
    "article_extraction_failed": "An X Article was detected but article content extraction returned no content.",
    "export_failed": "Export saving failed.",
    "unknown_error": "An unexpected scraper error occurred.",
}


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

    def add_event(
        self,
        stage: str,
        level: str,
        message: str,
        reason: Optional[str] = None,
        selector: Optional[str] = None,
        **details: Any,
    ) -> ScrapeEvent:
        event = ScrapeEvent(
            stage=stage,
            level=level,
            message=message,
            reason=reason,
            selector=selector,
            details={k: v for k, v in details.items() if v is not None},
        )
        self.events.append(event)
        if level in {"error", "critical"} and reason:
            self.failure_reason = reason
            self.status = "failed"
        return event

    def mark_completed(self, status: str = "completed") -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        completed_at = self.completed_at or datetime.now(timezone.utc)
        return {
            "schema_version": RUN_LOG_SCHEMA_VERSION,
            "run_id": self.run_id,
            "target": self.target,
            "scrape_type": self.scrape_type,
            "mode": self.mode,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "failure_detail": FAILURE_REASONS.get(self.failure_reason)
            if self.failure_reason
            else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round((completed_at - self.started_at).total_seconds(), 3),
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
        run_log.mark_completed(run_log.status)

    filename = f"{run_log.run_id}_{run_log.status}_run_log.json"
    base_dir = os.path.abspath(output_dir or base_output_dir)
    log_dir = os.path.join(base_dir, safe_path_segment(run_log.target, "export"), "logs")
    path = os.path.join(log_dir, filename)
    atomic_write_json(path, run_log.to_dict())
    return path
