"""Stable public run statuses and process exit codes."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class RunStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INVALID_INPUT = "invalid_input"


class ExitCode(IntEnum):
    COMPLETED = 0
    FAILED = 1
    INVALID_INPUT = 2
    NO_RESULTS = 2
    PARTIAL = 3
    CANCELLED = 130
