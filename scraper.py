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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
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

    def __init__(self, headless: bool = False):
        """
        Scraper'ı başlat

        Args:
            headless: True ise browser görünmeden çalışır
        """
        self.driver = None
        self.headless = headless
        self.collected_tweet_ids = set()

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

    def stop(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()
            self.driver = None

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
                return True
            except TimeoutException:
                print("Giriş kontrol ediliyor...")
                return True  # Devam etmeyi dene

        except Exception as e:
            print(f"Giriş hatası: {e}")
            return False

    def manual_login(self) -> bool:
        """
        Manuel giriş - Kullanıcı kendisi giriş yapar (Google, Apple vs. için)

        Returns:
            Başarılı ise True
        """
        try:
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
                    return True

            print("Giriş yapılmış görünüyor, devam ediliyor...")
            return True

        except Exception as e:
            print(f"Manuel giriş hatası: {e}")
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
            self.driver.get(url)

            # Profil yüklendi mi kontrol et (tweet görünene kadar bekle)
            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )
            print("Profil yüklendi!")
            return True

        except TimeoutException:
            print("Profil yüklenemedi veya tweet bulunamadı.")
            return False
        except Exception as e:
            print(f"Profil navigasyon hatası: {e}")
            return False

    def navigate_to_bookmarks(self) -> bool:
        """
        Bookmark sayfasına git

        Returns:
            Başarılı ise True
        """
        try:
            print(f"Bookmarks sayfasına gidiliyor: {X_BOOKMARKS_URL}")
            self.driver.get(X_BOOKMARKS_URL)

            # Bookmark sayfası yüklendi mi kontrol et
            wait = WebDriverWait(self.driver, 15)
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//article[@data-testid="tweet"]'))
            )
            print("Bookmarks sayfası yüklendi!")
            return True

        except TimeoutException:
            print("Bookmarks yüklenemedi veya bookmark bulunamadı.")
            return False
        except Exception as e:
            print(f"Bookmarks navigasyon hatası: {e}")
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
            return None
        except Exception as e:
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
        finally:
            # Yeni tab'ı kapat ve ana tab'a dön
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass

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
            return result

        except Exception as e:
            print(f"    [!] Article hata: {str(e)[:50]}")
            return ""
        finally:
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass

    def _scroll_down(self):
        """Sayfayı aşağı kaydır ve yeni içerik yüklenmesini bekle"""
        # Scroll öncesi tweet sayısı
        old_count = len(self.driver.find_elements(By.XPATH, XPATHS["tweet_article"]))

        # Scroll yap
        self.driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX))

        # Yeni tweet yüklenmesini bekle (max 5 saniye)
        for _ in range(10):
            new_count = len(self.driver.find_elements(By.XPATH, XPATHS["tweet_article"]))
            if new_count > old_count:
                break
            time.sleep(0.5)

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
        stale_scroll_count = 0  # Scroll yapıp DOM'da yeni article gelmeyen sayı
        max_stale_scrolls = 10  # Ardışık 10 scroll'da DOM'da yeni element yoksa dur
        last_height = 0
        same_height_count = 0

        try:
            while len(self.tweets_collected) < count:
                # Scroll öncesi DOM'daki article sayısı
                articles_before = len(self.driver.find_elements(By.XPATH, XPATHS["tweet_article"]))

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

                # Aşağı kaydır
                self._scroll_down()

                # Scroll sonrası DOM'daki article sayısı
                articles_after = len(self.driver.find_elements(By.XPATH, XPATHS["tweet_article"]))

                # Sayfa sonu tespiti: scroll height değişmedi mi?
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    same_height_count += 1
                else:
                    same_height_count = 0
                last_height = new_height

                # DOM'da yeni article geldi mi?
                if articles_after <= articles_before and same_height_count >= 3:
                    stale_scroll_count += 1
                    # Ekstra bekleme ile bir şans daha ver
                    if stale_scroll_count <= 3:
                        time.sleep(3)
                else:
                    stale_scroll_count = 0

                if stale_scroll_count >= max_stale_scrolls:
                    print("Sayfa sonuna ulaşıldı, daha fazla tweet yüklenmiyor.")
                    break

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} tweet toplandı.")
            raise  # Ana programa ilet

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} tweet toplandı.")
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
        no_new_tweets_count = 0
        max_no_new_tweets = 15
        reached_start_date = False

        try:
            while not reached_start_date:
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

                if new_tweets_found:
                    no_new_tweets_count = 0
                else:
                    no_new_tweets_count += 1

                if no_new_tweets_count >= max_no_new_tweets:
                    print("Daha fazla tweet bulunamadı veya tarih aralığı dışına çıkıldı.")
                    break

                if reached_start_date:
                    break

                self._scroll_down()

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} tweet toplandı.")
            raise

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} tweet toplandı.")
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
        no_new_tweets_count = 0
        max_no_new_tweets = 10  # Ardışık 10 scroll'da yeni tweet yoksa dur

        try:
            while True:
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

                if new_tweets_found:
                    no_new_tweets_count = 0
                else:
                    no_new_tweets_count += 1

                if no_new_tweets_count >= max_no_new_tweets:
                    print("Daha fazla bookmark bulunamadı.")
                    break

                # Aşağı kaydır
                self._scroll_down()

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} bookmark toplandı.")
            raise  # Ana programa ilet

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} bookmark toplandı.")
        return self.tweets_collected
