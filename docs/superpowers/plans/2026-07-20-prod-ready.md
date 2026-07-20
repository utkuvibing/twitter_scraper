# Production-Ready X Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an installable, safe, scriptable X/Twitter archival CLI while preserving the existing interactive manual-login workflow.

**Architecture:** Keep Selenium extraction in `scraper.py`; place all browser-free command parsing and request validation in a new `cli.py`. `main.py` dispatches arguments to the new CLI and retains the no-argument interactive wizard. CSV becomes a normalized-schema export beside JSON, Markdown, and DOCX; packaging and CI make the same release path verifiable outside the repository.

**Tech Stack:** Python 3.11+, argparse, Selenium, python-docx, setuptools, pytest, GitHub Actions.

## Global Constraints

- Preserve personal/authorized archival use; never add bypass, credential persistence, or password command-line arguments.
- Require Python `>=3.11`; bound runtime dependencies below their next major version.
- Keep existing JSON schema version `0.2` and safe output-path behavior unchanged.
- Use manual browser login for all new CLI scrape commands; reject `--headless` without `--browser-profile`.
- Execute every behavior change with a red-green test cycle and commit each completed task.

---

### Task 1: Browser-free CLI request model and validation

**Files:**
- Create: `cli.py`
- Create: `tests/test_cli.py`
- Modify: `main.py:1-40` and `main.py:311-627`

**Interfaces:**
- Produces `ScrapeRequest(target_username: str, scrape_type: str, mode_config: dict, output_file: str, output_format: str, output_dir: str | None, browser_profile: str | None, headless: bool)`.
- Produces `parse_scrape_request(argv: list[str]) -> ScrapeRequest` and `validate_diagnostics_url(value: str) -> str`.
- Produces `run_cli(argv: list[str] | None = None) -> int`; `main.main(argv: list[str] | None = None) -> int` dispatches to it when arguments exist.

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_scrape_request_accepts_a_profile_count_and_csv_output(tmp_path):
    request = parse_scrape_request([
        "scrape", "--profile", "example", "--count", "25",
        "--format", "csv", "--output-dir", str(tmp_path),
    ])
    assert request.target_username == "example"
    assert request.scrape_type == "profile"
    assert request.mode_config == {"mode": "count", "count": 25}
    assert request.output_format == "csv"

def test_parse_scrape_request_rejects_conflicting_sources():
    with pytest.raises(CliValidationError, match="exactly one source"):
        parse_scrape_request(["scrape", "--profile", "example", "--bookmarks", "--count", "1"])

def test_validate_diagnostics_url_rejects_a_non_x_host():
    with pytest.raises(CliValidationError, match="x.com"):
        validate_diagnostics_url("https://example.com")
```

- [ ] **Step 2: Run the tests to verify they fail because the module is missing**

Run: `python -m pytest tests/test_cli.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'cli'`.

- [ ] **Step 3: Implement the parser and request model**

```python
@dataclass(frozen=True)
class ScrapeRequest:
    target_username: str
    scrape_type: str
    mode_config: dict[str, object]
    output_file: str
    output_format: str
    output_dir: str | None
    browser_profile: str | None
    headless: bool

def parse_scrape_request(argv: list[str]) -> ScrapeRequest:
    parser = build_parser()
    namespace = parser.parse_args(argv)
    if namespace.command != "scrape":
        raise CliValidationError("expected the scrape command")
    return request_from_namespace(namespace)
```

`request_from_namespace` must reject an empty/invalid handle, non-positive count/days, incomplete or reversed ISO date ranges, a headless request without a profile, and unknown formats. `run_cli` must support `scrape`, `diagnostics`, and `--help`; it calls `run_cli_scrape(request)` only after validation. The no-argument `main.main()` path must call the preserved interactive implementation; move the current body into `run_interactive()` without changing its collection behavior.

- [ ] **Step 4: Run parser and regression tests**

Run: `python -m pytest tests/test_cli.py tests/test_diagnostics.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the task**

```bash
git add cli.py main.py tests/test_cli.py
git commit -m "feat: add validated non-interactive CLI"
```

### Task 2: Safe authorized Chrome-profile reuse and CLI scrape dispatch

**Files:**
- Modify: `cli.py`
- Modify: `scraper.py:64-117`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_scroll_helpers.py`

**Interfaces:**
- `XScraper(headless: bool = False, run_log: ScrapeRunLog | None = None, browser_profile: str | None = None)`.
- `run_cli_scrape(request: ScrapeRequest, scraper_factory: Callable[[bool, ScrapeRunLog | None, str | None], XScraper] = XScraper) -> int`.

- [ ] **Step 1: Write failing dispatch and profile tests**

```python
def test_run_cli_scrape_passes_the_selected_profile_to_the_scraper(tmp_path):
    request = parse_scrape_request([
        "scrape", "--profile", "example", "--count", "1",
        "--browser-profile", str(tmp_path),
    ])
    fake_factory = RecordingScraperFactory(tweets=[])
    assert run_cli_scrape(request, scraper_factory=fake_factory) == 2
    assert fake_factory.kwargs["browser_profile"] == str(tmp_path.resolve())

def test_setup_driver_adds_a_user_data_dir_for_an_explicit_profile(monkeypatch, tmp_path):
    scraper = XScraper(browser_profile=str(tmp_path))
    # Patch Chrome Options/WebDriver and assert --user-data-dir=<resolved path>.
```

- [ ] **Step 2: Run the targeted tests and verify expected failure**

Run: `python -m pytest tests/test_cli.py tests/test_scroll_helpers.py -q`

Expected: failure because `browser_profile` and `run_cli_scrape` do not yet exist.

- [ ] **Step 3: Implement profile forwarding and manual-login dispatch**

```python
def run_cli_scrape(request: ScrapeRequest, scraper_factory=XScraper) -> int:
    run_log = ScrapeRunLog(request.target_username, request.scrape_type, request.mode_config["mode"])
    scraper = scraper_factory(headless=request.headless, run_log=run_log,
                              browser_profile=request.browser_profile)
    try:
        scraper.start()
        if not scraper.manual_login():
            save_cli_run_log(run_log, "failed")
            return 1
        tweets = collect_request_tweets(scraper, request, run_log)
        if not tweets:
            record_event(run_log, "timeline_loading", "error", "No tweets collected", reason="timeline_empty")
            save_cli_run_log(run_log, "failed")
            return 2
        tweets.sort(key=lambda tweet: tweet.date or datetime.min, reverse=True)
        if request.output_format == "json":
            create_json_document(tweets, request.output_file, request.target_username,
                                 output_dir=request.output_dir, scrape_type=request.scrape_type)
        elif request.output_format == "csv":
            create_csv_document(tweets, request.output_file, request.target_username,
                                output_dir=request.output_dir)
        elif request.output_format == "md":
            create_markdown_document(tweets, request.output_file, request.target_username,
                                     output_dir=request.output_dir)
        else:
            create_word_document(tweets, request.output_file, request.target_username,
                                 output_dir=request.output_dir)
        save_cli_run_log(run_log, "completed")
        return 0
    finally:
        scraper.stop()

def collect_request_tweets(scraper, request, run_log):
    mode = request.mode_config
    if request.scrape_type == "bookmarks":
        if not scraper.navigate_to_bookmarks():
            record_event(run_log, "bookmarks_navigation", "error", "Bookmarks navigation failed",
                         reason="bookmarks_navigation_failed")
            return []
        if mode["mode"] == "count":
            return scraper.scrape_bookmarks(count=int(mode["count"]))
        tweets = scraper.scrape_bookmarks(get_all=True)
    else:
        if not scraper.navigate_to_profile(request.target_username):
            record_event(run_log, "profile_navigation", "error", "Profile navigation failed",
                         reason="profile_navigation_failed")
            return []
        if mode["mode"] == "count":
            return scraper.scrape_by_count(int(mode["count"]))
        if mode["mode"] == "days":
            return scraper.scrape_last_n_days(int(mode["days"]))
        return scraper.scrape_by_date(mode["start"], mode["end"])
    if mode["mode"] == "days":
        cutoff = datetime.now() - timedelta(days=int(mode["days"]))
        return [tweet for tweet in tweets if tweet.date and tweet.date >= cutoff]
    return [tweet for tweet in tweets if tweet.date and mode["start"] <= tweet.date <= mode["end"]]
```

In `_setup_driver`, append `--user-data-dir=<resolved profile>` only when `browser_profile` is not `None`. Do not log the path or use it to read/write any credentials directly.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_cli.py tests/test_scroll_helpers.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the task**

```bash
git add cli.py scraper.py tests/test_cli.py tests/test_scroll_helpers.py
git commit -m "feat: support authorized browser profiles"
```

### Task 3: CSV export with the public tweet schema

**Files:**
- Modify: `document_generator.py:1-270`
- Modify: `cli.py`
- Modify: `main.py:78-296` and `main.py:311-627`
- Modify: `tests/test_exports.py`

**Interfaces:**
- Produces `create_csv_document(tweets: list, output_path: str, target_username: str, output_dir: str | None = None) -> str`.
- CSV header is exactly `id,date,date_str,text,tweet_url,has_media,media_urls,has_article,needs_full_text,likes,retweets,replies,views`.

- [ ] **Step 1: Write a failing CSV export test**

```python
def test_csv_export_is_utf8_bom_and_uses_normalized_schema(tmp_path):
    path = create_csv_document([DummyTweet()], "tweets.csv", "@alice", output_dir=str(tmp_path))
    payload = Path(path).read_bytes()
    assert payload.startswith(codecs.BOM_UTF8)
    rows = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
    assert rows[0]["tweet_url"] == "https://x.com/alice/status/1"
    assert rows[0]["media_urls"] == "https://img.example/one.jpg"
```

- [ ] **Step 2: Run the test and verify it fails because the writer is missing**

Run: `python -m pytest tests/test_exports.py::DocumentExportTests::test_csv_export_is_utf8_bom_and_uses_normalized_schema -q`

Expected: import failure for `create_csv_document`.

- [ ] **Step 3: Implement atomic CSV output and wire both CLI paths**

```python
CSV_COLUMNS = ("id", "date", "date_str", "text", "tweet_url", "has_media", "media_urls",
               "has_article", "needs_full_text", "likes", "retweets", "replies", "views")

def create_csv_document(tweets, output_path, target_username, output_dir=None):
    full_path = resolve_output_path(target_username, output_path, ".csv", BASE_OUTPUT_DIR, output_dir)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for tweet in map(normalize_tweet, tweets):
        tweet["media_urls"] = " | ".join(tweet["media_urls"])
        writer.writerow({key: tweet[key] for key in CSV_COLUMNS})
    atomic_write_text(full_path, stream.getvalue(), encoding="utf-8-sig")
    return full_path
```

Add `csv` to the interactive and argparse format choices, maintaining exact extensions in partial/error exports.

- [ ] **Step 4: Run export and CLI tests**

Run: `python -m pytest tests/test_exports.py tests/test_cli.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the task**

```bash
git add document_generator.py main.py cli.py tests/test_exports.py tests/test_cli.py
git commit -m "feat: add CSV tweet exports"
```

### Task 4: Publishable packaging, readable UX, and CI release gates

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `requirements.txt`
- Modify: `main.py`, `scraper.py`, and `document_generator.py` user-facing prompts/messages only
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces console script `x-scraper = main:main`.
- Produces `main.py --version` with the package version and `main.py --help` with no browser startup.

- [ ] **Step 1: Write failing command-surface tests**

```python
def test_cli_version_does_not_start_a_browser(capsys, monkeypatch):
    monkeypatch.setattr(cli, "run_cli_scrape", pytest.fail)
    assert cli.run_cli(["--version"]) == 0
    assert "1.0.0" in capsys.readouterr().out

def test_cli_help_is_successful(capsys):
    assert cli.run_cli(["--help"]) == 0
    assert "scrape" in capsys.readouterr().out
```

- [ ] **Step 2: Run the command-surface tests and verify they fail**

Run: `python -m pytest tests/test_cli.py -q`

Expected: failure because version/help dispatch is incomplete.

- [ ] **Step 3: Add metadata and release gates**

```toml
[project]
name = "x-scraper-cli"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
  "selenium>=4.15,<5",
  "webdriver-manager>=4.0.1,<5",
  "python-docx>=1.1,<2",
]

[project.scripts]
x-scraper = "main:main"
```

Replace corrupted user-facing strings with clear English text, retaining behavior. In CI, test Python 3.11 and 3.12, run the full pytest suite and compilation, build a wheel/sdist, install the wheel into a clean virtual environment, then run `x-scraper --help` and `x-scraper --version`. Include `prod-ready` in push branch triggers.

- [ ] **Step 4: Run local packaging and smoke tests**

Run: `python -m pip install --upgrade build && python -m pytest -q && python -m compileall main.py cli.py scraper.py document_generator.py export_schema.py diagnostics.py config.py && python main.py --help && python main.py --version && python -m build`

Expected: tests pass, commands return zero without Chrome startup, and `dist/` contains a wheel and source archive.

- [ ] **Step 5: Commit the task**

```bash
git add pyproject.toml LICENSE README.md requirements.txt .github/workflows/ci.yml main.py scraper.py document_generator.py cli.py tests/test_cli.py
git commit -m "release: package the production CLI"
```

### Task 5: Release audit and publishing

**Files:**
- Modify: `README.md` only if validation exposes a documented mismatch
- Test: `tests/`

**Interfaces:**
- No new production interface; this task proves the release contract.

- [ ] **Step 1: Run the full release test matrix locally**

Run: `python -m pytest -q; python -m compileall main.py cli.py scraper.py document_generator.py export_schema.py diagnostics.py config.py; python main.py --help; python main.py --version; python -m build`

Expected: zero test failures, successful compilation/build, and browser-free CLI help/version output.

- [ ] **Step 2: Run clean-environment wheel smoke test**

Run: `python -m venv .release-smoke; .release-smoke\\Scripts\\python -m pip install dist\\*.whl; .release-smoke\\Scripts\\x-scraper --help; .release-smoke\\Scripts\\x-scraper --version`

Expected: the installed console script prints help and version with exit code 0.

- [ ] **Step 3: Run dependency and focused security checks**

Run: `python -m pip_audit -r requirements.txt; git grep -nE "password|token|secret" -- ':!tests'`

Expected: no known dependency vulnerability and no credentials persisted or accepted through CLI arguments. Review any grep hits to confirm they are interactive-only or documentation.

- [ ] **Step 4: Inspect the release diff and status**

Run: `git diff main...HEAD --check; git status --short --branch; git log --oneline main..HEAD`

Expected: no whitespace errors, clean branch, and focused production-ready commits.

- [ ] **Step 5: Commit any validation-only doc correction and publish**

```bash
git add README.md
git commit -m "docs: clarify release usage"
git push -u origin prod-ready
```

Run the README commit only when the inspection in Step 4 identified and corrected a real documentation mismatch; otherwise push the existing task commits without creating an empty commit.
