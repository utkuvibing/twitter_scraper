import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


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
        self.assertIn("https://x.com/i/flow/login", command)

    def test_manual_login_refuses_google_oauth_in_a_webdriver_window(self):
        from scraper import XScraper

        scraper = XScraper(browser_profile=".sessions/x-scraper")
        scraper.driver = UnauthenticatedDriver()
        with patch("builtins.input", return_value="") as login_input:
            self.assertFalse(scraper.manual_login())

        login_input.assert_not_called()


class UnauthenticatedDriver:
    current_url = "https://x.com/i/flow/login"

    def get(self, _url):
        pass


if __name__ == "__main__":
    unittest.main()
