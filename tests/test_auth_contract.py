from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from chrome_auth import authenticated_x_ui_present, is_prepared_profile
from run_models import ExitCode
from x_scraper_cli import run_cli


class AuthDriver:
    def __init__(self, url: str, selector_hits: int):
        self.current_url = url
        self.selector_hits = selector_hits

    def find_elements(self, _by, _selector):
        return [object()] * self.selector_hits


def test_authenticated_x_ui_requires_destination_and_authenticated_ui():
    assert not authenticated_x_ui_present(AuthDriver("https://x.com/home", 0))
    assert not authenticated_x_ui_present(
        AuthDriver("https://x.com/i/flow/login", 1)
    )
    assert authenticated_x_ui_present(AuthDriver("https://x.com/home", 1))


def test_prepared_profile_requires_chrome_profile_artifacts():
    with TemporaryDirectory() as temporary_directory:
        profile = Path(temporary_directory)
        assert not is_prepared_profile(profile)
        (profile / "Local State").write_text("{}", encoding="utf-8")
        assert is_prepared_profile(profile)


def test_missing_default_profile_fails_before_scrape_runner_is_called():
    with TemporaryDirectory() as temporary_directory:
        missing = Path(temporary_directory) / "missing-profile"
        with (
            patch("x_scraper_cli.default_browser_profile", return_value=str(missing)),
            patch("x_scraper_cli.is_prepared_profile", return_value=False, create=True),
        ):
            called = []
            code = run_cli(
                ["scrape", "--profile", "example", "--count", "1"],
                scrape_runner=lambda request: called.append(request) or 0,
            )

    assert code == ExitCode.INVALID_INPUT
    assert called == []
