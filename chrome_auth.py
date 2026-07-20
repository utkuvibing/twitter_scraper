"""Prepare a persistent X session in a normal, user-controlled Chrome window."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import X_LOGIN_URL
from terminal_ui import TerminalUI


AUTHENTICATED_X_SELECTORS = (
    '[data-testid="AppTabBar_Home_Link"]',
    '[data-testid="SideNav_AccountSwitcher_Button"]',
)


def default_browser_profile(cwd: Path | None = None) -> str:
    """Return the isolated profile used by the interactive x-scraper flow."""
    root = cwd or Path.cwd()
    return str((root / ".sessions" / "x-scraper").resolve())


def is_prepared_profile(profile: Path) -> bool:
    """Return whether Chrome has initialized the isolated local profile."""
    return profile.is_dir() and (
        (profile / "Local State").is_file() or (profile / "Default").is_dir()
    )


def authenticated_x_ui_present(driver: object) -> bool:
    """Confirm both an authenticated X destination and signed-in navigation UI."""
    current_url = str(getattr(driver, "current_url", "")).lower()
    if (
        not current_url.startswith("https://x.com/")
        or "/login" in current_url
        or "/flow/" in current_url
        or "/i/flow" in current_url
    ):
        return False
    find_elements = getattr(driver, "find_elements", None)
    if not callable(find_elements):
        return False
    return any(
        bool(find_elements("css selector", selector))
        for selector in AUTHENTICATED_X_SELECTORS
    )


def find_chrome_executable() -> str | None:
    """Locate a normal Chrome executable without relying on WebDriver."""
    for name in ("chrome", "google-chrome"):
        executable = shutil.which(name)
        if executable:
            return executable

    if sys.platform == "win32":
        candidates = []
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(variable)
            if root:
                candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
    elif sys.platform == "darwin":
        candidate = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if candidate.is_file():
            return str(candidate)

    return None


def open_chrome_for_x_login(browser_profile: str) -> int:
    """Open normal Chrome for a human X login and wait until the window closes."""
    ui = TerminalUI()
    chrome = find_chrome_executable()
    if not chrome:
        ui.status("error", "Google Chrome was not found. Install Chrome, then run x-scraper login again.")
        return 1

    profile = Path(browser_profile).expanduser()
    try:
        profile.parent.mkdir(parents=True, exist_ok=True)
        ui.status(
            "info",
            "Chrome is opening. Sign in to X, then close this x-scraper Chrome window to continue.",
        )
        subprocess.run(
            [
                chrome,
                "--disable-background-mode",
                f"--user-data-dir={browser_profile}",
                X_LOGIN_URL,
            ],
            check=False,
        )
    except OSError as exc:
        ui.status("error", f"Chrome could not start: {exc}")
        return 1
    ui.status("success", "Chrome session is ready. Starting x-scraper.")
    return 0
