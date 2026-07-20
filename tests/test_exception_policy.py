import ast
from pathlib import Path

import pytest

from scraper import XScraper


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MODULES = (
    "chrome_auth.py",
    "diagnostics.py",
    "document_generator.py",
    "export_schema.py",
    "main.py",
    "scraper.py",
    "time_utils.py",
    "x_scraper_cli.py",
)


def test_runtime_modules_contain_no_bare_except_handlers():
    offenders = []
    for module_name in RUNTIME_MODULES:
        tree = ast.parse((ROOT / module_name).read_text(encoding="utf-8"))
        offenders.extend(
            f"{module_name}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler) and node.type is None
        )

    assert offenders == []


class ProgrammingErrorArticle:
    def find_element(self, _by, _selector):
        raise TypeError("selector integration bug")


def test_tweet_parser_does_not_swallow_unexpected_programming_errors():
    scraper = XScraper()

    with pytest.raises(TypeError, match="selector integration bug"):
        scraper._parse_tweet_element(ProgrammingErrorArticle())
