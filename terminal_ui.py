"""Portable, dependency-free presentation helpers for the interactive CLI."""

from __future__ import annotations

import os
import sys
from typing import TextIO


class TerminalUI:
    """Render concise CLI output with an automatic plain-text fallback."""

    COLORS = {
        "info": "36",
        "success": "32",
        "warning": "33",
        "error": "31",
        "accent": "35",
    }
    LABELS = {
        "info": "INFO",
        "success": "OK",
        "warning": "WARN",
        "error": "ERROR",
    }

    def __init__(self, stream: TextIO | None = None, color: bool | None = None):
        self.stream = stream or sys.stdout
        requested_color = self.stream.isatty() if color is None else color
        self.color = bool(requested_color) and not bool(os.environ.get("NO_COLOR"))

    def _paint(self, text: str, color: str) -> str:
        if not self.color:
            return text
        return f"\033[{self.COLORS[color]}m{text}\033[0m"

    def banner(self) -> None:
        print(self._paint("+------------------------------------------+", "accent"), file=self.stream)
        print(self._paint("|                x-scraper                 |", "accent"), file=self.stream)
        print("|     personal X archive command line      |", file=self.stream)
        print(self._paint("+------------------------------------------+", "accent"), file=self.stream)

    def section(self, title: str, number: int | None = None) -> None:
        prefix = f"[{number}] " if number is not None else ""
        print("", file=self.stream)
        print(self._paint(f"{prefix}{title}", "accent"), file=self.stream)
        print(self._paint("-" * 42, "accent"), file=self.stream)

    def choice(self, number: int, label: str, detail: str = "") -> None:
        message = f"{number}. {label}"
        if detail:
            message += f" - {detail}"
        print(message, file=self.stream)

    def status(self, kind: str, message: str) -> None:
        if kind not in self.LABELS:
            raise ValueError(f"unsupported status kind: {kind}")
        label = f"[{self.LABELS[kind]}]"
        print(f"{self._paint(label, kind)} {message}", file=self.stream)
