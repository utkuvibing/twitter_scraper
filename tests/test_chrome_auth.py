import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException

class ChromeAuthTests(unittest.TestCase):
    def test_normal_chrome_login_uses_an_isolated_profile(self):
        from chrome_auth import open_chrome_for_x_login

        with TemporaryDirectory() as temporary_directory:
            profile = str(Path(temporary_directory) / "x-scraper")
            with (
                patch("chrome_auth.find_chrome_executable", return_value="chrome.exe"),
                patch("chrome_auth.subprocess.run") as run,
            ):
                self.assertEqual(open_chrome_for_x_login(profile), 0)

        command = run.call_args.args[0]
        self.assertEqual(command[0], "chrome.exe")
        self.assertIn(f"--user-data-dir={profile}", command)
        self.assertIn("--disable-background-mode", command)
        self.assertIn("https://x.com/i/flow/login", command)

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
