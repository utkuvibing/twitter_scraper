import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsLauncherTests(unittest.TestCase):
    def test_launcher_bootstraps_a_project_virtual_environment(self):
        launcher = (ROOT / "x-scraper.cmd").read_text(encoding="utf-8")

        self.assertIn(".venv\\Scripts\\python.exe", launcher)
        self.assertIn("-m pip install", launcher)
        self.assertIn('"%APP_ROOT%\\main.py"', launcher)
        self.assertIn('set "APP_ROOT=%APP_ROOT:~0,-1%"', launcher)
        self.assertIn('python -m venv "%APP_ROOT%\\.venv"', launcher)


if __name__ == "__main__":
    unittest.main()
