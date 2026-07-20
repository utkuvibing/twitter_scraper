# x-scraper

`x-scraper` is a local Python CLI for archiving public X profile posts and the signed-in user's bookmarks through an authorized Chrome session. It exports JSON, CSV, Markdown, or DOCX and writes a structured run log beside every target archive.

This project automates X's normal web interface. It does not bypass access controls, CAPTCHAs, rate limits, or browser security. X can change its interface without notice, so review important archives and run selector diagnostics when collection behavior changes.

> Release status: `1.0.0b1` (Beta). Browser-free automated checks cover Python 3.11-3.13 on Windows, macOS, and Linux. The live-X checks in [the release checklist](docs/RELEASE_CHECKLIST.md) must pass before publishing a stable `1.0.0` tag.

## Requirements

- Python 3.11, 3.12, or 3.13
- Google Chrome, or Chromium on Linux
- Network access on the first browser run if Selenium Manager needs to obtain a compatible ChromeDriver
- An X account and an authorized local session, including for bookmarks and headless runs

## Install

From a source checkout:

```bash
git clone https://github.com/utkuvibing/twitter_scraper.git
cd twitter_scraper
python -m pip install .
x-scraper --help
```

From a built wheel:

```bash
python -m pip install dist/x_scraper_cli-1.0.0b1-py3-none-any.whl
x-scraper --version
```

Windows users may also run `x-scraper.cmd` from a source checkout. It creates `.venv`, installs the project once when required, and then runs the same Python entry point. The installed `x-scraper` console command is preferred for normal use.

## 1. Prepare an authorized session

```bash
x-scraper login
```

This opens normal Chrome with an isolated profile below `.sessions/x-scraper` in the current directory. Sign in directly on X, then close that Chrome window. The application does not receive or store your password. Chrome stores its normal local profile data, including session cookies, inside that isolated directory; keep it private and never commit or share it.

To use a different isolated profile:

```bash
x-scraper login --browser-profile "C:\private\x-scraper-profile"
```

A scrape checks for Chrome profile artifacts before WebDriver starts. It then confirms both an authenticated X destination and signed-in X navigation/account UI. URL redirection alone is not treated as proof of authentication.

## 2. Archive content

Run the English interactive wizard:

```bash
x-scraper
```

Or use repeatable commands. The documented default isolated profile is selected automatically:

```bash
# Exactly 50 public profile posts as JSON
x-scraper scrape --profile example --count 50 --format json

# Profile posts from the last seven days as CSV
x-scraper scrape --profile example --days 7 --format csv

# Inclusive UTC date range as Markdown
x-scraper scrape --profile example --from 2026-07-01 --to 2026-07-20 --format md

# The signed-in account's bookmarks
x-scraper scrape --bookmarks --count 100 --format docx

# Reuse the prepared profile without displaying Chrome
x-scraper scrape --profile example --count 10 --headless
```

Exactly one source (`--profile` or `--bookmarks`) and one range (`--count`, `--days`, or `--from` plus `--to`) are required. Handles use X's 1-15 character letter/number/underscore format. Count is limited to 10,000 and days to 3,650. Output filenames cannot contain directories.

Use `--output-dir` to select another writable base directory, `--output` to select a filename, and `--browser-profile` to select another prepared isolated profile.

### Optional promotional filter

Archives preserve promotional language by default. To explicitly exclude posts containing a case-insensitive match for `link in bio`, `telegram`, `newsletter`, `free prompts`, `join my`, or `subscribe`, add:

```bash
x-scraper scrape --profile example --count 100 --exclude-promotional-posts
```

This filter can remove legitimate posts. Do not enable it when completeness is more important than topical filtering.

## Outputs and local paths

```bash
x-scraper paths
```

The default export root is the current working directory's `output` folder, never the installed package or `site-packages` directory:

```text
output/<target>/<filename>
output/<target>/logs/<run-id>_<status>_run_log.json
```

Writes use a same-directory temporary file followed by atomic replacement. Target and filename segments are sanitized for Windows, macOS, and Linux. Scraped content cannot select an output path. `--output-dir` is an explicit user-selected base directory.

### JSON schema 1.0

JSON preserves the original scraped text and emits UTC-aware ISO-8601 dates. A missing timestamp is represented as `null`; it is never replaced with the current time.

Each tweet contains:

```text
id, text, date, date_str, url, tweet_url, has_media, media_urls,
has_article, needs_full_text
```

Media URLs are validated, deduplicated, and kept in first-seen order. Engagement counters are intentionally absent because the scraper does not collect them reliably.

CSV uses the same supported fields, UTF-8 with BOM, and prefixes text cells beginning with `=`, `+`, `-`, or `@` so spreadsheet software does not execute archive content as a formula. JSON remains unchanged. Markdown renders tweet text as blockquotes so archived headings and links do not alter the document structure.

## Run outcomes and exit codes

Console output, the run log's `status`/`exit_code`, and the process exit code follow one contract:

| Exit | Status | Meaning |
|---:|---|---|
| `0` | `completed` | The requested count or chronological boundary was fully reached and exported. |
| `1` | `failed` | Authentication, browser startup/navigation, runtime, or export failed. |
| `2` | `invalid_input` or `failed` | Input was rejected before Chrome, or zero usable posts were collected. |
| `3` | `partial` | Usable posts were saved, but the requested target was not reached. |
| `130` | `cancelled` | Ctrl+C interrupted the run; collected posts were saved when possible. |

Requesting 100 posts and receiving 12 is not success: the export is retained, the run is `partial`, and the command exits 3. Date-filtered modes visibly exclude posts whose timestamp is unavailable while count archives retain them with `date: null`.

## Selector diagnostics

```bash
x-scraper diagnostics --url https://x.com/home
```

Diagnostics only accepts HTTPS URLs on `x.com` or `twitter.com`, with no embedded credentials or custom port. It reports selector presence; it does not dump page source or private page content. A passing selector check does not guarantee that X will allow or complete a long scrape.

## Troubleshooting

- **`x-scraper` is not recognized:** activate the environment where the package was installed, reinstall with `python -m pip install .`, or use `python main.py --help` from the checkout.
- **No prepared session:** run `x-scraper login` from the same working directory, finish X sign-in in the dedicated Chrome window, close it, and retry.
- **Session check fails after Chrome opens:** run `x-scraper login` again. Confirm the dedicated profile shows signed-in Home navigation before closing it.
- **Chrome cannot start:** install/update Chrome. If Selenium Manager is downloading ChromeDriver, confirm network and proxy settings allow it.
- **Collection stalls or returns partial:** preserve the partial export, run diagnostics, and check `output/<target>/logs/` for the classified reason. X may have reached the end, rate-limited the session, or changed selectors.
- **Headless fails while visible mode works:** refresh the prepared session in normal Chrome and retry visible mode before headless mode.
- **Windows launcher installs repeatedly:** update the checkout. The launcher dependency probe must import `selenium` and `docx`; it does not require `python-dotenv`.

Run logs redact registered browser-profile paths and sensitive token/cookie/password fields. They may contain public target handles, post URLs, selector names, counts, output paths, and concise exception diagnostics.

## Development and release checks

```bash
python -m pip install ".[dev]"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m build
python -m twine check dist/*
python scripts/wheel_smoke.py
pip-audit -r requirements.txt
```

GitHub Actions runs these gates on Ubuntu, Windows, and macOS with Python 3.11, 3.12, and 3.13, plus a gitleaks secret scan. Automated CI does not use a live X account.

## Known limitations

- X's private web UI and selectors are not a stable API.
- Protected, suspended, deleted, unavailable, or access-restricted posts cannot be archived unless the authorized session can normally view them.
- Reposts and replies are excluded from profile archives; quoted content remains part of the containing post text/card and is not emitted as a separate post.
- The tool records media URLs but does not download media files.
- X Articles and expanded long posts require additional page navigation and may remain flagged when extraction fails.
- Bookmark date modes must scroll the authorized account's bookmark timeline before local filtering and can finish partially if the timeline stalls.
- Engagement counts are not part of schema 1.0.

## Responsible use and privacy

Use `x-scraper` only for content and accounts you are authorized to access. Follow X's terms, applicable law, copyright, data-protection rules, and the expectations of people whose content you archive. Do not use it for private-data harvesting, surveillance, access-control evasion, or redistribution you are not permitted to perform.

Session profiles and exports remain local. `.sessions/` and `output/` are ignored by Git. The application does not upload archives, cookies, or credentials.

## License

[MIT](LICENSE)
