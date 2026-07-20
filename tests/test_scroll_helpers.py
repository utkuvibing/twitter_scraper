import unittest
from unittest.mock import patch

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from scraper import XScraper, SKIP_ALREADY_COLLECTED
from diagnostics import ScrapeRunLog


class FakeLink:
    def __init__(self, href):
        self.href = href

    def get_attribute(self, name):
        return self.href if name == "href" else None


class FakeTime:
    def __init__(self, href, timestamp="2026-07-20T10:00:00Z"):
        self.href = href
        self.timestamp = timestamp

    @property
    def text(self):
        return "Jul 20"

    def get_attribute(self, name):
        return self.timestamp if name == "datetime" else None

    def find_element(self, by, selector):
        if by == By.XPATH and selector == "./ancestor::a":
            return FakeLink(self.href)
        raise LookupError(selector)


class FakeArticle:
    def __init__(self, href):
        self.href = href

    def find_element(self, by, selector):
        if by == By.TAG_NAME and selector == "time":
            return FakeTime(self.href)
        raise LookupError(selector)


class FakeTextElement:
    def __init__(self, text):
        self.text = text


class FakeTweetArticle:
    def __init__(self, href, text="", social_context=None, article_labels=None, cards=None):
        self.href = href
        self.text = text
        self.social_context = social_context
        self.article_labels = article_labels or []
        self.cards = cards or []

    def find_element(self, by, selector):
        if by == By.CSS_SELECTOR and selector == '[data-testid="socialContext"]':
            if self.social_context is None:
                raise NoSuchElementException(selector)
            return FakeTextElement(self.social_context)
        if by == By.TAG_NAME and selector == "time":
            return FakeTime(self.href)
        if by == By.XPATH and selector == './/*[@data-testid="tweetText"]':
            if not self.text:
                raise NoSuchElementException(selector)
            return FakeTextElement(self.text)
        if by == By.CSS_SELECTOR and selector == '[data-testid="tweet-text-show-more-link"]':
            raise NoSuchElementException(selector)
        raise NoSuchElementException(selector)

    def find_elements(self, by, selector):
        if by == By.XPATH and 'contains(@href, "/status/")' in selector:
            return [FakeLink(self.href)]
        if by == By.XPATH and "Show more" in selector:
            return []
        if by == By.XPATH and "tweetPhoto" in selector:
            return []
        if by == By.XPATH and selector == './/video':
            return []
        if by == By.CSS_SELECTOR and selector == '[data-testid="videoPlayer"]':
            return []
        if by == By.CSS_SELECTOR and selector == '[data-testid="card.wrapper"]':
            return self.cards
        if by == By.XPATH and "ancestor-or-self" in selector and "article" in selector:
            return self.article_labels
        return []


class FakeCard:
    def __init__(self, text="", headings=None):
        self.text = text
        self.headings = headings or []

    def find_elements(self, by, selector):
        if by == By.XPATH and "string-length" in selector:
            return self.headings
        return []


class ScrollHelperTests(unittest.TestCase):
    def test_successful_javascript_scroll_does_not_call_native_or_cdp_fallbacks(self):
        driver = ScrollDriver()
        scraper = XScraper(headless=True)
        scraper.driver = driver

        with patch(
            "scraper.ActionChains",
            side_effect=AssertionError("native scroll used"),
            create=True,
        ):
            scraper._perform_timeline_scroll(2)

        self.assertEqual(len(driver.scripts), 1)
        self.assertEqual(driver.cdp_calls, [])
        self.assertEqual(driver.find_calls, [])

    def test_get_article_ids_fast_extracts_status_ids(self):
        scraper = XScraper(headless=True)
        articles = [
            FakeArticle("https://x.com/user/status/111"),
            FakeArticle("https://x.com/user/status/222?ref=profile"),
            FakeArticle("https://x.com/user/status/111"),
            FakeArticle("https://x.com/user/with_replies"),
        ]

        self.assertEqual(scraper._get_article_ids_fast(articles), {"111", "222"})

    def test_get_article_ids_fast_ignores_bad_articles(self):
        scraper = XScraper(headless=True)

        self.assertEqual(scraper._get_article_ids_fast([object()]), set())

    def test_timeline_advanced_detects_new_uncollected_id(self):
        scraper = XScraper(headless=True)
        scraper.collected_tweet_ids = {"111"}

        before = {
            "article_ids": {"111"},
            "article_count": 1,
            "scroll_y": 100,
            "scroll_height": 1000,
        }
        after = {
            "article_ids": {"111", "222"},
            "article_count": 1,
            "scroll_y": 100,
            "scroll_height": 1000,
        }

        self.assertTrue(scraper._timeline_advanced(before, after))

    def test_timeline_advanced_detects_scroll_progress_without_new_id(self):
        scraper = XScraper(headless=True)

        before = {
            "article_ids": {"111"},
            "article_count": 1,
            "scroll_y": 100,
            "scroll_height": 1000,
        }
        after = {
            "article_ids": {"111"},
            "article_count": 1,
            "scroll_y": 500,
            "scroll_height": 1000,
        }

        self.assertTrue(scraper._timeline_advanced(before, after))

    def test_timeline_advanced_rejects_static_timeline(self):
        scraper = XScraper(headless=True)

        before = {
            "article_ids": {"111"},
            "article_count": 1,
            "scroll_y": 100,
            "scroll_height": 1000,
        }
        after = {
            "article_ids": {"111"},
            "article_count": 1,
            "scroll_y": 120,
            "scroll_height": 1000,
        }

        self.assertFalse(scraper._timeline_advanced(before, after))

    def test_partial_target_not_met_records_classified_warning(self):
        run_log = ScrapeRunLog(target="example", scrape_type="profile", mode="count")
        scraper = XScraper(headless=True, run_log=run_log)
        scraper.driver = None

        scraper._record_partial_target_not_met("Count", collected=6, target=20, no_progress_cycles=8)

        self.assertEqual(run_log.events[-1].reason, "partial_target_not_met")
        self.assertEqual(run_log.events[-1].details["collected"], 6)
        self.assertEqual(run_log.events[-1].details["missing"], 14)
        self.assertEqual(run_log.events[-1].details["no_progress_cycles"], 8)

    def test_parse_tweet_element_skips_reposts(self):
        scraper = XScraper(headless=True)
        article = FakeTweetArticle(
            "https://x.com/actuallyvetted/status/2054974310646006144",
            text="every founder we speak to is struggling...",
            social_context="Machina reposted",
        )

        self.assertIsNone(scraper._parse_tweet_element(article))
        self.assertNotIn("2054974310646006144", scraper.collected_tweet_ids)

    def test_article_word_inside_tweet_text_does_not_trigger_article_extraction(self):
        scraper = XScraper(headless=True)
        article = FakeTweetArticle(
            "https://x.com/EXM7777/status/2054946364740837580",
            text="writing an article on how i went from 0 to 100,000 followers in a year...",
        )

        tweet = scraper._parse_tweet_element(article)

        self.assertIsNotNone(tweet)
        self.assertNotEqual(tweet, SKIP_ALREADY_COLLECTED)
        self.assertFalse(tweet.has_article)
        self.assertEqual(tweet.text, "writing an article on how i went from 0 to 100,000 followers in a year...")

    def test_article_label_outside_tweet_text_still_triggers_article_extraction(self):
        scraper = XScraper(headless=True)
        article = FakeTweetArticle(
            "https://x.com/user/status/333",
            text="New longform post",
            article_labels=[FakeTextElement("Article")],
        )

        tweet = scraper._parse_tweet_element(article)

        self.assertTrue(tweet.has_article)


if __name__ == "__main__":
    unittest.main()


class ScrollDriver:
    def __init__(self):
        self.scripts = []
        self.cdp_calls = []
        self.find_calls = []

    def execute_script(self, script, *args):
        self.scripts.append((script, args))

    def execute_cdp_cmd(self, *args):
        self.cdp_calls.append(args)

    def find_element(self, *args):
        self.find_calls.append(args)
        return FakeTextElement("")
