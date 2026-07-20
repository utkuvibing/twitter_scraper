"""UTC datetime policy shared by scraping, filtering, sorting, and exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any, Iterable, TypeVar


T = TypeVar("T")


def utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime, interpreting naive values as UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_x_datetime(value: str) -> datetime:
    """Parse an ISO-8601 timestamp returned by X and normalize it to UTC."""
    if not value:
        raise ValueError("X timestamp is empty")
    return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def utc_day_range(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse inclusive YYYY-MM-DD boundaries as UTC-aware datetimes."""
    start_day = datetime.strptime(start, "%Y-%m-%d").date()
    end_day = datetime.strptime(end, "%Y-%m-%d").date()
    return (
        datetime.combine(start_day, time.min, tzinfo=timezone.utc),
        datetime.combine(end_day, time.max, tzinfo=timezone.utc),
    )


def filter_tweets_by_range(
    tweets: Iterable[T], start: datetime, end: datetime
) -> tuple[list[T], list[T]]:
    """Split tweets into in-range items and items with unavailable timestamps."""
    normalized_start = ensure_utc(start)
    normalized_end = ensure_utc(end)
    kept: list[T] = []
    missing: list[T] = []
    for tweet in tweets:
        value = getattr(tweet, "date", None)
        if value is None:
            missing.append(tweet)
        elif normalized_start <= ensure_utc(value) <= normalized_end:
            kept.append(tweet)
    return kept, missing


def tweet_sort_key(tweet: Any) -> tuple[datetime, str]:
    """Return a deterministic key that safely orders missing/naive dates."""
    value = getattr(tweet, "date", None)
    normalized = (
        ensure_utc(value)
        if isinstance(value, datetime)
        else datetime.min.replace(tzinfo=timezone.utc)
    )
    return normalized, str(getattr(tweet, "id", ""))


def deduplicate_tweets(tweets: Iterable[T]) -> list[T]:
    """Keep the first item for each stable post ID or URL."""
    unique: list[T] = []
    seen: set[str] = set()
    for index, tweet in enumerate(tweets):
        item_id = str(getattr(tweet, "id", "") or "")
        url = str(getattr(tweet, "tweet_url", "") or "")
        key = item_id or url or f"__unidentified_{index}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(tweet)
    return unique


@dataclass
class DateRangeStopTracker:
    """Stop only after a stable run of old, non-pinned chronological posts."""

    start: datetime
    consecutive_old_required: int = 3
    consecutive_old: int = 0

    def __post_init__(self) -> None:
        self.start = ensure_utc(self.start)
        if self.consecutive_old_required < 1:
            raise ValueError("consecutive_old_required must be positive")

    def observe(self, value: datetime | None, is_pinned: bool = False) -> bool:
        if value is None or is_pinned:
            return False
        if ensure_utc(value) < self.start:
            self.consecutive_old += 1
        else:
            self.consecutive_old = 0
        return self.consecutive_old >= self.consecutive_old_required
