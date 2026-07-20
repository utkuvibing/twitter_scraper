# Production-Ready X Scraper Design

## Context

The project is a Python/Selenium CLI for personal, authorized X/Twitter archiving. The current extraction and export layers have browser-free tests, but the product is difficult to automate or publish: it has only prompt-driven input, no installable package metadata or console command, no CSV export, inconsistent user-facing text, and no clear release contract.

## Goals

1. Make installation, discovery, and day-to-day invocation predictable on Windows, macOS, and Linux.
2. Preserve the existing interactive manual-login workflow while adding a validated non-interactive CLI for reproducible profile and bookmark scrapes.
3. Add CSV export for spreadsheet workflows without weakening the existing JSON, Markdown, or DOCX contracts.
4. Allow an explicitly chosen local Chrome profile directory to reuse an already-authorized browser session; do not store, log, or accept passwords through command-line arguments.
5. Improve failure messages, input validation, diagnostics safety, tests, CI, packaging metadata, and release documentation.

## Non-Goals

- Bypassing X access controls, rate limits, bot checks, or private-content restrictions.
- Downloading media, adding cloud sync, creating a GUI, or making live-browser scraping deterministic.
- Storing credentials or tokens in repository files, output files, command history, or run logs.

## Alternatives Considered

### 1. Rewrite the scraper around an API or a new browser framework

This could provide a cleaner architecture, but it would invalidate the existing tested selectors and require credentials or platform access that the product deliberately avoids. It is not appropriate for a release-hardening branch.

### 2. Focused CLI and release hardening (recommended)

Keep the existing Selenium extraction engine and introduce a small, testable command layer, output extension, session-profile configuration, and publication artifacts. This adds immediate user value while containing regression risk.

### 3. Add a desktop UI

A UI would improve discoverability but contradicts the repository's intentional CLI-only direction and would substantially expand build, signing, and support requirements.

## Product Design

### Commands and user flows

`python main.py` remains the interactive wizard for manual login. The installable command `x-scraper` exposes the same behavior plus these non-interactive commands:

```text
x-scraper scrape --profile example --count 50 --format csv
x-scraper scrape --bookmarks --days 7 --format json --browser-profile .sessions/chrome
x-scraper diagnostics --url https://x.com/home
x-scraper --version
```

The command layer validates exactly one source (`--profile` or `--bookmarks`) and exactly one scrape mode (`--count`, `--days`, or `--from` with `--to`). Invalid dates, non-positive limits, invalid handles, unsafe browser-profile paths, and non-X diagnostics URLs fail before Chrome starts with a clear message and non-zero exit status.

Manual login stays the default. Headless use requires an explicit local `--browser-profile` directory so a user can reuse a session they already authorized in Chrome. Password arguments are intentionally not added.

### Boundaries

- `main.py` owns the entry point and interactive compatibility layer.
- A new `x_scraper_cli.py` module owns `argparse`, request validation, and conversion to the existing scrape configuration shape. It is browser-free and directly unit tested.
- A small orchestration function owns one scrape run and receives a scraper factory and export writer mapping, allowing browser-free tests for dispatch, exit statuses, and partial exports.
- `scraper.py` accepts an optional browser-profile directory and adds only the corresponding Chrome option after validating it is a local filesystem path.
- `document_generator.py` adds CSV export using the normalized public tweet schema, preventing format-specific field drift.

### Data and exports

CSV contains one row per tweet with stable columns: `id`, `date`, `date_str`, `text`, `tweet_url`, `has_media`, `media_urls`, `has_article`, `needs_full_text`, `likes`, `retweets`, `replies`, and `views`. The writer uses UTF-8 with BOM for spreadsheet compatibility and the existing atomic safe-path helpers.

JSON remains schema version `0.2`; its shape is unchanged. Markdown and DOCX keep their existing output behavior. All output paths remain under the requested output root and per-target folder.

### Errors, diagnostics, and security controls

Argument validation happens before browser startup. Diagnostics accepts only `https://x.com/...`, `https://www.x.com/...`, and `https://twitter.com/...` URLs to prevent the tool from becoming a generic browser launcher. Browser profile paths must resolve to a directory supplied by the user; they are never copied into logs. Run logs continue to omit credentials and add configuration-safe context only.

### Packaging and release contract

`pyproject.toml` declares Python 3.11+, runtime dependencies, a console script, package metadata, and repository links. A root MIT `LICENSE`, `.gitignore` coverage for test/build artifacts, and expanded README sections document installation, commands, security expectations, Chrome requirements, supported platforms, and release verification. CI runs the full unit suite, bytecode compilation, and a smoke check for `--help` and `--version` on Python 3.11 and 3.12.

## Test Strategy

Every behavioral change follows red-green TDD:

1. Parser tests cover valid and invalid source/mode combinations, dates, handles, profile paths, and diagnostics URLs.
2. Export tests cover CSV headers, quoting, UTF-8 BOM, normalized field values, and safe filenames.
3. Orchestration tests use a fake scraper to cover profile/bookmark dispatch, writer dispatch, partial statuses, and browser-profile forwarding.
4. Existing diagnostics, export, and scroll-helper tests remain green.
5. Release verification runs `python -m pytest`, `python -m compileall ...`, `python main.py --help`, `python main.py --version`, and package build/install smoke tests in a clean virtual environment.

## Acceptance Criteria

- `prod-ready` contains a single documented release-ready product path and is pushed to origin.
- A new user can install with `pip install .`, run `x-scraper --help`, and use the interactive wizard.
- Scripted scrape and diagnostics commands validate input before Chrome starts and return actionable exit codes.
- CSV exports are atomic, safe-path constrained, spreadsheet-friendly, and fully tested.
- Manual-login and authorized-profile workflows do not expose credentials in CLI arguments or run logs.
- Full unit tests, compilation, CLI smoke tests, package build, clean-environment install smoke test, and focused security review pass with recorded evidence.
