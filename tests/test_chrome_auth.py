import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException


class ChromeAuthTests(unittest.TestCase):
    def test_linux_discovery_accepts_google_chrome_and_chromium(self):
        from chrome_auth import find_chrome_executable

        def locate(name):
            return "/usr/bin/chromium" if name == "chromium" else None

        with (
            patch("chrome_auth.sys.platform", "linux"),
            patch("chrome_auth.shutil.which", side_effect=locate),
        ):
            self.assertEqual(find_chrome_executable(), "/usr/bin/chromium")

    def test_windows_discovery_handles_program_files_paths(self):
        from chrome_auth import find_chrome_executable

        environment = {"PROGRAMFILES": r"C:\Program Files"}
        with (
            patch("chrome_auth.sys.platform", "win32"),
            patch("chrome_auth.shutil.which", return_value=None),
            patch.dict(os.environ, environment, clear=True),
            patch("chrome_auth.Path.is_file", return_value=True),
        ):
            found = find_chrome_executable()

        self.assertEqual(
            found,
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        )

    def test_macos_discovery_checks_the_standard_application_bundle(self):
        from chrome_auth import find_chrome_executable

        with (
            patch("chrome_auth.sys.platform", "darwin"),
            patch("chrome_auth.shutil.which", return_value=None),
            patch("chrome_auth.Path.is_file", return_value=True),
        ):
            found = find_chrome_executable()

        self.assertEqual(
            found.replace("\\", "/"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )

    def test_normal_chrome_login_uses_an_isolated_profile(self):
        from chrome_auth import open_chrome_for_x_login

        with TemporaryDirectory() as temporary_directory:
            profile = str(Path(temporary_directory) / "x-scraper")
            with (
                patch("chrome_auth.find_chrome_executable", return_value="chrome.exe"),
                patch(
                    "chrome_auth.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 0),
                ) as run,
            ):
                self.assertEqual(open_chrome_for_x_login(profile), 0)

        command = run.call_args.args[0]
        self.assertEqual(command[0], "chrome.exe")
        self.assertIn(f"--user-data-dir={profile}", command)
        self.assertIn("--disable-background-mode", command)
        self.assertIn("https://x.com/i/flow/login", command)
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_normal_chrome_login_reports_a_nonzero_process_exit(self):
        from chrome_auth import open_chrome_for_x_login

        with TemporaryDirectory() as temporary_directory:
            with (
                patch("chrome_auth.find_chrome_executable", return_value="chrome.exe"),
                patch(
                    "chrome_auth.subprocess.run",
                    return_value=subprocess.CompletedProcess([], 7),
                ),
            ):
                self.assertEqual(open_chrome_for_x_login(temporary_directory), 1)

    def test_manual_login_refuses_google_oauth_in_a_webdriver_window(self):
        from scraper import XScraper

        scraper = XScraper(browser_profile=".sessions/x-scraper")
        scraper.driver = UnauthenticatedDriver()
        with (
            patch("builtins.input", return_value="") as login_input,
            patch("scraper.WebDriverWait", ImmediateWait),
        ):
            self.assertFalse(scraper.manual_login())

        login_input.assert_not_called()

    def test_manual_login_accepts_a_session_that_redirects_after_login_flow(self):
        from scraper import XScraper

        scraper = XScraper(browser_profile=".sessions/x-scraper")
        driver = DelayedAuthenticatedDriver()
        scraper.driver = driver
        with patch("scraper.WebDriverWait", DelayedWait):
            self.assertTrue(scraper.manual_login())

        self.assertEqual(driver.requested_url, "https://x.com/home")


class UnauthenticatedDriver:
    current_url = "https://x.com/i/flow/login"

    def get(self, _url):
        pass


class DelayedAuthenticatedDriver:
    def __init__(self):
        self.url_checks = 0
        self.requested_url = None

    def get(self, url):
        self.requested_url = url

    def find_elements(self, _by, _selector):
        return [object()] if self.url_checks > 1 else []

    @property
    def current_url(self):
        self.url_checks += 1
        if self.url_checks == 1:
            return "https://x.com/i/flow/login"
        return "https://x.com/home"


class ImmediateWait:
    def __init__(self, driver, _timeout):
        self.driver = driver

    def until(self, condition):
        result = condition(self.driver)
        if not result:
            raise TimeoutException()
        return result


class DelayedWait(ImmediateWait):
    def until(self, condition):
        if condition(self.driver):
            return True
        return super().until(condition)


if __name__ == "__main__":
    unittest.main()
