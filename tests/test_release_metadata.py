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
        from version import __version__

        self.assertEqual(__version__, "1.0.0b1")
        self.assertIn("version", project["dynamic"])
        self.assertNotIn("version", project)
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["scripts"]["x-scraper"], "main:main")

    def test_metadata_is_beta_and_declares_every_tested_python(self):
        with (ROOT / "pyproject.toml").open("rb") as metadata_file:
            project = tomllib.load(metadata_file)["project"]

        self.assertIn("Development Status :: 4 - Beta", project["classifiers"])
        self.assertNotIn("Development Status :: 5 - Production/Stable", project["classifiers"])
        for version in ("3.11", "3.12", "3.13"):
            self.assertIn(f"Programming Language :: Python :: {version}", project["classifiers"])

    def test_all_runtime_modules_are_explicitly_packaged(self):
        with (ROOT / "pyproject.toml").open("rb") as metadata_file:
            metadata = tomllib.load(metadata_file)
        modules = set(metadata["tool"]["setuptools"]["py-modules"])

        self.assertTrue({"run_models", "time_utils", "version"}.issubset(modules))

    def test_ci_covers_three_operating_systems_and_python_311_through_313(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

        for runner in ("ubuntu-latest", "windows-latest", "macos-latest"):
            self.assertIn(runner, workflow)
        for version in ('"3.11"', '"3.12"', '"3.13"'):
            self.assertIn(version, workflow)
        for gate in ("ruff check", "mypy", "twine check", "pip-audit"):
            self.assertIn(gate, workflow)

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
