"""
X (Twitter) Scraper - Selenium ile tweet toplama
Refactored for JSON stdio communication (no print/input).
All output goes through the emit callback as structured messages.
"""

import time
import random
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    X_LOGIN_URL,
    X_PROFILE_URL,
    X_BOOKMARKS_URL,
    IMPLICIT_WAIT,
    PAGE_LOAD_TIMEOUT,
    SCROLL_PAUSE_MIN,
    SCROLL_PAUSE_MAX,
    CHROME_OPTIONS,
    USER_AGENT,
    XPATHS,
)

from session_manager import SessionManager


SKIP_ALREADY_COLLECTED = "SKIP_ALREADY_COLLECTED"


@dataclass
class Tweet:
    """Tweet data structure with engagement metrics"""

    id: str
    text: str
    date: datetime
    date_str: str
    media_urls: List[str]
    tweet_url: str
    needs_full_text: bool = False
    has_article: bool = False
    # Engagement metrics
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return {
            "id": self.id,
            "text": self.text,
            "date": self.date.isoformat() if self.date else None,
            "date_str": self.date_str,
            "media_urls": self.media_urls,
            "tweet_url": self.tweet_url,
            "has_article": self.has_article,
            "needs_full_text": self.needs_full_text,
            "likes": self.likes,
            "retweets": self.retweets,
            "replies": self.replies,
            "views": self.views,
        }


class XScraper:
    """X (Twitter) Tweet Scraper - JSON stdio communication"""

    def __init__(
        self,
        headless: bool = False,
        emit: Callable = None,
        chrome_path: Optional[str] = None,
        scroll_pause_min: Optional[float] = None,
        scroll_pause_max: Optional[float] = None,
    ):
        self.driver = None
        self.headless = headless
        self.collected_tweet_ids = set()
        self.tweets_collected: List[Tweet] = []
        self.chrome_path = chrome_path
        self.scroll_pause_min = scroll_pause_min or SCROLL_PAUSE_MIN
        self.scroll_pause_max = scroll_pause_max or SCROLL_PAUSE_MAX
        self.target_username = None  # Set by navigate_to_profile

        # State management
        self._paused = False
        self._cancelled = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially

        # Message emitter - sends structured JSON messages
        self._emit = emit or self._default_emit

        # Session manager
        self.session_manager = SessionManager(emit=self._emit)

    def _default_emit(self, msg_type: str, **kwargs):
        """Default emit does nothing (silent mode for testing)"""
        pass

    def _check_pause_cancel(self):
        """Check if paused or cancelled. Blocks while paused."""
        if self._cancelled:
            raise KeyboardInterrupt("Scrape cancelled by user")
        self._pause_event.wait()  # Blocks if paused

    def pause(self):
        """Pause the scraping operation"""
        self._paused = True
        self._pause_event.clear()
        self._emit("status", status="paused", collected=len(self.tweets_collected))

    def resume(self):
        """Resume the scraping operation"""
        self._paused = False
        self._pause_event.set()
        self._emit("status", status="running", collected=len(self.tweets_collected))

    def cancel(self):
        """Cancel the scraping operation"""
        self._cancelled = True
        self._pause_event.set()  # Unblock if paused
        self._emit("status", status="cancelled", collected=len(self.tweets_collected))

    def _setup_driver(self):
        """Configure and start Chrome WebDriver"""
        chrome_options = Options()

        for option in CHROME_OPTIONS:
            chrome_options.add_argument(option)

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument(f"user-agent={USER_AGENT}")

        # Hide automation detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        if self.chrome_path:
            chrome_options.binary_location = self.chrome_path

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Hide automation flag
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
            },
        )

        self.driver.implicitly_wait(IMPLICIT_WAIT)
        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    def start(self):
        """Start the driver"""
        if not self.driver:
            self._setup_driver()

    def stop(self):
        """Stop the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def login(self, username: str, password: str) -> bool:
        """
        Login to X with username and password.

        Args:
            username: X username or email
            password: Password

        Returns:
            True if successful
        """
        try:
            self._emit("log", level="info", message="Logging in to X...")
            self.driver.get(X_LOGIN_URL)

            wait = WebDriverWait(self.driver, 20)
            username_input = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATHS["username_input"]))
            )
            username_input.clear()
            self._human_type(username_input, username)

            # Click Next button
            next_buttons = self.driver.find_elements(
                By.XPATH, "//button[@role='button']"
            )
            for btn in next_buttons:
                try:
                    if "Next" in btn.text or "İleri" in btn.text:
                        btn.click()
                        break
                except:
                    continue
            else:
                username_input.send_keys(Keys.RETURN)

            # Additional verification may be required
            try:
                verification_input = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//input[@data-testid="ocfEnterTextTextInput"]')
                    )
                )
                # Emit that verification is needed - the frontend will handle it
                self._emit(
                    "login_waiting",
                    message="Additional verification required. Please complete in the browser.",
                )
                # Wait for verification (up to 60 seconds)
                WebDriverWait(self.driver, 60).until(
                    lambda d: d.find_elements(By.XPATH, XPATHS["password_input"])
                )
            except TimeoutException:
                pass

            # Password
            password_input = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATHS["password_input"]))
            )
            password_input.clear()
            self._human_type(password_input, password)

            # Click Login button
            try:
                login_btn = self.driver.find_element(By.XPATH, XPATHS["login_button"])
                login_btn.click()
            except:
                password_input.send_keys(Keys.RETURN)

            # Wait for login to complete
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: "home" in d.current_url.lower()
                    or (
                        "x.com" in d.current_url
                        and "login" not in d.current_url
                        and "flow" not in d.current_url
                    )
                )
                self.session_manager.save_cookies(self.driver)
                self._emit("login_status", success=True, message="Login successful")
                return True
            except TimeoutException:
                self._emit(
                    "login_status",
                    success=True,
                    message="Login check passed, continuing...",
                )
                return True

        except Exception as e:
            self._emit("login_status", success=False, message=f"Login error: {e}")
            return False

    def manual_login(self) -> bool:
        """
        Manual login - opens browser for user to login themselves.
        Emits login_waiting and waits for login_confirm command.

        Returns:
            True if successful
        """
        try:
            self._emit(
                "login_waiting",
                message="Browser opened. Please login to your X account.",
            )
            self.driver.get(X_LOGIN_URL)

            # Wait for login (poll every 2 seconds for up to 5 minutes)
            for _ in range(150):
                time.sleep(2)
                try:
                    current_url = self.driver.current_url.lower()
                    if "home" in current_url or (
                        "x.com" in current_url
                        and "login" not in current_url
                        and "flow" not in current_url
                    ):
                        self.session_manager.save_cookies(self.driver)
                        self._emit(
                            "login_status", success=True, message="Login successful"
                        )
                        return True
                except:
                    continue

            self._emit("login_status", success=False, message="Login timed out")
            return False

        except Exception as e:
            self._emit(
                "login_status", success=False, message=f"Manual login error: {e}"
            )
            return False

    def try_restore_session(self) -> bool:
        """Try to restore session from saved cookies"""
        return self.session_manager.load_cookies(self.driver)

    def _human_type(self, element, text: str):
        """Fast but human-like typing"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.05))

    def navigate_to_profile(self, target_username: str) -> bool:
        """Navigate to target profile"""
        try:
            self.target_username = target_username.lower().strip().lstrip("@")
            url = X_PROFILE_URL.format(username=target_username)
            self._emit("log", level="info", message=f"Navigating to profile: {url}")
            self.driver.get(url)

            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//article[@data-testid="tweet"]')
                )
            )

            # Wait for X to fully render the timeline
            time.sleep(2)
            articles = self.driver.find_elements(
                By.XPATH, '//article[@data-testid="tweet"]'
            )
            self._emit(
                "log",
                level="info",
                message=f"Profile loaded with {len(articles)} initial articles",
            )

            # If very few articles, wait longer for X to finish loading
            if len(articles) < 5:
                self._emit(
                    "log",
                    level="info",
                    message="Few articles detected, waiting for more to load...",
                )
                time.sleep(3)
                articles = self.driver.find_elements(
                    By.XPATH, '//article[@data-testid="tweet"]'
                )
                self._emit(
                    "log",
                    level="info",
                    message=f"After extra wait: {len(articles)} articles",
                )

            return True

        except TimeoutException:
            self._emit(
                "error", message="Profile could not be loaded or no tweets found"
            )
            return False
        except Exception as e:
            self._emit("error", message=f"Profile navigation error: {e}")
            return False

    def navigate_to_bookmarks(self) -> bool:
        """Navigate to bookmarks page"""
        try:
            self._emit(
                "log",
                level="info",
                message=f"Navigating to bookmarks: {X_BOOKMARKS_URL}",
            )
            self.driver.get(X_BOOKMARKS_URL)

            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//article[@data-testid="tweet"]')
                )
            )

            # Wait for X to fully render
            time.sleep(2)
            articles = self.driver.find_elements(
                By.XPATH, '//article[@data-testid="tweet"]'
            )
            self._emit(
                "log",
                level="info",
                message=f"Bookmarks page loaded with {len(articles)} initial articles",
            )
            return True

        except TimeoutException:
            self._emit(
                "error", message="Bookmarks could not be loaded or no bookmarks found"
            )
            return False
        except Exception as e:
            self._emit("error", message=f"Bookmarks navigation error: {e}")
            return False

    def _parse_engagement_metrics(self, article) -> dict:
        """Extract engagement metrics from a tweet article element"""
        metrics = {"likes": 0, "retweets": 0, "replies": 0, "views": 0}

        try:
            # Reply count
            try:
                reply_btn = article.find_element(
                    By.CSS_SELECTOR, '[data-testid="reply"]'
                )
                reply_text = reply_btn.get_attribute("aria-label") or ""
                metrics["replies"] = self._parse_metric_text(reply_text)
            except NoSuchElementException:
                pass

            # Retweet count
            try:
                retweet_btn = article.find_element(
                    By.CSS_SELECTOR, '[data-testid="retweet"]'
                )
                retweet_text = retweet_btn.get_attribute("aria-label") or ""
                metrics["retweets"] = self._parse_metric_text(retweet_text)
            except NoSuchElementException:
                pass

            # Like count
            try:
                like_btn = article.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
                like_text = like_btn.get_attribute("aria-label") or ""
                metrics["likes"] = self._parse_metric_text(like_text)
            except NoSuchElementException:
                pass

            # Views - from aria-label of analytics link or the view count display
            try:
                # Try the "views" text in the article group
                analytics_links = article.find_elements(
                    By.XPATH, './/a[contains(@href, "/analytics")]'
                )
                for link in analytics_links:
                    aria = link.get_attribute("aria-label") or ""
                    views = self._parse_metric_text(aria)
                    if views > 0:
                        metrics["views"] = views
                        break
            except:
                pass

        except Exception:
            pass

        return metrics

    def _parse_metric_text(self, text: str) -> int:
        """Parse metric count from aria-label text like '5 replies' or '1,234 likes'"""
        if not text:
            return 0
        try:
            # Extract numbers from text like "5 replies", "1,234 Likes", "12.5K views"
            import re

            # Find the first number pattern
            match = re.search(r"([\d,]+\.?\d*)\s*([KMB]?)", text, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(",", "")
                multiplier_char = match.group(2).upper()
                num = float(num_str)
                multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
                if multiplier_char in multipliers:
                    num *= multipliers[multiplier_char]
                return int(num)
        except (ValueError, AttributeError):
            pass
        return 0

    def _parse_tweet_element(self, article) -> Any:
        """
        Extract data from a tweet DOM element.

        Returns:
            Tweet object, None (skip), or SKIP_ALREADY_COLLECTED
        """
        try:
            # Retweet / Reply check via socialContext
            try:
                social_context = article.find_element(
                    By.CSS_SELECTOR, '[data-testid="socialContext"]'
                )
                context_text = social_context.text.lower()
                if "replying" in context_text:
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[FILTER] Skipping reply (socialContext: {context_text[:50]})",
                    )
                    return None
                if "reposted" in context_text or "retweeted" in context_text:
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[FILTER] Skipping retweet (socialContext: {context_text[:50]})",
                    )
                    return None
            except NoSuchElementException:
                pass

            # Tweet ID from URL
            tweet_id = None
            tweet_url = ""
            try:
                time_element = article.find_element(By.TAG_NAME, "time")
                parent_link = time_element.find_element(By.XPATH, "./ancestor::a")
                tweet_url = parent_link.get_attribute("href")
                if "/status/" in tweet_url:
                    tweet_id = (
                        tweet_url.split("/status/")[-1].split("?")[0].split("/")[0]
                    )
            except:
                links = article.find_elements(
                    By.XPATH, './/a[contains(@href, "/status/")]'
                )
                for link in links:
                    href = link.get_attribute("href")
                    if "/status/" in href:
                        tweet_url = href
                        tweet_id = (
                            href.split("/status/")[-1].split("?")[0].split("/")[0]
                        )
                        break

            if not tweet_id:
                self._emit(
                    "log",
                    level="debug",
                    message="[FILTER] Skipping article: no tweet ID found",
                )
                return None

            # Check if tweet belongs to target user (skip retweets/others' tweets)
            if self.target_username and tweet_url and "/status/" in tweet_url:
                try:
                    url_lower = tweet_url.lower()
                    # Extract username from tweet URL: https://x.com/USERNAME/status/...
                    before_status = url_lower.split("/status/")[0]
                    url_parts = before_status.rstrip("/").split("/")
                    tweet_author = url_parts[-1] if url_parts else None
                    if tweet_author and tweet_author != self.target_username:
                        self._emit(
                            "log",
                            level="debug",
                            message=f"[FILTER] Skipping other user's tweet (@{tweet_author}, expected @{self.target_username})",
                        )
                        return None
                except Exception:
                    pass  # If URL parsing fails, don't filter

            # Already collected check
            if tweet_id in self.collected_tweet_ids:
                return SKIP_ALREADY_COLLECTED

            # Tweet text
            text = ""
            try:
                text_element = article.find_element(
                    By.XPATH, './/*[@data-testid="tweetText"]'
                )
                text = text_element.text
            except NoSuchElementException:
                pass

            # "Show more" check
            has_show_more = False
            try:
                article.find_element(
                    By.CSS_SELECTOR, '[data-testid="tweet-text-show-more-link"]'
                )
                has_show_more = True
            except NoSuchElementException:
                pass

            if not has_show_more:
                try:
                    show_more_links = article.find_elements(
                        By.XPATH,
                        './/a[contains(text(), "Show more") or contains(text(), "Daha fazla")]',
                    )
                    if show_more_links:
                        has_show_more = True
                except:
                    pass

            if not has_show_more and text:
                if len(text) >= 270 and text.rstrip().endswith("…"):
                    has_show_more = True

            # Article check
            has_article = False
            try:
                article_labels = article.find_elements(
                    By.XPATH,
                    './/*[contains(text(), "Article") or contains(text(), "article")]',
                )
                if article_labels:
                    has_article = True

                if not has_article:
                    cards = article.find_elements(
                        By.CSS_SELECTOR, '[data-testid="card.wrapper"]'
                    )
                    for card in cards:
                        headings = card.find_elements(
                            By.XPATH, ".//span[string-length(text()) > 30]"
                        )
                        if headings:
                            has_article = True
                            break
            except:
                pass

            # Promo tweet filter - only skip if multiple promo signals found
            if text:
                text_lower = text.lower()
                promo_patterns = [
                    "link in bio",
                    "join my telegram",
                    "free prompts",
                    "join my newsletter",
                    "subscribe to my",
                    "t.me/",
                ]
                promo_hits = [p for p in promo_patterns if p in text_lower]
                if promo_hits:
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[FILTER] Skipping promo tweet (matched: {promo_hits}): {text[:60]}...",
                    )
                    return None

            # Date
            date = None
            date_str = ""
            try:
                time_elem = article.find_element(By.TAG_NAME, "time")
                datetime_attr = time_elem.get_attribute("datetime")
                date_str = time_elem.text
                if datetime_attr:
                    date = datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
            except:
                date = datetime.now()
                date_str = "Date unavailable"

            # Media URLs
            media_urls = []
            try:
                images = article.find_elements(
                    By.XPATH, './/*[@data-testid="tweetPhoto"]//img'
                )
                for img in images:
                    src = img.get_attribute("src")
                    if src and "pbs.twimg.com/media" in src:
                        media_urls.append(src)

                videos = article.find_elements(
                    By.XPATH, './/*[@data-testid="videoPlayer"]'
                )
                if videos:
                    media_urls.append("[Video content]")

                gifs = article.find_elements(By.XPATH, ".//video")
                for gif in gifs:
                    poster = gif.get_attribute("poster")
                    if poster:
                        media_urls.append(poster)
            except:
                pass

            # Engagement metrics
            metrics = self._parse_engagement_metrics(article)

            self.collected_tweet_ids.add(tweet_id)

            return Tweet(
                id=tweet_id,
                text=text,
                date=date,
                date_str=date_str,
                media_urls=media_urls,
                tweet_url=tweet_url,
                needs_full_text=has_show_more,
                has_article=has_article,
                likes=metrics["likes"],
                retweets=metrics["retweets"],
                replies=metrics["replies"],
                views=metrics["views"],
            )

        except StaleElementReferenceException:
            self._emit(
                "log",
                level="debug",
                message="[FILTER] Skipping article: stale element (DOM changed)",
            )
            return None
        except Exception as e:
            self._emit(
                "log",
                level="debug",
                message=f"[FILTER] Skipping article: parse error: {str(e)[:80]}",
            )
            return None

    def _close_extra_tabs(self, main_window: str):
        """Close all tabs except the main window and switch back"""
        try:
            for handle in self.driver.window_handles:
                if handle != main_window:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
            self.driver.switch_to.window(main_window)
        except:
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass

    def _get_full_tweet_text(self, tweet_url: str) -> str:
        """Open tweet in new tab and get full text"""
        text = ""
        main_window = self.driver.current_window_handle
        start_time = time.time()
        max_time = 8  # Max 8 seconds per tweet

        self._emit(
            "log", level="info", message=f"SHOW MORE: Opening tab for {tweet_url}"
        )

        # Set short page load timeout for tab operations
        try:
            self.driver.set_page_load_timeout(10)
        except Exception as e:
            self._emit(
                "log", level="warning", message=f"SHOW MORE: Could not set timeout: {e}"
            )

        try:
            self._emit("log", level="info", message="SHOW MORE: Opening new tab...")
            self.driver.execute_script(f"window.open('{tweet_url}', '_blank');")
            self._emit(
                "log", level="info", message="SHOW MORE: Switching to new tab..."
            )
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self._emit(
                "log", level="info", message="SHOW MORE: Waiting for page load..."
            )
            time.sleep(0.5)  # Reduced from 1

            self._emit(
                "log", level="info", message="SHOW MORE: Looking for tweet text..."
            )
            wait = WebDriverWait(self.driver, 5)
            try:
                text_element = wait.until(
                    EC.visibility_of_element_located(
                        (
                            By.XPATH,
                            '//article[@data-testid="tweet"]//div[@data-testid="tweetText"]',
                        )
                    )
                )
                time.sleep(0.2)  # Reduced from 0.3
                text = text_element.text
                self._emit(
                    "log",
                    level="info",
                    message=f"SHOW MORE: Got text, length: {len(text)}",
                )
            except TimeoutException:
                self._emit(
                    "log",
                    level="warning",
                    message="SHOW MORE: Timeout waiting for text, trying fallback...",
                )
                try:
                    text_elements = self.driver.find_elements(
                        By.XPATH, '//*[@data-testid="tweetText"]'
                    )
                    if text_elements:
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", text_elements[0]
                        )
                        time.sleep(0.3)  # Reduced from 0.5
                        text = text_elements[0].text
                        self._emit(
                            "log",
                            level="info",
                            message=f"SHOW MORE: Fallback got text, length: {len(text)}",
                        )
                    else:
                        self._emit(
                            "log",
                            level="warning",
                            message="SHOW MORE: No text elements found",
                        )
                except Exception as e2:
                    self._emit(
                        "log",
                        level="error",
                        message=f"SHOW MORE: Fallback failed: {e2}",
                    )

        except Exception as e:
            self._emit("log", level="error", message=f"SHOW MORE ERROR: {str(e)[:100]}")
        finally:
            self._emit(
                "log", level="info", message="SHOW MORE: Closing tab and returning..."
            )
            self._close_extra_tabs(main_window)
            # Restore default page load timeout
            try:
                self.driver.set_page_load_timeout(30)
            except:
                pass

        # Check if we exceeded max time
        elapsed = time.time() - start_time
        if elapsed > max_time:
            self._emit(
                "log",
                level="warning",
                message=f"SHOW MORE: Fetch took {elapsed:.1f}s (max {max_time}s)",
            )

        return text

    def _get_article_content(self, tweet_url: str) -> str:
        """Extract article content"""
        content_parts = []
        main_window = self.driver.current_window_handle
        start_time = time.time()
        max_time = 15  # Max 15 seconds per article

        self._emit("log", level="info", message=f"ARTICLE: Opening tab for {tweet_url}")

        # Set page load timeout for tab operations
        try:
            self.driver.set_page_load_timeout(15)
        except Exception as e:
            self._emit(
                "log", level="warning", message=f"ARTICLE: Could not set timeout: {e}"
            )

        try:
            self._emit("log", level="info", message="ARTICLE: Opening new tab...")
            self.driver.execute_script(f"window.open('{tweet_url}', '_blank');")
            self._emit("log", level="info", message="ARTICLE: Switching to new tab...")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self._emit("log", level="info", message="ARTICLE: Waiting for page load...")
            time.sleep(1)  # Reduced from 2

            # Scroll through article (max 5 iterations instead of 10)
            self._emit(
                "log", level="info", message="ARTICLE: Scrolling to load content..."
            )
            last_height = 0
            scroll_count = 0
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(0.2)  # Reduced from 0.3
                new_height = self.driver.execute_script(
                    "return document.documentElement.scrollHeight"
                )
                scroll_count += 1
                if new_height == last_height:
                    self._emit(
                        "log",
                        level="info",
                        message=f"ARTICLE: Reached end after {scroll_count} scrolls",
                    )
                    break
                last_height = new_height

            self._emit(
                "log",
                level="info",
                message=f"ARTICLE: Scrolled {scroll_count} times, extracting content...",
            )
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)  # Reduced from 0.5 (wait for content to settle)

            page_text = self.driver.execute_script("return document.body.innerText;")
            self._emit(
                "log",
                level="info",
                message=f"ARTICLE: Got page text, length: {len(page_text)} chars",
            )
            lines = page_text.split("\n")

            skip_patterns = [
                "home",
                "explore",
                "notifications",
                "messages",
                "grok",
                "premium",
                "profile",
                "more",
                "post",
                "subscribe",
                "follow",
                "following",
                "followers",
                "likes",
                "bookmark",
                "share",
                "reply",
                "repost",
                "quote",
                "view",
                "show",
                "hide",
                "keyboard shortcuts",
                "article",
                "conversation",
                "relevant people",
                "terms of service",
                "privacy policy",
                "© 2",
                "log out",
                "settings",
                "trending",
                "reposted",
                "liked",
                "joined",
                "posts",
                "replies",
                "media",
            ]

            collecting = False

            for line in lines:
                line = line.strip()
                if not line or len(line) < 40:
                    if " – " in line:
                        content_parts.append(f"\n## {line}\n")
                        collecting = True
                    continue

                line_lower = line.lower()
                if any(skip in line_lower for skip in skip_patterns):
                    continue
                if line.startswith("@"):
                    continue

                if len(line) > 60:
                    collecting = True
                    if line not in content_parts:
                        content_parts.append(line)

            result = "\n\n".join(content_parts)
            self._emit(
                "log",
                level="info",
                message=f"Article: {len(result)} characters extracted",
            )

            # Check if we exceeded max time
            elapsed = time.time() - start_time
            if elapsed > max_time:
                self._emit(
                    "log",
                    level="warning",
                    message=f"Article fetch took {elapsed:.1f}s (max {max_time}s)",
                )

            return result

        except Exception as e:
            error_msg = str(e)
            self._emit(
                "log", level="error", message=f"ARTICLE ERROR: {error_msg[:100]}"
            )
            import traceback

            self._emit(
                "log",
                level="debug",
                message=f"ARTICLE TRACEBACK: {traceback.format_exc()[:200]}",
            )
            return ""
        finally:
            self._emit(
                "log",
                level="info",
                message="ARTICLE: Closing tab and returning to profile...",
            )
            self._close_extra_tabs(main_window)
            # Restore default page load timeout
            try:
                self.driver.set_page_load_timeout(30)
            except:
                pass

    def _scroll_recovery(self):
        """Recovery when scroll gets stuck: scroll to top, wait, then gradually scroll down"""
        try:
            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Gradually scroll down to trigger X's lazy loading
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(0.8)

            # Final wait for content to load
            time.sleep(2)

            articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
            self._emit(
                "log",
                level="info",
                message=f"Recovery complete: {len(articles)} articles in DOM",
            )
        except Exception as e:
            self._emit(
                "log",
                level="warning",
                message=f"Recovery scroll error: {str(e)[:80]}",
            )

    def _scroll_down(self):
        """Scroll page down and wait for new content"""
        import time as time_module

        self._emit("log", level="debug", message="[DEBUG] Starting scroll...")

        # Track scroll position and article IDs instead of just count
        old_scroll_pos = 0
        old_count = 0
        old_ids = set()
        try:
            old_scroll_pos = self.driver.execute_script("return window.pageYOffset;")
            old_articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
            old_count = len(old_articles)
            # Track IDs of currently visible articles to detect replacement
            for art in old_articles:
                try:
                    time_el = art.find_element(By.TAG_NAME, "time")
                    link = time_el.find_element(By.XPATH, "./ancestor::a")
                    href = link.get_attribute("href")
                    if href and "/status/" in href:
                        sid = href.split("/status/")[-1].split("?")[0].split("/")[0]
                        if sid:
                            old_ids.add(sid)
                except:
                    pass
        except Exception as e:
            self._emit(
                "log", level="warning", message=f"[DEBUG] Error finding articles: {e}"
            )

        self._emit(
            "log",
            level="debug",
            message=f"[DEBUG] Found {old_count} tweets before scroll (pos: {old_scroll_pos})",
        )

        # Multi-strategy scroll to trigger X's lazy loading
        try:
            articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
            if articles:
                # Strategy 1: Scroll last article into view + extra distance
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(false);", articles[-1]
                )
                time_module.sleep(0.2)
                # Scroll further past to trigger loading zone
                self.driver.execute_script("window.scrollBy(0, 1200);")
            else:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
        except Exception as e:
            self._emit("log", level="warning", message=f"[DEBUG] Scroll error: {e}")
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

        time_module.sleep(random.uniform(self.scroll_pause_min, self.scroll_pause_max))

        # Check for new content: both count increase AND new tweet IDs
        scroll_timeout = 5
        start_time = time_module.time()
        found_new = False

        for i in range(10):
            if time_module.time() - start_time > scroll_timeout:
                self._emit(
                    "log", level="debug", message="[DEBUG] Scroll timeout reached"
                )
                break

            try:
                new_articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_count = len(new_articles)

                # Check if count increased
                if new_count > old_count:
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[DEBUG] New tweets loaded: {old_count} -> {new_count}",
                    )
                    found_new = True
                    break

                # Also check if articles were replaced (same count but different IDs)
                new_ids = set()
                for art in new_articles:
                    try:
                        time_el = art.find_element(By.TAG_NAME, "time")
                        link = time_el.find_element(By.XPATH, "./ancestor::a")
                        href = link.get_attribute("href")
                        if href and "/status/" in href:
                            sid = href.split("/status/")[-1].split("?")[0].split("/")[0]
                            if sid:
                                new_ids.add(sid)
                    except:
                        pass

                unseen_ids = new_ids - old_ids - self.collected_tweet_ids
                if unseen_ids:
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[DEBUG] Found {len(unseen_ids)} new tweet IDs after scroll",
                    )
                    found_new = True
                    break

            except Exception as e:
                self._emit("log", level="debug", message=f"[DEBUG] Find error: {e}")
                break

            time_module.sleep(0.3)

        if not found_new:
            self._emit(
                "log", level="debug", message="[DEBUG] No new tweets after 10 attempts"
            )
            # Try a more aggressive scroll as fallback
            try:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time_module.sleep(1.0)
            except:
                pass

    def _scroll_to_bottom(self):
        """Jump to page bottom"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(self.scroll_pause_min, self.scroll_pause_max))

    def scrape_by_count(self, count: int) -> List[Tweet]:
        """
        Collect a specific number of tweets.

        Args:
            count: Number of tweets to collect

        Returns:
            List of Tweet objects
        """
        self._emit("log", level="info", message=f"Collecting {count} tweets...")
        self.tweets_collected = []
        stale_scroll_count = 0
        max_stale_scrolls = 10
        last_height = 0
        same_height_count = 0
        no_new_tweets_count = 0
        max_no_new_tweets = 8

        try:
            loop_count = 0
            while len(self.tweets_collected) < count:
                loop_count += 1
                self._check_pause_cancel()

                collected_before = len(self.tweets_collected)

                self._emit(
                    "log",
                    level="debug",
                    message=f"[LOOP {loop_count}] Finding articles with XPath: {XPATHS['tweet_article']}",
                )

                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])

                self._emit(
                    "log",
                    level="debug",
                    message=f"[LOOP {loop_count}] Found {len(articles)} articles in DOM",
                )

                for article in articles:
                    if len(self.tweets_collected) >= count:
                        break
                    self._check_pause_cancel()

                    result = self._parse_tweet_element(article)
                    if result == SKIP_ALREADY_COLLECTED:
                        continue
                    if result is None:
                        continue
                    tweet = result
                    self.tweets_collected.append(tweet)

                    # Emit progress with tweet data
                    self._emit(
                        "progress",
                        collected=len(self.tweets_collected),
                        target=count,
                        tweet=tweet.to_dict(),
                        message=f"Tweet collected: {tweet.date_str}",
                    )

                # Track whether we found any NEW tweets this cycle
                collected_after = len(self.tweets_collected)
                new_tweets_this_cycle = collected_after - collected_before

                self._emit(
                    "log",
                    level="debug",
                    message=f"[LOOP {loop_count}] Cycle complete. Articles: {len(articles)}, New tweets: {new_tweets_this_cycle}, Total: {collected_after}",
                )

                if collected_after > collected_before:
                    no_new_tweets_count = 0
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[LOOP {loop_count}] Found {new_tweets_this_cycle} new tweets, reset counter",
                    )
                else:
                    no_new_tweets_count += 1
                    self._emit(
                        "log",
                        level="debug",
                        message=f"[LOOP {loop_count}] No new tweets. Counter: {no_new_tweets_count}/{max_no_new_tweets}",
                    )

                if no_new_tweets_count >= max_no_new_tweets:
                    self._emit(
                        "log",
                        level="info",
                        message=f"End of timeline reached. Found {collected_after} of {count} requested tweets.",
                    )
                    break

                # Recovery: if stuck for 3+ loops, scroll to top and back down
                if no_new_tweets_count == 3:
                    self._emit(
                        "log",
                        level="info",
                        message="Scroll stuck, trying recovery: scroll to top then back down...",
                    )
                    self._scroll_recovery()

                self._emit(
                    "log",
                    level="info",
                    message=f"Scrolling... ({collected_after} tweets collected so far)",
                )
                self._scroll_down()

                new_height = self.driver.execute_script(
                    "return document.body.scrollHeight"
                )
                if new_height == last_height:
                    same_height_count += 1
                else:
                    same_height_count = 0
                last_height = new_height

                if same_height_count >= 3:
                    stale_scroll_count += 1
                    if stale_scroll_count <= 3:
                        time.sleep(3)
                else:
                    stale_scroll_count = 0

                if stale_scroll_count >= max_stale_scrolls:
                    self._emit(
                        "log",
                        level="info",
                        message=f"End of timeline reached. Found {collected_after} of {count} requested tweets.",
                    )
                    break

        except KeyboardInterrupt:
            self._emit(
                "log",
                level="warning",
                message=f"Stopped! {len(self.tweets_collected)} tweets collected.",
            )
            raise

        # Process show more tweets
        self._process_show_more_tweets()

        self._emit(
            "log",
            level="info",
            message=f"Total {len(self.tweets_collected)} tweets collected.",
        )
        return self.tweets_collected

    def _process_show_more_tweets(self):
        """Get full text for truncated tweets and articles (after scrolling)"""
        show_more_tweets = [t for t in self.tweets_collected if t.needs_full_text]
        article_tweets = [t for t in self.tweets_collected if t.has_article]

        total = len(show_more_tweets) + len(article_tweets)
        if total == 0:
            return

        self._emit(
            "log",
            level="info",
            message=f"Fetching {total} full content items ({len(show_more_tweets)} show more, {len(article_tweets)} articles)...",
        )
        current = 0

        for tweet in show_more_tweets:
            current += 1
            self._check_pause_cancel()
            try:
                self._emit(
                    "log",
                    level="info",
                    message=f"[{current}/{total}] Fetching full text...",
                )
                full_text = self._get_full_tweet_text(tweet.tweet_url)
                if full_text:
                    tweet.text = full_text
                    tweet.needs_full_text = False
            except Exception as e:
                self._emit("log", level="warning", message=f"Error: {str(e)[:30]}")

        for tweet in article_tweets:
            current += 1
            self._check_pause_cancel()
            try:
                self._emit(
                    "log",
                    level="info",
                    message=f"[{current}/{total}] Fetching article content...",
                )
                article_content = self._get_article_content(tweet.tweet_url)
                if article_content:
                    if tweet.text:
                        tweet.text = (
                            tweet.text
                            + "\n\n--- ARTICLE CONTENT ---\n\n"
                            + article_content
                        )
                    else:
                        tweet.text = article_content
                    tweet.has_article = False
                else:
                    self._emit(
                        "log",
                        level="warning",
                        message="Article content could not be extracted",
                    )
            except Exception as e:
                self._emit("log", level="warning", message=f"Error: {str(e)[:50]}")

        self._emit("log", level="info", message="Full content fetching complete.")

    def scrape_by_date(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Tweet]:
        """
        Collect tweets within a date range.

        Args:
            start_date: Start date (oldest)
            end_date: End date (newest), None = today

        Returns:
            List of Tweet objects
        """
        if end_date is None:
            end_date = (
                datetime.now(start_date.tzinfo) if start_date.tzinfo else datetime.now()
            )

        self._emit(
            "log",
            level="info",
            message=f"Date range: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}",
        )
        self.tweets_collected = []
        no_new_tweets_count = 0
        max_no_new_tweets = 5
        reached_start_date = False

        try:
            while not reached_start_date:
                self._check_pause_cancel()

                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_tweets_found = False

                for article in articles:
                    self._check_pause_cancel()

                    result = self._parse_tweet_element(article)
                    if result == SKIP_ALREADY_COLLECTED or result is None:
                        continue
                    tweet = result
                    if tweet:
                        tweet_date = (
                            tweet.date.replace(tzinfo=None)
                            if tweet.date.tzinfo
                            else tweet.date
                        )
                        start_date_naive = (
                            start_date.replace(tzinfo=None)
                            if start_date.tzinfo
                            else start_date
                        )
                        end_date_naive = (
                            end_date.replace(tzinfo=None)
                            if end_date.tzinfo
                            else end_date
                        )

                        if tweet_date < start_date_naive:
                            reached_start_date = True
                            break

                        if start_date_naive <= tweet_date <= end_date_naive:
                            self.tweets_collected.append(tweet)
                            new_tweets_found = True
                            self._emit(
                                "progress",
                                collected=len(self.tweets_collected),
                                tweet=tweet.to_dict(),
                                message=f"Tweet: {tweet.date_str}",
                            )

                if new_tweets_found:
                    no_new_tweets_count = 0
                else:
                    no_new_tweets_count += 1

                if no_new_tweets_count >= max_no_new_tweets:
                    self._emit(
                        "log",
                        level="info",
                        message="No more tweets found or outside date range",
                    )
                    break

                if reached_start_date:
                    break

                self._scroll_down()

        except KeyboardInterrupt:
            self._emit(
                "log",
                level="warning",
                message=f"Stopped! {len(self.tweets_collected)} tweets collected.",
            )
            raise

        self._process_show_more_tweets()
        self._emit(
            "log",
            level="info",
            message=f"Total {len(self.tweets_collected)} tweets collected.",
        )
        return self.tweets_collected

    def scrape_last_n_days(self, days: int) -> List[Tweet]:
        """Collect tweets from last N days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.scrape_by_date(start_date, end_date)

    def scrape_bookmarks(self, count: int = None, get_all: bool = False) -> List[Tweet]:
        """
        Collect bookmarked tweets.

        Args:
            count: Number of bookmarks to collect (None for get_all)
            get_all: True to collect all bookmarks

        Returns:
            List of Tweet objects
        """
        if get_all:
            self._emit("log", level="info", message="Collecting all bookmarks...")
        else:
            self._emit("log", level="info", message=f"Collecting {count} bookmarks...")

        self.tweets_collected = []
        no_new_tweets_count = 0
        max_no_new_tweets = 10

        try:
            while True:
                self._check_pause_cancel()

                if not get_all and count and len(self.tweets_collected) >= count:
                    break

                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_tweets_found = False

                for article in articles:
                    if not get_all and count and len(self.tweets_collected) >= count:
                        break
                    self._check_pause_cancel()

                    result = self._parse_tweet_element(article)
                    if result == SKIP_ALREADY_COLLECTED or result is None:
                        continue
                    tweet = result
                    self.tweets_collected.append(tweet)
                    new_tweets_found = True

                    self._emit(
                        "progress",
                        collected=len(self.tweets_collected),
                        target=count,
                        tweet=tweet.to_dict(),
                        message=f"Bookmark collected: {tweet.date_str}",
                    )

                if new_tweets_found:
                    no_new_tweets_count = 0
                else:
                    no_new_tweets_count += 1

                if no_new_tweets_count >= max_no_new_tweets:
                    self._emit("log", level="info", message="No more bookmarks found")
                    break

                self._scroll_down()

        except KeyboardInterrupt:
            self._emit(
                "log",
                level="warning",
                message=f"Stopped! {len(self.tweets_collected)} bookmarks collected.",
            )
            raise

        self._process_show_more_tweets()
        self._emit(
            "log",
            level="info",
            message=f"Total {len(self.tweets_collected)} bookmarks collected.",
        )
        return self.tweets_collected
