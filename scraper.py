"""
X (Twitter) Scraper - Selenium ile tweet toplama
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchWindowException,
    StaleElementReferenceException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

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
from diagnostics import (
    ScrapeRunLog,
    add_diagnostics_to_log,
    record_event,
    run_selector_diagnostics,
)


SKIP_ALREADY_COLLECTED = "SKIP_ALREADY_COLLECTED"


@dataclass
class Tweet:
    """Tweet veri yapısı"""
    id: str
    text: str
    date: datetime
    date_str: str
    media_urls: List[str]
    tweet_url: str
    needs_full_text: bool = False  # Show more varsa True
    has_article: bool = False  # X Article varsa True


class XScraper:
    """X (Twitter) Tweet Scraper"""

    def __init__(self, headless: bool = False, run_log: Optional[ScrapeRunLog] = None):
        """
        Scraper'ı başlat

        Args:
            headless: True ise browser görünmeden çalışır
        """
        self.driver = None
        self.headless = headless
        self.collected_tweet_ids = set()
        self.run_log = run_log

    def _setup_driver(self):
        """Chrome WebDriver'ı yapılandır ve başlat"""
        chrome_options = Options()

        for option in CHROME_OPTIONS:
            chrome_options.add_argument(option)

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument(f"user-agent={USER_AGENT}")

        # Automation detection'ı gizle
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Automation flag'ini gizle
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
        """Driver'ı başlat"""
        if not self.driver:
            self._setup_driver()
            record_event(self.run_log, "browser_start", "info", "Chrome WebDriver started")

    def stop(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            record_event(self.run_log, "browser_stop", "info", "Chrome WebDriver stopped")

    def run_selector_diagnostics(self):
        """Run configured selector checks on the current browser page."""
        diagnostics = run_selector_diagnostics(self.driver)
        add_diagnostics_to_log(self.run_log, diagnostics)
        return diagnostics

    def login(self, username: str, password: str) -> bool:
        """
        X'e giriş yap

        Args:
            username: X kullanıcı adı veya email
            password: Şifre

        Returns:
            Başarılı ise True
        """
        try:
            print("X'e giriş yapılıyor...")
            record_event(self.run_log, "login", "info", "Automatic login started")
            self.driver.get(X_LOGIN_URL)

            # Username girişi (sayfa yüklenene kadar bekle)
            wait = WebDriverWait(self.driver, 20)
            username_input = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATHS["username_input"]))
            )
            username_input.clear()
            self._human_type(username_input, username)

            # Next butonuna tıkla
            next_buttons = self.driver.find_elements(By.XPATH, "//button[@role='button']")
            for btn in next_buttons:
                try:
                    if "Next" in btn.text or "İleri" in btn.text:
                        btn.click()
                        break
                except:
                    continue
            else:
                username_input.send_keys(Keys.RETURN)

            # Bazen ek doğrulama isteyebilir (telefon/email)
            try:
                verification_input = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, '//input[@data-testid="ocfEnterTextTextInput"]'))
                )
                print("Ek doğrulama gerekiyor. Lütfen telefon veya email girin:")
                verification_code = input("Doğrulama kodu/bilgisi: ")
                verification_input.clear()
                self._human_type(verification_input, verification_code)
                verification_input.send_keys(Keys.RETURN)
            except TimeoutException:
                pass

            # Password girişi
            password_input = wait.until(
                EC.presence_of_element_located((By.XPATH, XPATHS["password_input"]))
            )
            password_input.clear()
            self._human_type(password_input, password)

            # Login butonuna tıkla
            try:
                login_btn = self.driver.find_element(By.XPATH, XPATHS["login_button"])
                login_btn.click()
            except:
                password_input.send_keys(Keys.RETURN)

            # Giriş başarılı olana kadar bekle (max 10 saniye)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: "home" in d.current_url.lower() or
                              ("x.com" in d.current_url and "login" not in d.current_url and "flow" not in d.current_url)
                )
                print("Giriş başarılı!")
                record_event(self.run_log, "login", "info", "Automatic login completed")
                return True
            except TimeoutException:
                print("Giriş kontrol ediliyor...")
                record_event(
                    self.run_log,
                    "login",
                    "warning",
                    "Login success could not be confirmed by URL; continuing",
                )
                return True  # Devam etmeyi dene

        except Exception as e:
            print(f"Giriş hatası: {e}")
            record_event(
                self.run_log,
                "login",
                "error",
                f"Login failed: {e}",
                reason="login_failed",
            )
            return False

    def manual_login(self) -> bool:
        """
        Manuel giriş - Kullanıcı kendisi giriş yapar (Google, Apple vs. için)

        Returns:
            Başarılı ise True
        """
        try:
            record_event(self.run_log, "manual_login", "info", "Manual login started")
            print("\n" + "=" * 50)
            print("MANUEL GİRİŞ MODU")
            print("=" * 50)
            print("Browser açılacak. Lütfen X hesabınıza giriş yapın.")
            print("Google, Apple veya normal şifre ile giriş yapabilirsiniz.")
            print("Giriş yaptıktan sonra buraya dönüp ENTER'a basın.")
            print("=" * 50 + "\n")

            self.driver.get(X_LOGIN_URL)

            input(">>> Giriş yaptıktan sonra ENTER'a basın...")

            # Giriş kontrolü
            time.sleep(0.5)
            current_url = self.driver.current_url.lower()

            if "home" in current_url or "x.com" in current_url:
                if "login" not in current_url and "flow" not in current_url:
                    print("Giriş başarılı!")
                    record_event(self.run_log, "manual_login", "info", "Manual login confirmed")
                    return True

            print("Giriş yapılmış görünüyor, devam ediliyor...")
            record_event(
                self.run_log,
                "manual_login",
                "warning",
                "Manual login confirmation was ambiguous; continuing",
            )
            return True

        except Exception as e:
            print(f"Manuel giriş hatası: {e}")
            record_event(
                self.run_log,
                "manual_login",
                "error",
                f"Manual login failed: {e}",
                reason="manual_login_timeout",
            )
            return False

    def _human_type(self, element, text: str):
        """Hızlı ama insan benzeri yazma"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.05))

    def navigate_to_profile(self, target_username: str) -> bool:
        """
        Hedef profile git

        Args:
            target_username: Scrape edilecek hesabın kullanıcı adı (@olmadan)

        Returns:
            Başarılı ise True
        """
        try:
            url = X_PROFILE_URL.format(username=target_username)
            print(f"Profile gidiliyor: {url}")
            record_event(
                self.run_log,
                "profile_navigation",
                "info",
                f"Navigating to profile @{target_username}",
                url=url,
            )
            self.driver.get(url)

            # Profil yüklendi mi kontrol et (tweet görünene kadar bekle)
            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )
            print("Profil yüklendi!")
            diagnostics = self.run_selector_diagnostics()
            record_event(
                self.run_log,
                "timeline_loading",
                "info" if diagnostics.get("ok") else "warning",
                "Profile timeline selector diagnostics completed",
                missing_required=diagnostics.get("missing_required", []),
            )
            return True

        except TimeoutException:
            print("Profil yüklenemedi veya tweet bulunamadı.")
            record_event(
                self.run_log,
                "profile_navigation",
                "error",
                "Profile page did not expose tweet articles before timeout",
                reason="profile_navigation_failed",
                selector=XPATHS["tweet_article"],
            )
            return False
        except Exception as e:
            print(f"Profil navigasyon hatası: {e}")
            record_event(
                self.run_log,
                "profile_navigation",
                "error",
                f"Profile navigation error: {e}",
                reason="profile_navigation_failed",
            )
            return False

    def navigate_to_bookmarks(self) -> bool:
        """
        Bookmark sayfasına git

        Returns:
            Başarılı ise True
        """
        try:
            print(f"Bookmarks sayfasına gidiliyor: {X_BOOKMARKS_URL}")
            record_event(
                self.run_log,
                "bookmarks_navigation",
                "info",
                "Navigating to bookmarks",
                url=X_BOOKMARKS_URL,
            )
            self.driver.get(X_BOOKMARKS_URL)

            # Bookmark sayfası yüklendi mi kontrol et
            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )
            print("Bookmarks sayfası yüklendi!")
            diagnostics = self.run_selector_diagnostics()
            record_event(
                self.run_log,
                "timeline_loading",
                "info" if diagnostics.get("ok") else "warning",
                "Bookmarks timeline selector diagnostics completed",
                missing_required=diagnostics.get("missing_required", []),
            )
            return True

        except TimeoutException:
            print("Bookmarks yüklenemedi veya bookmark bulunamadı.")
            record_event(
                self.run_log,
                "bookmarks_navigation",
                "error",
                "Bookmarks page did not expose tweet articles before timeout",
                reason="bookmarks_navigation_failed",
                selector=XPATHS["tweet_article"],
            )
            return False
        except Exception as e:
            print(f"Bookmarks navigasyon hatası: {e}")
            record_event(
                self.run_log,
                "bookmarks_navigation",
                "error",
                f"Bookmarks navigation error: {e}",
                reason="bookmarks_navigation_failed",
            )
            return False

    def _parse_tweet_element(self, article) -> Optional[Tweet]:
        """
        Tweet elementinden veri çıkar

        Args:
            article: Tweet article elementi

        Returns:
            Tweet objesi veya None (reply ise)
        """
        try:
            # Pinned / Reply kontrolü
            try:
                social_context = article.find_element(By.CSS_SELECTOR, '[data-testid="socialContext"]')
                context_text = social_context.text.lower()
                if "replying" in context_text:
                    return None  # Reply, atla
                # "Pinned" / "Sabitlenmiş" ise normal tweet olarak devam et
            except NoSuchElementException:
                pass  # socialContext yok, normal tweet

            # Tweet ID'sini al (URL'den)
            tweet_id = None
            tweet_url = ""
            try:
                time_element = article.find_element(By.TAG_NAME, "time")
                parent_link = time_element.find_element(By.XPATH, "./ancestor::a")
                tweet_url = parent_link.get_attribute("href")
                if "/status/" in tweet_url:
                    tweet_id = tweet_url.split("/status/")[-1].split("?")[0].split("/")[0]
            except:
                # Alternatif yöntem
                links = article.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')
                for link in links:
                    href = link.get_attribute("href")
                    if "/status/" in href:
                        tweet_url = href
                        tweet_id = href.split("/status/")[-1].split("?")[0].split("/")[0]
                        break

            if not tweet_id:
                record_event(
                    self.run_log,
                    "tweet_parsing",
                    "warning",
                    "Tweet article skipped because no status URL/id was found",
                    reason="tweet_parse_failed",
                    selector='a[href*="/status/"]',
                )
                return None

            # Zaten toplandıysa atla (ama "yeni tweet yok" sayma)
            if tweet_id in self.collected_tweet_ids:
                return SKIP_ALREADY_COLLECTED

            # Tweet metnini al
            text = ""
            try:
                text_element = article.find_element(By.XPATH, './/*[@data-testid="tweetText"]')
                text = text_element.text
            except NoSuchElementException:
                pass

            # "Show more" kontrolü - birden fazla yöntem dene
            has_show_more = False
            try:
                article.find_element(By.CSS_SELECTOR, '[data-testid="tweet-text-show-more-link"]')
                has_show_more = True
            except NoSuchElementException:
                pass

            if not has_show_more:
                try:
                    # "Show more" / "Daha fazla göster" text'i olan link
                    show_more_links = article.find_elements(By.XPATH,
                        './/a[contains(text(), "Show more") or contains(text(), "Daha fazla")]')
                    if show_more_links:
                        has_show_more = True
                except:
                    pass

            if not has_show_more and text:
                # Metin "…" ile bitiyorsa ve 270+ karakter ise muhtemelen truncate
                if len(text) >= 270 and text.rstrip().endswith("…"):
                    has_show_more = True

            # Article kontrolü
            has_article = False
            try:
                # Yöntem 1: "Article" text'i ara (𝕏 Article etiketi)
                article_labels = article.find_elements(By.XPATH,
                    './/*[contains(text(), "Article") or contains(text(), "article")]')
                if article_labels:
                    has_article = True

                # Yöntem 2: Card içinde uzun başlık varsa article olabilir
                if not has_article:
                    cards = article.find_elements(By.CSS_SELECTOR, '[data-testid="card.wrapper"]')
                    for card in cards:
                        headings = card.find_elements(By.XPATH, './/span[string-length(text()) > 30]')
                        if headings:
                            has_article = True
                            break
            except:
                pass

            if has_article:
                print(f"      [ARTICLE] Article tespit edildi")

            # Promo/tanıtım tweetlerini atla
            if text:
                text_lower = text.lower()
                promo_patterns = [
                    "link in bio",
                    "telegram",
                    "newsletter",
                    "free prompts",
                    "join my",
                    "subscribe",
                ]
                if any(pattern in text_lower for pattern in promo_patterns):
                    return None  # Promo tweet, atla

            # Tarihi al
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
                date_str = "Tarih alınamadı"

            # Medya URL'lerini al
            media_urls = []
            try:
                # Resimler
                images = article.find_elements(
                    By.XPATH, './/*[@data-testid="tweetPhoto"]//img'
                )
                for img in images:
                    src = img.get_attribute("src")
                    if src and "pbs.twimg.com/media" in src:
                        media_urls.append(src)

                # Video thumbnail
                videos = article.find_elements(
                    By.XPATH, './/*[@data-testid="videoPlayer"]'
                )
                if videos:
                    media_urls.append("[Video içeriği]")

                # GIF
                gifs = article.find_elements(
                    By.XPATH, './/video'
                )
                for gif in gifs:
                    poster = gif.get_attribute("poster")
                    if poster:
                        media_urls.append(poster)

            except:
                pass

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
            )

        except StaleElementReferenceException:
            record_event(
                self.run_log,
                "tweet_parsing",
                "debug",
                "Tweet article became stale while parsing",
            )
            return None
        except Exception as e:
            record_event(
                self.run_log,
                "tweet_parsing",
                "warning",
                f"Tweet parsing failed: {e}",
                reason="tweet_parse_failed",
            )
            return None

    def _get_full_tweet_text(self, tweet_url: str) -> str:
        """
        Yeni tab'da tweet açıp tam metni al

        Args:
            tweet_url: Tweet'in URL'si

        Returns:
            Tam tweet metni
        """
        text = ""
        main_window = self.driver.current_window_handle

        try:
            # Yeni tab aç
            self.driver.execute_script(f"window.open('{tweet_url}', '_blank');")

            # Yeni tab'a geç
            self.driver.switch_to.window(self.driver.window_handles[-1])

            # Sayfanın tam yüklenmesini bekle
            time.sleep(2)

            # Tweet metnini al - visibility bekle (presence değil)
            wait = WebDriverWait(self.driver, 8)
            try:
                text_element = wait.until(
                    EC.visibility_of_element_located((By.XPATH, '//article[@data-testid="tweet"]//div[@data-testid="tweetText"]'))
                )
                # Element görünür oldu, biraz daha bekle (lazy load için)
                time.sleep(0.5)
                text = text_element.text
            except TimeoutException:
                # Alternatif: tüm tweetText elementleri
                try:
                    text_elements = self.driver.find_elements(By.XPATH, '//*[@data-testid="tweetText"]')
                    if text_elements:
                        # İlk elementi görünür yap
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", text_elements[0])
                        time.sleep(0.5)
                        text = text_elements[0].text
                except:
                    pass

        except Exception as e:
            print(f"    [!] Hata: {str(e)[:30]}")
            record_event(
                self.run_log,
                "full_text_extraction",
                "warning",
                f"Full text extraction failed: {e}",
                reason="full_text_failed",
                url=tweet_url,
            )
        finally:
            # Yeni tab'ı kapat ve ana tab'a dön
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass

        if not text:
            record_event(
                self.run_log,
                "full_text_extraction",
                "warning",
                "Full text extraction returned empty content",
                reason="full_text_failed",
                url=tweet_url,
            )
        return text

    def _get_article_content(self, tweet_url: str) -> str:
        """
        Article içeriğini al - document.body.innerText kullanarak
        """
        content_parts = []
        main_window = self.driver.current_window_handle

        try:
            self.driver.execute_script(f"window.open('{tweet_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(3)

            # Scroll yap
            last_height = 0
            for _ in range(20):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(0.5)
                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)

            # Tüm sayfa text'ini al
            page_text = self.driver.execute_script("return document.body.innerText;")
            lines = page_text.split('\n')

            skip_patterns = [
                'home', 'explore', 'notifications', 'messages', 'grok',
                'premium', 'profile', 'more', 'post', 'subscribe',
                'follow', 'following', 'followers', 'likes', 'bookmark', 'share',
                'reply', 'repost', 'quote', 'view', 'show', 'hide',
                'keyboard shortcuts', 'article', 'conversation',
                'relevant people', 'terms of service', 'privacy policy',
                '© 2', 'log out', 'settings', 'trending',
                'reposted', 'liked', 'joined', 'posts', 'replies', 'media',
            ]

            collecting = False

            for line in lines:
                line = line.strip()
                if not line or len(line) < 40:
                    if ' – ' in line:
                        content_parts.append(f"\n## {line}\n")
                        collecting = True
                    continue

                line_lower = line.lower()
                if any(skip in line_lower for skip in skip_patterns):
                    continue
                if line.startswith('@'):
                    continue

                if len(line) > 60:
                    collecting = True
                    if line not in content_parts:
                        content_parts.append(line)

            result = "\n\n".join(content_parts)
            print(f"    ✓ Article: {len(result)} karakter")
            if not result:
                record_event(
                    self.run_log,
                    "article_extraction",
                    "warning",
                    "Article extraction returned empty content",
                    reason="article_extraction_failed",
                    url=tweet_url,
                )
            return result

        except Exception as e:
            print(f"    [!] Article hata: {str(e)[:50]}")
            record_event(
                self.run_log,
                "article_extraction",
                "warning",
                f"Article extraction failed: {e}",
                reason="article_extraction_failed",
                url=tweet_url,
            )
            return ""
        finally:
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass

    def _scroll_down(self):
        """Sayfayı aşağı kaydır ve X'in sanal timeline DOM'unu tetikle."""
        before = self._timeline_snapshot()

        # X timeline React/virtualized bir liste. Bazı profillerde window.scrollBy
        # tek başına hiçbir şeyi tetiklemiyor; gerçek wheel input daha güvenilir.
        for attempt in range(4):
            self._perform_timeline_scroll(attempt + 1)
            time.sleep(random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX))

            for _ in range(10):
                after = self._timeline_snapshot()
                if self._timeline_advanced(before, after):
                    return True
                time.sleep(0.3)

        return False

    def _perform_timeline_scroll(self, intensity: int = 1) -> None:
        """Birden fazla scroll yöntemi dene; X her yönteme aynı cevap vermiyor."""
        delta = 900 * max(1, intensity)

        try:
            self.driver.execute_script("window.focus();")
        except Exception:
            pass

        try:
            ActionChains(self.driver).scroll_by_amount(0, delta).perform()
            time.sleep(0.15)
        except Exception:
            pass

        try:
            self.driver.execute_cdp_cmd(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": 600,
                    "y": 600,
                    "deltaX": 0,
                    "deltaY": delta,
                },
            )
            time.sleep(0.15)
        except Exception:
            pass

        try:
            self.driver.execute_script(
                """
                const delta = arguments[0];
                window.dispatchEvent(new WheelEvent('wheel', {
                  deltaY: delta,
                  bubbles: true,
                  cancelable: true
                }));
                const scroller = document.scrollingElement || document.documentElement || document.body;
                scroller.scrollBy(0, delta);
                """,
                delta,
            )
            time.sleep(0.15)
        except Exception:
            pass

        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.15)
        except Exception:
            pass

    def _timeline_snapshot(self) -> Dict:
        """DOM ve scroll durumunu tek yerde ölç."""
        articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
        try:
            scroll_y = int(self.driver.execute_script("return Math.round(window.scrollY || 0);") or 0)
            scroll_height = int(
                self.driver.execute_script(
                    "return Math.round(document.documentElement.scrollHeight || document.body.scrollHeight || 0);"
                )
                or 0
            )
            viewport_height = int(
                self.driver.execute_script("return Math.round(window.innerHeight || document.documentElement.clientHeight || 0);")
                or 0
            )
        except Exception:
            scroll_y = 0
            scroll_height = 0
            viewport_height = 0

        ids = self._get_article_ids_fast(articles)
        return {
            "article_count": len(articles),
            "article_ids": ids,
            "articles": articles,
            "scroll_y": scroll_y,
            "scroll_height": scroll_height,
            "viewport_height": viewport_height,
        }

    def _timeline_advanced(self, before: Dict, after: Dict) -> bool:
        """X timeline progress'i article sayısı, yeni ID veya scroll hareketinden anla."""
        before_ids = before.get("article_ids", set())
        after_ids = after.get("article_ids", set())
        new_uncollected_ids = after_ids - before_ids - self.collected_tweet_ids

        if new_uncollected_ids:
            return True
        if after.get("article_count", 0) > before.get("article_count", 0):
            return True
        if after.get("scroll_height", 0) > before.get("scroll_height", 0):
            return True
        if after.get("scroll_y", 0) > before.get("scroll_y", 0) + 80:
            return True
        return False

    def _timeline_end_distance(self) -> Optional[int]:
        """Viewport'un document bottom'a yaklaşık mesafesi."""
        try:
            value = self.driver.execute_script(
                """
                const scrollY = window.scrollY || 0;
                const innerHeight = window.innerHeight || document.documentElement.clientHeight || 0;
                const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight || 0;
                return Math.round(scrollHeight - scrollY - innerHeight);
                """
            )
            return int(value)
        except Exception:
            return None

    def _classify_visible_timeline_issue(self) -> Optional[str]:
        """Basit body text sinyallerinden neden ayrımı yap."""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            return None

        if any(text in body_text for text in ("log in", "sign in", "giriş yap", "oturum aç")):
            return "login_failed"
        if any(text in body_text for text in ("rate limit", "try again later", "bir süre sonra tekrar dene")):
            return "timeline_stalled"
        if any(text in body_text for text in ("these posts are protected", "account suspended", "this account doesn")):
            return "profile_navigation_failed"
        return None

    def _record_partial_target_not_met(self, label: str, collected: int, target: Optional[int], no_progress_cycles: int) -> None:
        if not target or collected >= target:
            return

        visible_issue = self._classify_visible_timeline_issue()
        end_distance = self._timeline_end_distance()
        reason = visible_issue or ("timeline_empty" if collected == 0 else "partial_target_not_met")
        message = f"{label} scrape ended before requested target was reached"
        record_event(
            self.run_log,
            "timeline_loading",
            "warning" if collected else "error",
            message,
            reason=reason,
            collected=collected,
            target=target,
            missing=target - collected,
            no_progress_cycles=no_progress_cycles,
            end_distance_px=end_distance,
        )

    def _get_article_ids_fast(self, articles) -> set:
        """Mevcut DOM article elementlerinden tweet ID'lerini hızlı çıkar."""
        ids = set()
        for article in articles:
            try:
                time_element = article.find_element(By.TAG_NAME, "time")
                parent_link = time_element.find_element(By.XPATH, "./ancestor::a")
                href = parent_link.get_attribute("href")
                if href and "/status/" in href:
                    tweet_id = href.split("/status/")[-1].split("?")[0].split("/")[0]
                    if tweet_id:
                        ids.add(tweet_id)
            except Exception:
                continue
        return ids

    def _scroll_recovery(self):
        """Timeline takıldığında daha güçlü native scroll denemeleri yap."""
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(0.2)
        except Exception:
            pass

        for intensity in (2, 3, 4, 5):
            self._perform_timeline_scroll(intensity)
            time.sleep(0.4)

    def _scroll_to_bottom(self):
        """Sayfanın en altına git"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX))

    def scrape_by_count(self, count: int) -> List[Tweet]:
        """
        Belirli sayıda tweet topla

        Args:
            count: Toplanacak tweet sayısı

        Returns:
            Tweet listesi
        """
        print(f"{count} tweet toplanıyor...")
        print("(İptal etmek için Ctrl+C - toplananlar kaydedilecek)\n")
        self.tweets_collected = []  # Instance variable olarak sakla
        no_progress_count = 0
        no_new_collected_count = 0
        recovery_attempts = 0
        max_no_progress = 8
        max_no_new_collected = 14
        max_recovery_attempts = 3
        scan_cycles = 0
        max_scan_cycles = max(60, count * 8)
        browser_lost = False

        try:
            while len(self.tweets_collected) < count:
                scan_cycles += 1
                collected_before = len(self.tweets_collected)
                # Mevcut tweetleri topla
                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])

                for article in articles:
                    if len(self.tweets_collected) >= count:
                        break

                    result = self._parse_tweet_element(article)
                    # SKIP_ALREADY_COLLECTED = zaten toplandı, bu "yeni tweet yok" değil
                    if result == SKIP_ALREADY_COLLECTED:
                        continue
                    if result is None:
                        continue
                    tweet = result
                    self.tweets_collected.append(tweet)
                    article_tag = " [ARTICLE]" if tweet.has_article else ""
                    show_more_tag = " [SHOW MORE]" if tweet.needs_full_text else ""
                    print(f"  [{len(self.tweets_collected)}/{count}] Tweet toplandı: {tweet.date_str}{article_tag}{show_more_tag}")

                collected_after = len(self.tweets_collected)
                if collected_after >= count:
                    break

                scroll_advanced = self._scroll_down()

                if collected_after > collected_before:
                    no_progress_count = 0
                    no_new_collected_count = 0
                else:
                    no_new_collected_count += 1
                    if scroll_advanced:
                        no_progress_count = 0
                    else:
                        no_progress_count += 1

                if (
                    no_progress_count in (2, 4, 6)
                    and recovery_attempts < max_recovery_attempts
                ):
                    recovery_attempts += 1
                    print(f"Timeline takıldı gibi görünüyor, scroll recovery deneniyor ({recovery_attempts}/{max_recovery_attempts})...")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Timeline did not advance; trying scroll recovery",
                        collected=len(self.tweets_collected),
                        target=count,
                        no_progress_cycles=no_progress_count,
                        no_new_collected_cycles=no_new_collected_count,
                        recovery_attempts=recovery_attempts,
                        scan_cycles=scan_cycles,
                    )
                    self._scroll_recovery()

                if no_new_collected_count >= max_no_new_collected:
                    print(f"{max_no_new_collected} tarama turunda yeni tweet parse edilemedi. Kısmi sonuçla duruluyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Timeline advanced or scanned but produced no new parsed tweets",
                        reason="timeline_empty" if not self.tweets_collected else "partial_target_not_met",
                        collected=len(self.tweets_collected),
                        target=count,
                        no_new_collected_cycles=no_new_collected_count,
                        recovery_attempts=recovery_attempts,
                        scan_cycles=scan_cycles,
                    )
                    break

                if no_progress_count >= max_no_progress:
                    print(f"Timeline {max_no_progress} denemede ilerlemedi. Kısmi sonuçla duruluyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Timeline stopped advancing after recovery attempts",
                        reason="timeline_empty" if not self.tweets_collected else "timeline_stalled",
                        collected=len(self.tweets_collected),
                        target=count,
                        no_progress_cycles=no_progress_count,
                        no_new_collected_cycles=no_new_collected_count,
                        recovery_attempts=recovery_attempts,
                        scan_cycles=scan_cycles,
                    )
                    break

                if scan_cycles >= max_scan_cycles:
                    print("Maksimum timeline tarama denemesine ulaşıldı. Kısmi sonuçla duruluyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Maximum timeline scan cycles reached before target count",
                        reason="partial_target_not_met",
                        collected=len(self.tweets_collected),
                        target=count,
                        scan_cycles=scan_cycles,
                    )
                    break

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} tweet toplandı.")
            raise  # Ana programa ilet
        except NoSuchWindowException as e:
            browser_lost = True
            print(f"\nBrowser penceresi kapandı veya Chrome bağlantısı koptu. {len(self.tweets_collected)} tweet kısmi sonuç olarak kullanılacak.")
            record_event(
                self.run_log,
                "browser",
                "error" if not self.tweets_collected else "warning",
                f"Browser window closed during count scrape: {e}",
                reason="browser_window_closed",
                collected=len(self.tweets_collected),
                target=count,
                scan_cycles=scan_cycles,
            )
        except WebDriverException as e:
            if "no such window" not in str(e).lower() and "web view not found" not in str(e).lower():
                raise
            browser_lost = True
            print(f"\nChrome webview kayboldu. {len(self.tweets_collected)} tweet kısmi sonuç olarak kullanılacak.")
            record_event(
                self.run_log,
                "browser",
                "error" if not self.tweets_collected else "warning",
                f"Chrome webview was lost during count scrape: {e}",
                reason="browser_window_closed",
                collected=len(self.tweets_collected),
                target=count,
                scan_cycles=scan_cycles,
            )

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        if browser_lost:
            print("Browser kapandığı için show more/article tam metin alma adımı atlandı.")
        else:
            self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} tweet toplandı.")
        if not self.tweets_collected:
            record_event(
                self.run_log,
                "timeline_loading",
                "error",
                "No tweets collected after count scrape",
                reason="timeline_empty",
            )
        else:
            self._record_partial_target_not_met(
                "Count",
                len(self.tweets_collected),
                count,
                no_progress_count,
            )
        return self.tweets_collected

    def _process_show_more_tweets(self):
        """Show more ve article olan tweetlerin tam metnini al (scroll bittikten sonra)"""
        show_more_tweets = [t for t in self.tweets_collected if t.needs_full_text]
        article_tweets = [t for t in self.tweets_collected if t.has_article]

        total = len(show_more_tweets) + len(article_tweets)
        if total == 0:
            return

        print(f"\n{total} uzun içerik alınıyor ({len(show_more_tweets)} show more, {len(article_tweets)} article)...")
        current = 0

        for tweet in show_more_tweets:
            current += 1
            try:
                print(f"  [{current}/{total}] Show more - tam metin alınıyor...")
                full_text = self._get_full_tweet_text(tweet.tweet_url)
                if full_text:
                    tweet.text = full_text
                    tweet.needs_full_text = False
            except Exception as e:
                print(f"    [!] Hata: {str(e)[:30]}")

        for tweet in article_tweets:
            current += 1
            try:
                print(f"  [{current}/{total}] Article içeriği alınıyor...")
                article_content = self._get_article_content(tweet.tweet_url)
                if article_content:
                    if tweet.text:
                        tweet.text = tweet.text + "\n\n--- ARTICLE İÇERİĞİ ---\n\n" + article_content
                    else:
                        tweet.text = article_content
                    tweet.has_article = False
                    print(f"    ✓ {len(article_content)} karakter alındı")
                else:
                    print(f"    ✗ Article içeriği alınamadı")
            except Exception as e:
                print(f"    [!] Hata: {str(e)[:50]}")

        print("Tam içerikler alındı.\n")

    def scrape_by_date(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> List[Tweet]:
        """
        Tarih aralığındaki tweetleri topla

        Args:
            start_date: Başlangıç tarihi (en eski)
            end_date: Bitiş tarihi (en yeni), None ise bugün

        Returns:
            Tweet listesi
        """
        if end_date is None:
            end_date = datetime.now(start_date.tzinfo) if start_date.tzinfo else datetime.now()

        print(f"Tarih aralığı: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        print("(İptal etmek için Ctrl+C - toplananlar kaydedilecek)\n")
        self.tweets_collected = []
        no_progress_count = 0
        max_no_progress = 8
        scan_cycles = 0
        max_scan_cycles = 160
        reached_start_date = False

        try:
            while not reached_start_date:
                scan_cycles += 1
                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_tweets_found = False

                for article in articles:
                    result = self._parse_tweet_element(article)
                    if result == SKIP_ALREADY_COLLECTED or result is None:
                        continue
                    tweet = result
                    if tweet:
                        # Tarih kontrolü
                        tweet_date = tweet.date.replace(tzinfo=None) if tweet.date.tzinfo else tweet.date
                        start_date_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
                        end_date_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date

                        if tweet_date < start_date_naive:
                            reached_start_date = True
                            break

                        if start_date_naive <= tweet_date <= end_date_naive:
                            self.tweets_collected.append(tweet)
                            new_tweets_found = True
                            print(f"  [{len(self.tweets_collected)}] Tweet: {tweet.date_str}")

                if reached_start_date:
                    break

                scroll_advanced = self._scroll_down()

                if new_tweets_found or scroll_advanced:
                    no_progress_count = 0
                else:
                    no_progress_count += 1

                if no_progress_count in (2, 4, 6):
                    print("Timeline takıldı gibi görünüyor, scroll recovery deneniyor...")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Timeline did not advance during date scrape; trying scroll recovery",
                        collected=len(self.tweets_collected),
                        no_progress_cycles=no_progress_count,
                        scan_cycles=scan_cycles,
                    )
                    self._scroll_recovery()

                if no_progress_count >= max_no_progress:
                    print("Daha fazla tweet bulunamadı veya timeline ilerlemiyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Timeline stopped advancing before date scrape completed",
                        reason="timeline_empty" if not self.tweets_collected else "timeline_stalled",
                        collected=len(self.tweets_collected),
                        no_progress_cycles=no_progress_count,
                        scan_cycles=scan_cycles,
                    )
                    break

                if scan_cycles >= max_scan_cycles:
                    print("Maksimum timeline tarama denemesine ulaşıldı. Kısmi sonuçla duruluyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Maximum timeline scan cycles reached during date scrape",
                        reason="partial_target_not_met",
                        collected=len(self.tweets_collected),
                        scan_cycles=scan_cycles,
                    )
                    break

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} tweet toplandı.")
            raise

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} tweet toplandı.")
        if not self.tweets_collected:
            record_event(
                self.run_log,
                "timeline_loading",
                "error",
                "No tweets collected after date scrape",
                reason="timeline_empty",
            )
        return self.tweets_collected

    def scrape_last_n_days(self, days: int) -> List[Tweet]:
        """
        Son N gündeki tweetleri topla

        Args:
            days: Gün sayısı

        Returns:
            Tweet listesi
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.scrape_by_date(start_date, end_date)

    def scrape_bookmarks(self, count: int = None, get_all: bool = False) -> List[Tweet]:
        """
        Bookmark'lardan tweet topla

        Args:
            count: Toplanacak bookmark sayısı (None ise get_all kullanılır)
            get_all: True ise tüm bookmark'ları topla

        Returns:
            Tweet listesi
        """
        if get_all:
            print("Tüm bookmark'lar toplanıyor...")
        else:
            print(f"{count} bookmark toplanıyor...")
        print("(İptal etmek için Ctrl+C - toplananlar kaydedilecek)\n")

        self.tweets_collected = []
        no_progress_count = 0
        max_no_progress = 8
        scan_cycles = 0
        max_scan_cycles = 180 if get_all else max(60, (count or 20) * 8)

        try:
            while True:
                scan_cycles += 1
                # Count kontrolü
                if not get_all and count and len(self.tweets_collected) >= count:
                    break

                # Mevcut tweetleri topla
                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_tweets_found = False

                for article in articles:
                    if not get_all and count and len(self.tweets_collected) >= count:
                        break

                    result = self._parse_tweet_element(article)
                    if result == SKIP_ALREADY_COLLECTED or result is None:
                        continue
                    tweet = result
                    self.tweets_collected.append(tweet)
                    new_tweets_found = True
                    article_tag = " [ARTICLE]" if tweet.has_article else ""
                    show_more_tag = " [SHOW MORE]" if tweet.needs_full_text else ""
                    if count:
                        print(f"  [{len(self.tweets_collected)}/{count}] Bookmark toplandı: {tweet.date_str}{article_tag}{show_more_tag}")
                    else:
                        print(f"  [{len(self.tweets_collected)}] Bookmark toplandı: {tweet.date_str}{article_tag}{show_more_tag}")

                if not get_all and count and len(self.tweets_collected) >= count:
                    break

                scroll_advanced = self._scroll_down()

                if new_tweets_found or scroll_advanced:
                    no_progress_count = 0
                else:
                    no_progress_count += 1

                if no_progress_count in (2, 4, 6):
                    print("Timeline takıldı gibi görünüyor, scroll recovery deneniyor...")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Bookmarks timeline did not advance; trying scroll recovery",
                        collected=len(self.tweets_collected),
                        target=count,
                        no_progress_cycles=no_progress_count,
                        scan_cycles=scan_cycles,
                    )
                    self._scroll_recovery()

                if no_progress_count >= max_no_progress:
                    print("Daha fazla bookmark bulunamadı veya timeline ilerlemiyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Bookmarks timeline stopped advancing",
                        reason="timeline_empty" if not self.tweets_collected else "timeline_stalled",
                        collected=len(self.tweets_collected),
                        target=count,
                        no_progress_cycles=no_progress_count,
                        scan_cycles=scan_cycles,
                    )
                    break

                if scan_cycles >= max_scan_cycles:
                    print("Maksimum bookmark tarama denemesine ulaşıldı. Kısmi sonuçla duruluyor.")
                    record_event(
                        self.run_log,
                        "timeline_loading",
                        "warning",
                        "Maximum bookmark scan cycles reached",
                        reason="partial_target_not_met" if count else "timeline_stalled",
                        collected=len(self.tweets_collected),
                        target=count,
                        scan_cycles=scan_cycles,
                    )
                    break

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} bookmark toplandı.")
            raise  # Ana programa ilet

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} bookmark toplandı.")
        if not self.tweets_collected:
            record_event(
                self.run_log,
                "timeline_loading",
                "error",
                "No bookmarks collected",
                reason="timeline_empty",
            )
        elif count:
            self._record_partial_target_not_met(
                "Bookmarks",
                len(self.tweets_collected),
                count,
                no_progress_count,
            )
        return self.tweets_collected
