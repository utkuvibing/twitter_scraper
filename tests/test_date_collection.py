from datetime import datetime, timezone

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from diagnostics import ScrapeRunLog
from scraper import Tweet, XScraper
from time_utils import DateRangeStopTracker


class FakeElement:
    def __init__(self, *, text: str = "", href: str | None = None, timestamp: str | None = None):
        self.text = text
        self.href = href
        self.timestamp = timestamp

    def find_element(self, by, selector):
        if by == By.XPATH and selector == "./ancestor::a":
            return FakeElement(href=self.href)
        raise NoSuchElementException(selector)

    def get_attribute(self, name):
        if name == "href":
            return self.href
        if name == "datetime":
            return self.timestamp
        return None


class TimestampArticle:
    def __init__(
        self,
        timestamp: str | None,
        text: str = "ordinary archival post",
        context: str | None = None,
        item_id: str = "123",
    ):
        self.timestamp = timestamp
        self.text = text
        self.context = context
        self.href = f"https://x.com/example/status/{item_id}"

    def find_element(self, by, selector):
        if by == By.CSS_SELECTOR and selector == '[data-testid="socialContext"]':
            if self.context is None:
                raise NoSuchElementException(selector)
            return FakeElement(text=self.context)
        if by == By.TAG_NAME and selector == "time":
            return FakeElement(text="Jul 20", href=self.href, timestamp=self.timestamp)
        if by == By.XPATH and selector == './/*[@data-testid="tweetText"]':
            return FakeElement(text=self.text)
        if by == By.CSS_SELECTOR and selector == '[data-testid="tweet-text-show-more-link"]':
            raise NoSuchElementException(selector)
        raise NoSuchElementException(selector)

    def find_elements(self, _by, _selector):
        return []


def test_old_pinned_post_does_not_stop_newer_posts_below_it():
    start = datetime(2026, 7, 10, tzinfo=timezone.utc)
    tracker = DateRangeStopTracker(start, consecutive_old_required=3)

    sequence = [
        (datetime(2020, 1, 1, tzinfo=timezone.utc), True),
        (datetime(2026, 7, 20, tzinfo=timezone.utc), False),
        (datetime(2026, 7, 15, tzinfo=timezone.utc), False),
        (datetime(2026, 7, 9, tzinfo=timezone.utc), False),
        (datetime(2026, 7, 8, tzinfo=timezone.utc), False),
        (datetime(2026, 7, 7, tzinfo=timezone.utc), False),
    ]

    decisions = [tracker.observe(date, is_pinned) for date, is_pinned in sequence]

    assert decisions == [False, False, False, False, False, True]


def test_profile_date_scrape_processes_newer_posts_below_an_old_pin():
    articles = [
        TimestampArticle("2020-01-01T00:00:00Z", context="Pinned", item_id="pin"),
        TimestampArticle("2026-07-20T00:00:00Z", item_id="new-1"),
        TimestampArticle("2026-07-15T00:00:00Z", item_id="new-2"),
        TimestampArticle("2026-07-09T00:00:00Z", item_id="old-1"),
        TimestampArticle("2026-07-08T00:00:00Z", item_id="old-2"),
        TimestampArticle("2026-07-07T00:00:00Z", item_id="old-3"),
    ]
    scraper = XScraper()
    scraper.driver = TimelineDriver(articles)

    tweets = scraper.scrape_by_date(
        datetime(2026, 7, 10, tzinfo=timezone.utc),
        datetime(2026, 7, 21, tzinfo=timezone.utc),
    )

    assert [tweet.id for tweet in tweets] == ["new-1", "new-2"]


class TimelineDriver:
    def __init__(self, articles):
        self.articles = articles

    def find_elements(self, _by, _selector):
        return self.articles


def test_missing_x_timestamp_is_not_fabricated_and_records_a_warning():
    run_log = ScrapeRunLog(target="example")
    scraper = XScraper(run_log=run_log)

    tweet = scraper._parse_tweet_element(TimestampArticle(None))

    assert tweet is not None
    assert tweet.date is None
    assert tweet.date_str == "Date unavailable"
    assert run_log.events[-1].reason == "tweet_date_unavailable"


def test_parsed_tweet_timestamp_is_immediately_utc_aware():
    scraper = XScraper()

    tweet = scraper._parse_tweet_element(TimestampArticle("2026-07-20T23:30:00-07:00"))

    assert tweet.date == datetime(2026, 7, 21, 6, 30, tzinfo=timezone.utc)


def test_promotional_language_is_archived_by_default():
    scraper = XScraper()

    tweet = scraper._parse_tweet_element(
        TimestampArticle(
            "2026-07-20T10:00:00Z",
            text="Subscribe to my newsletter and find the link in bio",
        )
    )

    assert isinstance(tweet, Tweet)


def test_promotional_filter_is_explicit_opt_in():
    scraper = XScraper(exclude_promotional_posts=True)

    tweet = scraper._parse_tweet_element(
        TimestampArticle(
            "2026-07-20T10:00:00Z",
            text="Subscribe to my newsletter and find the link in bio",
        )
    )

    assert tweet is None
