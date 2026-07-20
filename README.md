# X Scraper CLI

`x-scraper` is a Python/Selenium command-line tool for personal, authorized X/Twitter archiving. It collects public profile posts or the signed-in user's bookmarks and exports them as JSON, CSV, Markdown, or DOCX.

The project automates the X web UI; it does not use a private API, bypass access controls, work around rate limits, or store credentials. X can change its UI at any time, so treat every scrape as best-effort and verify important exports.

## Requirements

- Python 3.11 or newer
- A current Chrome installation
- An X account only when using bookmarks or a local authenticated browser profile

Windows, macOS, and Linux are supported where Chrome and ChromeDriver are available. `webdriver-manager` retrieves a compatible driver during the first browser run.

## Install

```bash
git clone https://github.com/utkuvibing/twitter_scraper.git
cd twitter_scraper
python -m pip install --upgrade pip
python -m pip install .
x-scraper --help
```

To run directly from a source checkout, use `python main.py` instead of `x-scraper`.

## Quick start

Run without arguments for the interactive Turkish-language wizard. It defaults to manual browser login and guides you through the source, scope, and export format.

```bash
x-scraper
```

For repeatable scripts, use the non-interactive command. It always opens Chrome for manual login unless you explicitly supply a previously authorized browser profile.

```bash
# Archive 50 public posts as JSON.
x-scraper scrape --profile example --count 50 --format json

# Archive posts from the last 7 days as CSV in a chosen output directory.
x-scraper scrape --profile example --days 7 --format csv --output-dir exports

# Archive a date range as Markdown.
x-scraper scrape --profile example --from 2026-07-01 --to 2026-07-20 --format md

# Archive the current account's bookmarks.
x-scraper scrape --bookmarks --count 100 --format docx
```

Exactly one source (`--profile` or `--bookmarks`) and one collection mode (`--count`, `--days`, or `--from` plus `--to`) are required. Handles, dates, limits, output formats, and diagnostics URLs are checked before Chrome starts.

## Reusing an authorized Chrome profile

Use `--browser-profile` only for a local Chrome profile directory you control. First run it with a visible browser, sign in yourself, then reuse it for a future run. The profile may contain account session data: keep it private and never commit or share it.

```bash
# First run: Chrome opens and you sign in yourself.
x-scraper scrape --profile example --count 10 --browser-profile .sessions/x-scraper

# Later: use the same authorized profile without opening a window.
x-scraper scrape --profile example --count 10 --headless --browser-profile .sessions/x-scraper
```

Headless mode rejects a missing profile directory to avoid launching a new unauthenticated session. The CLI does not accept passwords as arguments and does not write credentials to exports or run logs.

## Exports and run logs

Exports are written to `output/<target>/` by default, or below `--output-dir` when supplied. Filenames and target folders are sanitized and writes are atomic.

- JSON: versioned schema (`schema_version: "0.2"`) for programmatic use
- CSV: UTF-8 with BOM for spreadsheet applications
- Markdown: readable archive with links
- DOCX: Word document archive

Every scrape and diagnostics run also writes a structured JSON log to `output/<target>/logs/`. Logs record stages, selector diagnostics, timings, failure reasons, and export paths; they do not contain credentials or browser-profile paths.

The CLI returns `0` for a completed export, `1` for a login/runtime/export error, and `2` when validation fails or no posts are collected.

## Selector diagnostics

Run diagnostics when X changes its UI or a scrape returns no results:

```bash
x-scraper diagnostics --url https://x.com/home
```

Diagnostics only accepts HTTPS X/Twitter URLs and reports whether core selectors are visible on the page. It does not guarantee that a full scrape will succeed. The former `python main.py --diagnostics` command remains supported.

## Development and release checks

```bash
python -m pytest
python -m compileall main.py x_scraper_cli.py scraper.py document_generator.py export_schema.py diagnostics.py config.py
python main.py --help
python main.py --version
python -m build
```

GitHub Actions runs the unit suite, compile check, package build, and clean-environment console-command smoke test on Python 3.11 and 3.12.

## Project structure

```text
main.py                 Interactive compatibility entry point
x_scraper_cli.py        Validated non-interactive command layer
scraper.py              Selenium extraction and browser setup
document_generator.py   JSON, CSV, Markdown, and DOCX writers
export_schema.py        Versioned JSON schema and safe atomic file helpers
diagnostics.py          Selector checks and structured run logs
tests/                  Browser-free validation suite
```

## Responsible use

Use this project only for content and accounts you are authorized to access, and comply with X's terms, applicable law, and privacy obligations. Do not use it to evade access controls, collect private data, or mass-harvest content.

## License

[MIT](LICENSE)
