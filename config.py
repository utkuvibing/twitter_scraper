"""
X (Twitter) Scraper Configuration
"""

# URL Templates
X_BASE_URL = "https://x.com"
X_LOGIN_URL = "https://x.com/i/flow/login"
X_PROFILE_URL = "https://x.com/{username}"
X_BOOKMARKS_URL = "https://x.com/i/bookmarks"

# Selenium Settings
IMPLICIT_WAIT = 1
PAGE_LOAD_TIMEOUT = 30
SCROLL_PAUSE_MIN = 1.0
SCROLL_PAUSE_MAX = 2.0

# CSS Selectors
SELECTORS = {
    "username_input": 'input[autocomplete="username"]',
    "password_input": 'input[name="password"]',
    "next_button": '[role="button"]:has-text("Next"), button[type="button"]',
    "login_button": '[data-testid="LoginForm_Login_Button"]',
    "tweet_article": 'article[data-testid="tweet"]',
    "tweet_text": '[data-testid="tweetText"]',
    "tweet_time": 'time',
    "tweet_link": 'a[href*="/status/"]',
    "tweet_image": '[data-testid="tweetPhoto"] img',
    "tweet_video": '[data-testid="videoPlayer"]',
    "reply_indicator": '[data-testid="socialContext"]',
    "replying_to_text": 'div[dir="ltr"]:has-text("Replying to")',
    "article_link": 'a[href*="/i/articles/"]',
    "article_card": '[data-testid="card.wrapper"]',
    "article_title": 'h1, [role="heading"][aria-level="1"]',
    "article_content": 'article p, [data-testid="tweetText"]',
}

XPATHS = {
    "username_input": '//input[@autocomplete="username"]',
    "next_button": '//button[contains(@class, "css-175oi2r")]//span[text()="Next"]/ancestor::button',
    "password_input": '//input[@name="password"]',
    "login_button": '//button[@data-testid="LoginForm_Login_Button"]',
    "tweet_article": '//article[@data-testid="tweet"]',
    "replying_to": './/span[contains(text(), "Replying to")]',
    "article_link": './/a[contains(@href, "/i/articles/")]',
}

CORE_SELECTOR_CHECKS = [
    {
        "name": "login_username_input",
        "stage": "login",
        "type": "xpath",
        "selector": XPATHS["username_input"],
        "required": False,
    },
    {
        "name": "login_password_input",
        "stage": "login",
        "type": "xpath",
        "selector": XPATHS["password_input"],
        "required": False,
    },
    {
        "name": "tweet_article",
        "stage": "timeline_loading",
        "type": "xpath",
        "selector": XPATHS["tweet_article"],
        "required": True,
    },
    {
        "name": "tweet_text",
        "stage": "tweet_parsing",
        "type": "css",
        "selector": SELECTORS["tweet_text"],
        "required": False,
    },
    {
        "name": "tweet_time",
        "stage": "tweet_parsing",
        "type": "css",
        "selector": SELECTORS["tweet_time"],
        "required": False,
    },
    {
        "name": "tweet_status_link",
        "stage": "tweet_parsing",
        "type": "css",
        "selector": SELECTORS["tweet_link"],
        "required": False,
    },
    {
        "name": "show_more_link",
        "stage": "full_text_extraction",
        "type": "css",
        "selector": '[data-testid="tweet-text-show-more-link"]',
        "required": False,
    },
    {
        "name": "article_link",
        "stage": "article_extraction",
        "type": "xpath",
        "selector": XPATHS["article_link"],
        "required": False,
    },
]

CHROME_OPTIONS = [
    "--window-size=1920,1080",
    "--start-maximized",
]
