import unittest

from selenium.webdriver.common.by import By

from scraper import XScraper


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


if __name__ == "__main__":
    unittest.main()
