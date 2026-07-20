# Production Readiness Hardening Design

## Scope and release posture

This hardening pass turns `prod-ready` into a public, installable local archival CLI. It keeps Selenium and the existing selector strategy, but makes run outcomes, dates, authentication, exports, and packaging explicit and testable. Until browser-free release gates and the maintainer's live-X checklist pass, package metadata remains Beta rather than claiming Production/Stable.

The tool continues to support only authorized, normal Chrome sessions. It will not accept passwords as command-line arguments, automate third-party identity providers, disable browser security, or add stealth, CAPTCHA, proxy, or rate-limit bypass features.

## Approaches considered

1. **Rewrite into a `src/x_scraper/` package and replace the scraper engine.** This would create clean import boundaries, but it would combine release hardening with a high-risk migration of a working selector engine.
2. **Keep all existing loose modules and patch each caller independently.** This minimizes individual diffs but preserves the duplicated interactive/non-interactive behavior that caused status, date, and output inconsistencies.
3. **Focused shared-core hardening (selected).** Keep the explicit top-level modules packaged by setuptools, add small browser-free datetime and outcome modules, and route both command surfaces through one orchestration path. This satisfies installability and reliability requirements without an unrelated framework rewrite.

## Architecture

- `time_utils.py` is the only datetime policy. Internally all datetimes are UTC-aware. Naive user dates are interpreted as UTC, X timestamps are normalized immediately, day cutoffs use an injectable UTC clock, missing timestamps remain `None`, and sorting has a safe deterministic key.
- `run_models.py` defines stable statuses and exit codes: completed/0, failed/1, invalid_input or zero usable results/2, partial/3, and cancelled/130. A collection result explicitly states whether the requested boundary was reached.
- `x_scraper_cli.py` validates the entire request before constructing Selenium. It applies the documented isolated profile by default, checks that a prepared profile exists, validates output paths and limits, and owns the common scrape/export/log lifecycle.
- `main.py` retains the English wizard but converts its answers into the same validated request and calls the same orchestration. The direct username/password flow and duplicated scrape/export implementation are removed.
- `scraper.py` remains the Selenium extraction engine. Tweet dates become optional UTC datetimes; pinned state is explicit; date scraping stops only after three consecutive dated, non-pinned posts older than the start boundary. Promotional filtering is off unless explicitly requested. Bounded scroll commands and typed Selenium exceptions replace broad swallowing where practical.
- `export_schema.py` and `document_generator.py` preserve original text in JSON, remove unsupported engagement counters, deduplicate media URLs, mitigate CSV formula injection, represent unavailable dates as null, and write beneath `Path.cwd() / "output"` by default.
- `diagnostics.py` validates failure reasons, sanitizes sensitive fields and registered profile paths, preserves the first meaningful failure reason, and finalizes a run exactly once with status and exit code.

## Authentication contract

`x-scraper login` opens normal Chrome with a dedicated local profile. The user signs in directly to X and closes that Chrome window. A scrape uses the documented default profile unless `--browser-profile` is supplied. A missing/unprepared profile fails before WebDriver starts with instructions to run `x-scraper login`. After WebDriver starts, authentication is confirmed using both an authenticated X destination and authenticated navigation/account UI selectors; URL redirection alone is insufficient. Headless mode follows the same contract.

The application never reads or logs cookie values, tokens, passwords, page source, or private page contents. Browser profile paths are redacted from structured diagnostics.

## Data and completion semantics

Count mode is complete only when the requested count is exported. Date modes are complete only when the chronological boundary is reached; a stalled timeline produces a partial export. Missing timestamps are retained in count archives with a structured warning and excluded visibly from date-filtered results. Duplicate IDs are removed before deterministic sorting.

If usable posts exist after a recoverable shortfall or browser loss, the export is saved with `partial` status and exit 3. Ctrl+C saves collected data when possible, records `cancelled`, and exits 130. Zero usable posts exits 2. Authentication, browser, and export failures exit 1. Console text, JSON run logs, and process codes use the same decision.

## Packaging and operations

`version.py` is the canonical version source for package metadata and `--version`. Selenium Manager replaces the extra `webdriver-manager` dependency and is invoked only when a scrape/diagnostics browser starts. The sdist excludes local tests, session/output data, generated artifacts, and planning documents; the wheel contains every runtime module.

CI covers Windows, macOS, and Ubuntu on Python 3.11-3.13. It runs pytest, compilation, Ruff lint/format checks, focused mypy, build, twine, clean-wheel command/default-path smoke tests, dependency audit, and secret scanning. A manual release checklist covers live profile/bookmark/date/headless/interruption/diagnostics behavior without requiring an X account in CI.

## Test strategy and completion gate

Every behavior change starts with a focused failing test. Unit tests cover UTC normalization, aware X timestamps, bookmark/profile filtering, pinned termination, missing dates, statuses/exit codes, log finalization and redaction, safe paths, CSV injection, schema shape, Chrome discovery, authentication UI checks, and scroll bounds. Windows executes the real `.cmd` launcher twice, with the second run offline, proving it does not re-enter installation.

The release gate is: full tests green; Ruff/mypy/compile checks green; wheel and sdist build; twine check; wheel installed into a fresh venv; installed `x-scraper --help`, `--version`, and `paths` remain browser-free; package contents inspected; dependency and secret scans reviewed; final diff clean. Live-X checks are reported separately and never implied by browser-free tests.
