from datetime import datetime, timezone

from time_utils import (
    ensure_utc,
    filter_tweets_by_range,
    parse_x_datetime,
    tweet_sort_key,
    utc_day_range,
)


class DatedItem:
    def __init__(self, item_id: str, date: datetime | None):
        self.id = item_id
        self.date = date


def test_parse_x_datetime_normalizes_an_actual_offset_timestamp_to_utc():
    parsed = parse_x_datetime("2026-07-20T23:30:00-07:00")

    assert parsed == datetime(2026, 7, 21, 6, 30, tzinfo=timezone.utc)
    assert parsed.tzinfo is timezone.utc


def test_ensure_utc_interprets_naive_cli_values_as_utc():
    assert ensure_utc(datetime(2026, 7, 21, 12, 0)) == datetime(
        2026, 7, 21, 12, 0, tzinfo=timezone.utc
    )


def test_utc_day_range_includes_the_full_end_day():
    start, end = utc_day_range("2026-07-19", "2026-07-20")

    assert start == datetime(2026, 7, 19, tzinfo=timezone.utc)
    assert end == datetime(2026, 7, 20, 23, 59, 59, 999999, tzinfo=timezone.utc)


def test_filter_range_handles_aware_tweets_and_keeps_missing_dates_visible():
    items = [
        DatedItem("inside", datetime(2026, 7, 20, 10, tzinfo=timezone.utc)),
        DatedItem("outside", datetime(2026, 7, 18, 10, tzinfo=timezone.utc)),
        DatedItem("missing", None),
    ]

    kept, missing = filter_tweets_by_range(
        items,
        datetime(2026, 7, 19),
        datetime(2026, 7, 21),
    )

    assert [item.id for item in kept] == ["inside"]
    assert [item.id for item in missing] == ["missing"]


def test_sort_key_never_compares_naive_and_aware_datetimes():
    items = [
        DatedItem("missing", None),
        DatedItem("aware", datetime(2026, 7, 20, tzinfo=timezone.utc)),
        DatedItem("naive", datetime(2026, 7, 21)),
    ]

    ordered = sorted(items, key=tweet_sort_key, reverse=True)

    assert [item.id for item in ordered] == ["naive", "aware", "missing"]
