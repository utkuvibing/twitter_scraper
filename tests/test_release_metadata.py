import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):
    def test_project_metadata_exposes_the_console_command(self):
        with (ROOT / "pyproject.toml").open("rb") as metadata_file:
            metadata = tomllib.load(metadata_file)

        project = metadata["project"]
        self.assertEqual(project["name"], "x-scraper-cli")
        self.assertEqual(project["version"], "1.0.0")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["scripts"]["x-scraper"], "main:main")

    def test_project_includes_an_mit_license_text(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted", license_text)

    def test_runtime_dependencies_use_selenium_manager_without_webdriver_manager(self):
        with (ROOT / "pyproject.toml").open("rb") as metadata_file:
            metadata = tomllib.load(metadata_file)
        dependencies = metadata["project"]["dependencies"]
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertFalse(any("webdriver-manager" in item for item in dependencies))
        self.assertNotIn("webdriver-manager", requirements)


if __name__ == "__main__":
    unittest.main()
