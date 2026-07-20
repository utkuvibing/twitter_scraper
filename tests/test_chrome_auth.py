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


if __name__ == "__main__":
    unittest.main()
