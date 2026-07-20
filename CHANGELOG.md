# Changelog

All notable changes are documented here. Versions follow Semantic Versioning; Python package pre-release notation uses PEP 440.

## 1.0.0b1 - 2026-07-21

Beta release candidate for the stable `1.0.0` contract.

### Added

- Installable `x-scraper` console command with interactive and scripted profile/bookmark flows.
- Isolated normal-Chrome login command and reusable authenticated profile validation.
- Explicit completed, partial, cancelled, failed, and invalid-input outcomes with stable exit codes.
- UTC datetime normalization, pinned-post-safe range termination, missing-date warnings, and deterministic deduplication.
- JSON schema 1.0, CSV/DOCX/Markdown exports, atomic writes, CSV formula mitigation, and media URL validation.
- Structured selector diagnostics and redacted per-run logs.
- Windows launcher subprocess regression coverage and cross-platform Chrome/Chromium discovery.
- Windows/macOS/Linux CI on Python 3.11-3.13 with lint, type, package, audit, smoke, and secret gates.

### Changed

- Default exports now resolve from the invocation's current working directory.
- Promotional posts are preserved unless `--exclude-promotional-posts` is explicitly supplied.
- Selenium Manager replaces `webdriver-manager`.
- The wizard and scripted CLI share one collection/export/outcome lifecycle.
- Package status is Beta until the manual live-X release checklist passes.

### Removed

- The undeclared `python-dotenv` Windows launcher probe.
- Fabricated current timestamps for posts with unavailable dates.
- Unsupported engagement counters from the public export schema.
- Duplicate Turkish/English interactive orchestration and interactive password collection.
