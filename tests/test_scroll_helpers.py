import unittest

from selenium.webdriver.common.by import By

from scraper import XScraper
from diagnostics import ScrapeRunLog


class FakeLink:
    def __init__(self, href):
        self.href = href

    def get_attribute(self, name):
        return self.href if name == "href" else None


class FakeTime:
    def __init__(self, href):
        self.href = href

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


class ScrollHelperTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
