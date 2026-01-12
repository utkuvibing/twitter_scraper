"""
X (Twitter) Scraper Configuration
"""

# URL Templates
X_BASE_URL = "https://x.com"
X_LOGIN_URL = "https://x.com/i/flow/login"
X_PROFILE_URL = "https://x.com/{username}"

# Selenium Settings
IMPLICIT_WAIT = 1  # Düşürüldü - explicit wait kullanılıyor
PAGE_LOAD_TIMEOUT = 30
SCROLL_PAUSE_MIN = 0.1   # Minimum saniye
SCROLL_PAUSE_MAX = 0.25  # Maximum saniye

# CSS Selectors (X'in mevcut DOM yapısı - 2024/2025)
SELECTORS = {
    # Login page
    "username_input": 'input[autocomplete="username"]',
    "password_input": 'input[name="password"]',
    "next_button": '[role="button"]:has-text("Next"), button[type="button"]',
    "login_button": '[data-testid="LoginForm_Login_Button"]',

    # Tweet elements
    "tweet_article": 'article[data-testid="tweet"]',
    "tweet_text": '[data-testid="tweetText"]',
    "tweet_time": 'time',
    "tweet_link": 'a[href*="/status/"]',

    # Media
    "tweet_image": '[data-testid="tweetPhoto"] img',
    "tweet_video": '[data-testid="videoPlayer"]',

    # Reply indicator (bunu içeren tweetler reply'dır)
    "reply_indicator": '[data-testid="socialContext"]',
    "replying_to_text": 'div[dir="ltr"]:has-text("Replying to")',
}

# XPath Selectors (bazı elementler için daha güvenilir)
XPATHS = {
    "username_input": '//input[@autocomplete="username"]',
    "next_button": '//button[contains(@class, "css-175oi2r")]//span[text()="Next"]/ancestor::button',
    "password_input": '//input[@name="password"]',
    "login_button": '//button[@data-testid="LoginForm_Login_Button"]',
    "tweet_article": '//article[@data-testid="tweet"]',
    "replying_to": './/span[contains(text(), "Replying to")]',
}

# Chrome Options
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

# User Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
