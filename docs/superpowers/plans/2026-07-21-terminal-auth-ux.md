# x-scraper Terminal Authentication UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain Turkish interactive flow with an English, dependency-free colored terminal wizard and prepare Google/Apple X sessions in normal Chrome before Selenium reuses them.

**Architecture:** A small `terminal_ui.py` module owns ANSI color detection and presentation so prompts do not embed escape sequences. A separate `chrome_auth.py` module owns the persistent session path and normal Chrome launch; `main.py` uses it for the wizard while `x_scraper_cli.py` exposes it as `x-scraper login`.

**Tech Stack:** Python 3.11 standard library (`os`, `pathlib`, `shutil`, `subprocess`, `sys`), argparse, unittest, Selenium (existing only).

## Global Constraints

- Use only the Python standard library for terminal presentation; do not add a UI dependency.
- Use ANSI colors when supported and render equivalent plain text for `NO_COLOR` or non-terminal streams.
- Keep prompts ASCII-safe for CMD and PowerShell.
- Keep `scrape`, `diagnostics`, `--help`, and `--version` script-friendly.
- The Google/Apple sign-in flow must use normal Chrome, never ChromeDriver.
- Default persistent session directory is `.sessions/x-scraper`; it remains ignored by Git.
- Never log passwords, cookies, or the browser-profile path.

---

### Task 1: Add dependency-free terminal presentation

**Files:**
- Create: `terminal_ui.py`
- Modify: `tests/test_cli.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces `TerminalUI(stream: TextIO | None = None, color: bool | None = None)`.
- Produces `TerminalUI.banner() -> None`, `section(title: str, number: int | None = None) -> None`, `choice(number: int, label: str, detail: str = "") -> None`, and `status(kind: str, message: str) -> None`.
- `kind` is one of `"info"`, `"success"`, `"warning"`, or `"error"`; callers receive a plain label if color is disabled.

- [ ] **Step 1: Write the failing tests**

```python
from terminal_ui import TerminalUI

def test_terminal_ui_emits_colored_banner_when_color_is_enabled():
    stream = io.StringIO()
    TerminalUI(stream=stream, color=True).banner()
    output = stream.getvalue()
    self.assertIn("x-scraper", output)
    self.assertIn("\x1b[", output)

def test_terminal_ui_has_plain_text_fallback():
    stream = io.StringIO()
    TerminalUI(stream=stream, color=False).status("success", "Ready")
    self.assertEqual(stream.getvalue(), "[OK] Ready\n")
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_cli.py -q`

Expected: FAIL because `terminal_ui` does not exist.

- [ ] **Step 3: Implement the smallest presentation module**

```python
class TerminalUI:
    COLORS = {"info": "36", "success": "32", "warning": "33", "error": "31"}
    LABELS = {"info": "INFO", "success": "OK", "warning": "WARN", "error": "ERROR"}

    def __init__(self, stream=None, color=None):
        self.stream = stream or sys.stdout
        self.color = self.stream.isatty() if color is None else color
        self.color = self.color and not bool(os.environ.get("NO_COLOR"))

    def status(self, kind, message):
        label = self.LABELS[kind]
        prefix = f"[{label}]"
        if self.color:
            prefix = f"\033[{self.COLORS[kind]}m{prefix}\033[0m"
        print(f"{prefix} {message}", file=self.stream)
```

Implement `banner`, `section`, and `choice` with the same `print(..., file=self.stream)` behavior and ASCII separators. Add `terminal_ui` to the `py-modules` list in `pyproject.toml`.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python -m pytest tests/test_cli.py -q`

Expected: PASS, including the existing CLI validation tests.

- [ ] **Step 5: Commit the task**

```bash
git add terminal_ui.py tests/test_cli.py pyproject.toml
git commit -m "feat: add portable colored terminal UI"
```

### Task 2: Launch normal Chrome and expose `x-scraper login`

**Files:**
- Create: `chrome_auth.py`
- Modify: `x_scraper_cli.py`
- Modify: `pyproject.toml`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces `default_browser_profile(cwd: Path | None = None) -> str` returning an absolute `.sessions/x-scraper` path.
- Produces `find_chrome_executable() -> str | None` that checks `shutil.which("chrome")` and normal Windows Chrome locations.
- Produces `open_chrome_for_x_login(browser_profile: str) -> int`; it returns `0` after normal Chrome closes and `1` when Chrome cannot be found or launched.
- `run_cli(["login"])` calls `open_chrome_for_x_login(default_browser_profile())` and must not create `XScraper`.

- [ ] **Step 1: Write the failing tests**

```python
def test_login_command_opens_a_normal_chrome_profile_without_scraping(self):
    expected_profile = str((Path.cwd() / ".sessions" / "x-scraper").resolve())
    with patch("x_scraper_cli.open_chrome_for_x_login", return_value=0) as open_chrome:
        self.assertEqual(run_cli(["login"]), 0)
    open_chrome.assert_called_once_with(expected_profile)

def test_normal_chrome_login_uses_an_isolated_profile(self):
    with patch("chrome_auth.find_chrome_executable", return_value="chrome.exe"), patch(
        "chrome_auth.subprocess.run"
    ) as run:
        self.assertEqual(open_chrome_for_x_login("C:/sessions/x-scraper"), 0)
    command = run.call_args.args[0]
    self.assertEqual(command[0], "chrome.exe")
    self.assertIn("--user-data-dir=C:/sessions/x-scraper", command)
    self.assertIn("https://x.com/i/flow/login", command)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_cli.py::CliRequestTests::test_login_command_opens_a_normal_chrome_profile_without_scraping -q`

Expected: FAIL because `login` is not an argparse subcommand.

- [ ] **Step 3: Implement the normal Chrome launch flow**

```python
def open_chrome_for_x_login(browser_profile: str) -> int:
    chrome = find_chrome_executable()
    if not chrome:
        print("[ERROR] Google Chrome was not found. Install Chrome and run x-scraper login again.")
        return 1
    profile = Path(browser_profile).expanduser().resolve()
    profile.parent.mkdir(parents=True, exist_ok=True)
    print("[INFO] Chrome is opening. Sign in to X, then close every Chrome window to continue.")
    try:
        subprocess.run([chrome, f"--user-data-dir={profile}", X_LOGIN_URL], check=False)
    except OSError as exc:
        print(f"[ERROR] Chrome could not start: {exc}")
        return 1
    return 0
```

In `build_parser`, add a `login` subparser with optional `--browser-profile` defaulting to `default_browser_profile()`. In `run_cli`, dispatch it before the help fallback. Add `chrome_auth` to `pyproject.toml`.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -q`

Expected: PASS, including login dispatch and normal Chrome command assertions.

- [ ] **Step 5: Commit the task**

```bash
git add chrome_auth.py x_scraper_cli.py pyproject.toml tests/test_cli.py
git commit -m "feat: add normal Chrome login command"
```

### Task 3: Integrate the English wizard and prevent OAuth in WebDriver

**Files:**
- Modify: `main.py`
- Modify: `scraper.py`
- Modify: `README.md`
- Modify: `tests/test_cli.py`

**Interfaces:**
- `get_user_input()` returns `browser_profile: str | None` and `prepare_browser_profile: bool` in addition to its existing scrape configuration.
- `run_interactive()` calls `open_chrome_for_x_login(config["browser_profile"])` before constructing `XScraper` when `prepare_browser_profile` is true, then passes `browser_profile=config["browser_profile"]` to `XScraper`.
- `XScraper.manual_login()` returns `False` when the profile is unauthenticated and tells the user to run `x-scraper login`; it never suggests Google/Apple in its WebDriver window.

- [ ] **Step 1: Write the failing tests**

```python
@patch("builtins.input", side_effect=["1", "1", "example", "1", "1", "4", ""])
def test_interactive_wizard_uses_the_dedicated_browser_profile(self, _input):
    config = get_user_input()
    self.assertEqual(config["browser_profile"], str((Path.cwd() / ".sessions" / "x-scraper").resolve()))
    self.assertTrue(config["prepare_browser_profile"])

def test_manual_login_rejects_google_oauth_in_webdriver(self):
    scraper = XScraper()
    scraper.driver = FakeUnauthenticatedDriver("https://x.com/i/flow/login")
    with patch("builtins.input", side_effect=AssertionError):
        self.assertFalse(scraper.manual_login())
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_cli.py -q`

Expected: FAIL because the wizard does not return a profile configuration and `manual_login` still prompts for a browser login.

- [ ] **Step 3: Implement the English interactive flow**

Change the login section in `get_user_input()` to present:

```text
[1] Account session
1. Sign in with Google or Apple in normal Chrome (recommended)
2. Sign in to X with an X username and password
```

For option `1`, set `manual_login=True`, `browser_profile=default_browser_profile()`, and `prepare_browser_profile=True`. Translate all wizard headings, questions, validation notices, and completion messages to English, routing headings and status messages through `TerminalUI`. In `run_interactive()`, abort when the normal Chrome setup returns non-zero, instantiate `XScraper(headless=False, run_log=run_log, browser_profile=config["browser_profile"])`, and preserve the existing collection/export behavior.

Change `manual_login()` to navigate to X, return success only when the persistent session redirects away from login/flow, and otherwise print `Run x-scraper login to sign in using normal Chrome; Google and Apple sign-in are not available in this browser window.` before returning `False`.

Update README quick start with `x-scraper login`, then `x-scraper`; remove the statement that Google/Apple can be completed in the Selenium browser.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python -m pytest tests/test_cli.py -q`

Expected: PASS; no test invokes a real browser.

- [ ] **Step 5: Run release validation**

Run: `python -m pytest -q`

Expected: PASS for the full suite.

Run: `cmd /d /c "x-scraper --version"`

Expected: `x-scraper 1.0.0`.

Run: `python -m compileall main.py x_scraper_cli.py scraper.py terminal_ui.py chrome_auth.py`

Expected: all listed modules compile without errors.

- [ ] **Step 6: Commit the task**

```bash
git add main.py scraper.py README.md tests/test_cli.py
git commit -m "feat: add English interactive login wizard"
```

### Task 4: Publish the completed UX

**Files:**
- Modify: no source files expected

**Interfaces:**
- Consumes the completed Task 1-3 commits.
- Produces a pushed `prod-ready` branch containing the normal-Chrome authentication path and the portable terminal UI.

- [ ] **Step 1: Inspect the release diff and worktree**

Run: `git status --short --branch`

Expected: only intentional files are changed and the branch is `prod-ready`.

- [ ] **Step 2: Push the branch**

Run: `git push origin prod-ready`

Expected: remote `prod-ready` receives the implementation commits.
