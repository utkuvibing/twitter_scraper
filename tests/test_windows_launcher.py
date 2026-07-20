import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher requires cmd.exe")
def test_launcher_executes_without_reentering_install_when_dependencies_exist(tmp_path):
    project = tmp_path / "project with spaces"
    scripts = project / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "x-scraper.cmd", project / "x-scraper.cmd")
    (project / "main.py").write_text("print('x-scraper test entry')\n", encoding="utf-8")
    os.link(sys.executable, scripts / "python.exe")

    environment = os.environ.copy()
    environment["PIP_NO_INDEX"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(site.getsitepackages())
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "x-scraper.cmd"), "--version"],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Installing x-scraper" not in result.stdout
    assert "x-scraper" in result.stdout
