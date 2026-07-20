# Production Readiness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a tested, installable `x-scraper` whose dates, authentication, exports, run outcomes, and release artifacts have stable public contracts.

**Architecture:** Keep Selenium extraction in `scraper.py`, add browser-free datetime and outcome modules, and make `x_scraper_cli.py` the shared interactive/non-interactive orchestrator. Keep explicit setuptools `py-modules` packaging while using one dynamic version source and clean distribution manifests.

**Tech Stack:** Python 3.11-3.13, Selenium 4, python-docx, argparse, pytest, Ruff, mypy, build, twine, pip-audit, GitHub Actions.

## Global Constraints

- Work directly on `prod-ready` with no subagents.
- Use UTC-aware datetimes internally and never fabricate a missing tweet timestamp.
- Use only normal authorized Chrome sessions; no password CLI, security disabling, stealth, or access-control bypasses.
- Default exports to `Path.cwd() / "output"`; sanitize every target and filename segment.
- Apply stable exits 0/1/2/3/130 and statuses completed/failed/invalid_input/partial/cancelled.
- Add a failing regression test before each production behavior change.

---

### Task 1: UTC datetime and chronological collection contract

**Files:** Create `time_utils.py`, `tests/test_datetime_utils.py`, `tests/test_date_collection.py`; modify `scraper.py`, `x_scraper_cli.py`.

**Interfaces:** `ensure_utc(value: datetime) -> datetime`, `parse_x_datetime(value: str) -> datetime`, `utc_day_range(start: str, end: str) -> tuple[datetime, datetime]`, `tweet_sort_key(tweet) -> tuple`, and `Tweet.date: datetime | None`, `Tweet.is_pinned: bool`.

- [ ] Write tests using `2026-07-20T23:30:00-07:00`, naive CLI dates, aware bookmark cutoffs, `None` dates, and an old pinned/newer/three-old timeline.
- [ ] Run `python -m pytest tests/test_datetime_utils.py tests/test_date_collection.py -q`; expect failures from missing UTC helpers and first-old-item termination.
- [ ] Implement immediate UTC normalization, optional missing dates with `tweet_date_unavailable`, deterministic sorting, and three consecutive old non-pinned termination.
- [ ] Run the focused tests plus `tests/test_scroll_helpers.py`; expect all green.
- [ ] Commit as `fix: normalize dates and pinned range collection`.

### Task 2: Explicit outcomes and one orchestration path

**Files:** Create `run_models.py`, `tests/test_run_outcomes.py`; modify `x_scraper_cli.py`, replace duplicated orchestration in `main.py`, update `tests/test_cli.py`.

**Interfaces:** `RunStatus` string enum, `ExitCode` integer enum, `CollectionResult(items: list[Tweet], complete: bool, reason: str | None)`, and `run_cli_scrape(request, scraper_factory=XScraper) -> int`.

- [ ] Write failing tests for full count/0, short count/3, zero/2, auth or export failure/1, Ctrl+C with saved data/130, and identical interactive dispatch.
- [ ] Run `python -m pytest tests/test_run_outcomes.py tests/test_cli.py -q`; expect short counts to incorrectly return 0 and cancellation to lack a shared path.
- [ ] Implement one lifecycle that deduplicates/sorts, writes safe partial data, finalizes logs once, and maps outcomes to console/status/exit codes.
- [ ] Remove direct interactive password collection and make the wizard build a validated `ScrapeRequest` using the isolated profile.
- [ ] Re-run focused tests; expect all green.
- [ ] Commit as `fix: unify scrape outcomes and CLI orchestration`.

### Task 3: Authentication, logs, paths, and export integrity

**Files:** Modify `chrome_auth.py`, `diagnostics.py`, `export_schema.py`, `document_generator.py`, `x_scraper_cli.py`, `scraper.py`; create/update `tests/test_auth_contract.py`, `tests/test_diagnostics.py`, `tests/test_exports.py`, `tests/test_cli.py`.

**Interfaces:** `is_prepared_profile(path: Path) -> bool`, `authenticated_x_ui_present(driver) -> bool`, `ScrapeRunLog.finalize(status, exit_code)`, `csv_safe(value) -> str`, and `default_output_dir() -> Path`.

- [ ] Write failing tests for missing default profile before scraper construction, UI-based auth, profile-path redaction, registered reasons, immutable first failure, one completion timestamp, cwd output, CSV `= + - @` prefixes, media dedupe, and no engagement fields.
- [ ] Run the focused test files; expect current URL-only auth, site-package output, schema, and log tests to fail.
- [ ] Implement the auth/profile contract, sensitive diagnostic sanitizer, stable log finalization, cwd output, formula mitigation, schema cleanup, and explicit opt-in `--exclude-promotional-posts`.
- [ ] Run the focused tests; expect all green.
- [ ] Commit as `fix: harden authentication logs and exports`.

### Task 4: Selenium reliability and Windows launcher

**Files:** Modify `scraper.py`, `chrome_auth.py`, `x-scraper.cmd`, `tests/test_scroll_helpers.py`, `tests/test_chrome_auth.py`, `tests/test_windows_launcher.py`.

**Interfaces:** bounded WebDriver command timeout, JavaScript-first `_perform_timeline_scroll`, Selenium Manager driver startup, and launcher dependency probe `import selenium, docx`.

- [ ] Add failing tests that prove scroll avoids the blocking multi-command sequence, command timeout is configured, Chrome/Chromium discovery covers supported OS paths, and the real Windows launcher succeeds on a second offline invocation.
- [ ] Run the targeted tests; expect the launcher to re-enter install because `dotenv` is absent and scroll/driver tests to fail.
- [ ] Remove `webdriver-manager`, bound driver commands/retries, use specific Selenium exceptions, make shutdown safe, and remove `dotenv` from the launcher probe.
- [ ] Re-run targeted tests; expect all green.
- [ ] Commit as `fix: bound browser operations and launcher bootstrap`.

### Task 5: Packaging, CI, documentation, and release verification

**Files:** Create `version.py`, `MANIFEST.in`, `CHANGELOG.md`, `docs/RELEASE_CHECKLIST.md`, `tests/test_wheel_smoke.py`; modify `pyproject.toml`, `requirements.txt`, `.github/workflows/ci.yml`, `README.md`, `tests/test_release_metadata.py`.

**Interfaces:** `version.__version__` is used dynamically by setuptools and CLI; `x-scraper paths` prints cwd-derived browser-free paths.

- [ ] Add failing metadata/content/smoke tests for the canonical version, Beta classifier, Python 3.11-3.13 matrix on three OSes, clean sdist/wheel contents, and installed default output location.
- [ ] Run metadata tests; expect version drift, unsupported CI claims, and package-content failures.
- [ ] Configure dev tools and CI, document exits/schema/auth/limitations/responsible use, add changelog and manual live-X checklist, and exclude development artifacts from distributions.
- [ ] Install configured release tools, run focused metadata tests, then run Ruff format once and repair only reported semantic lint/type failures.
- [ ] Commit as `release: add verified beta release gates`.

### Task 6: Full release gate and publication audit

**Files:** All changed files; no new behavior unless a gate exposes a verified defect.

**Interfaces:** None; this task proves the release contract.

- [ ] Run `python -m pytest -q` and record the exact pass count.
- [ ] Run `python -m ruff check .`, `python -m ruff format --check .`, configured mypy, and `python -m compileall`.
- [ ] Run `python -m build`, `python -m twine check dist/*`, inspect archive contents, create a fresh venv, install only the wheel, and run installed `x-scraper --help`, `--version`, and `paths` from a temporary cwd.
- [ ] Run `python -m pip_audit`, `python -m pip check`, `git diff --check`, tracked-file secret/session scans, and inspect `git diff`/`git status` for generated or unrelated files.
- [ ] Push verified commits to `origin/prod-ready`; report any unperformed live-X checklist items without calling them verified.
