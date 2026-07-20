"""Install the built wheel into a fresh venv and verify browser-free commands."""

from __future__ import annotations

import os
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

from version import __version__

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = {
    "chrome_auth.py",
    "config.py",
    "diagnostics.py",
    "document_generator.py",
    "export_schema.py",
    "main.py",
    "run_models.py",
    "scraper.py",
    "terminal_ui.py",
    "time_utils.py",
    "version.py",
    "x_scraper_cli.py",
}


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


def main() -> int:
    wheels = sorted((ROOT / "dist").glob(f"x_scraper_cli-{__version__}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one wheel, found {len(wheels)}")

    with zipfile.ZipFile(wheels[0]) as wheel_file:
        names = set(wheel_file.namelist())
    missing_modules = RUNTIME_MODULES - names
    if missing_modules:
        raise RuntimeError(f"wheel is missing runtime modules: {sorted(missing_modules)}")
    if any(name.startswith(("tests/", "docs/superpowers/")) for name in names):
        raise RuntimeError("wheel contains development-only files")

    with tempfile.TemporaryDirectory(prefix="x-scraper-wheel-") as temporary_directory:
        workspace = Path(temporary_directory)
        environment = workspace / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        command = scripts / ("x-scraper.exe" if os.name == "nt" else "x-scraper")

        run([str(python), "-m", "pip", "install", str(wheels[0])])
        run([str(command), "--help"], cwd=workspace)
        version_result = run([str(command), "--version"], cwd=workspace)
        paths_result = run([str(command), "paths"], cwd=workspace)

        if __version__ not in version_result.stdout:
            raise RuntimeError("installed CLI version does not match package metadata")
        expected_output = str((workspace / "output").resolve())
        if f"output_dir={expected_output}" not in paths_result.stdout:
            raise RuntimeError("installed CLI default output is not based on the working directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
