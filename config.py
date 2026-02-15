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

CHROME_OPTIONS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
    "--start-maximized",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
