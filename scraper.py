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
    IMPLICIT_WAIT,
    PAGE_LOAD_TIMEOUT,
    SCROLL_PAUSE_MIN,
    SCROLL_PAUSE_MAX,
    CHROME_OPTIONS,
    USER_AGENT,
    XPATHS,
)


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
    has_article: bool = False  # Article varsa True


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

    def _parse_tweet_element(self, article) -> Optional[Tweet]:
        """
        Tweet elementinden veri çıkar

        Args:
            article: Tweet article elementi

        Returns:
            Tweet objesi veya None (reply ise)
        """
        try:
            # NOT: Reply filtreleme KALDIRILDI
            # Posts sekmesinde zaten sadece kullanıcının içerikleri var
            # Thread'ler de dahil edilecek

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

            # Zaten toplandıysa atla
            if tweet_id in self.collected_tweet_ids:
                return None

            # "Show more" kontrolü
            has_show_more = False
            has_article = False

            # Show more butonu
            try:
                article.find_element(By.CSS_SELECTOR, '[data-testid="tweet-text-show-more-link"]')
                has_show_more = True
            except NoSuchElementException:
                pass

            # Tweet metnini al (article kontrolü için önce text lazım)
            text = ""
            try:
                text_element = article.find_element(By.XPATH, './/*[@data-testid="tweetText"]')
                text = text_element.text
            except NoSuchElementException:
                pass

            # Article/Quoted Tweet kontrolü
            # Tweet içinde başka tweet (quoted tweet) veya article kartı var mı?
            try:
                # DEBUG: Tüm linkleri ve elementleri logla
                all_status_links = article.find_elements(By.XPATH, './/a[contains(@href, "/status/")]')

                # ÖNCELİKLİ: Tweet içinde BAŞKA tweet linki var mı? (quoted tweet)
                for link in all_status_links:
                    href = link.get_attribute("href") or ""
                    # Kendi tweet ID'si değilse = quoted tweet var
                    if "/status/" in href and tweet_id not in href:
                        has_article = True
                        print(f"      [DEBUG] QUOTED TWEET BULUNDU: {href[:50]}")
                        break

                # Quoted tweet testid'i
                if not has_article:
                    quoted = article.find_elements(By.CSS_SELECTOR, '[data-testid*="quote"]')
                    if quoted:
                        has_article = True
                        print(f"      [DEBUG] QUOTE TESTID BULUNDU")

                # Card wrapper (article kartları)
                if not has_article:
                    cards = article.find_elements(By.CSS_SELECTOR, '[data-testid="card.wrapper"]')
                    if cards:
                        has_article = True
                        print(f"      [DEBUG] CARD WRAPPER BULUNDU")

                # Card layout
                if not has_article:
                    cards = article.find_elements(By.CSS_SELECTOR, '[data-testid*="card.layout"]')
                    if cards:
                        has_article = True
                        print(f"      [DEBUG] CARD LAYOUT BULUNDU")

                # /i/ linkleri (X Notes vs)
                if not has_article:
                    article_links = article.find_elements(By.XPATH, './/a[contains(@href, "/i/")]')
                    if article_links:
                        has_article = True
                        print(f"      [DEBUG] /i/ LINK BULUNDU")

            except NoSuchElementException:
                pass
            except Exception as e:
                print(f"      [DEBUG] Article detection hatası: {str(e)[:30]}")

            # Text zaten yukarıda alındı

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
                needs_full_text=has_show_more,  # Show more varsa True
                has_article=has_article,  # Article varsa True
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
        Article/Quoted Tweet içeriğini al
        Tweet'e git, içindeki quoted tweet veya article'a tıkla, scroll yap, içeriği al

        Args:
            tweet_url: Tweet'in URL'si

        Returns:
            Article/Quoted tweet içeriği
        """
        text = ""
        main_window = self.driver.current_window_handle

        # Tweet URL'sinden kendi ID'sini çıkar
        own_tweet_id = ""
        if "/status/" in tweet_url:
            own_tweet_id = tweet_url.split("/status/")[-1].split("?")[0].split("/")[0]

        try:
            # 1. Tweet sayfasını yeni tab'da aç
            self.driver.execute_script(f"window.open('{tweet_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(3)
            original_url = self.driver.current_url

            clicked = False

            # ÖNCELİKLİ: Quoted tweet'e tıkla (başka tweet linki)
            # Kendi tweet ID'si OLMAYAN /status/ linklerini bul ve tıkla
            if not clicked:
                try:
                    all_status_links = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/status/")]')
                    for link in all_status_links:
                        href = link.get_attribute("href") or ""
                        # Kendi tweet'i değilse tıkla
                        if "/status/" in href and own_tweet_id and own_tweet_id not in href:
                            print(f"    → Quoted tweet bulundu: {href[:60]}...")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                            time.sleep(0.5)
                            link.click()
                            time.sleep(3)
                            if self.driver.current_url != original_url:
                                clicked = True
                                print(f"    → Quoted tweet açıldı: {self.driver.current_url[:60]}...")
                                break
                except Exception as e:
                    print(f"    [!] Quoted tweet tıklama hatası: {str(e)[:30]}")

            # Quoted tweet testid ile dene
            if not clicked:
                try:
                    quoted_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid*="quote"]')
                    for qe in quoted_elements:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", qe)
                            time.sleep(0.3)
                            qe.click()
                            time.sleep(2)
                            if self.driver.current_url != original_url:
                                clicked = True
                                print(f"    → Quote element açıldı: {self.driver.current_url[:60]}...")
                                break
                        except:
                            continue
                except:
                    pass

            # Card wrapper'a tıkla
            if not clicked:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="card.wrapper"]')
                    for card in cards:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                            time.sleep(0.3)
                            card.click()
                            time.sleep(2)
                            if self.driver.current_url != original_url:
                                clicked = True
                                print(f"    → Card açıldı: {self.driver.current_url[:60]}...")
                                break
                        except:
                            continue
                except:
                    pass

            # /i/ linklere tıkla (X Notes vs)
            if not clicked:
                try:
                    i_links = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/i/")]')
                    for link in i_links:
                        href = link.get_attribute("href") or ""
                        if "/i/" in href:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                            time.sleep(0.3)
                            link.click()
                            time.sleep(2)
                            if self.driver.current_url != original_url:
                                clicked = True
                                print(f"    → /i/ link açıldı: {self.driver.current_url[:60]}...")
                                break
                except:
                    pass

            # 2. Article/Quoted tweet sayfasında scroll yaparak içerik al
            time.sleep(1)
            text = self._scroll_and_collect_article_text()

            if text:
                print(f"    ✓ {len(text)} karakter içerik alındı")
            else:
                print(f"    [!] İçerik alınamadı")

        except Exception as e:
            print(f"    [!] Article hatası: {str(e)[:50]}")
        finally:
            # Tab'ı kapat ve ana pencereye dön
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass

        return text

    def _scroll_and_collect_article_text(self) -> str:
        """
        Tweet sayfasından SADECE ANA TWEET'in içeriğini al
        Replies/yorumları ALMA

        Returns:
            Ana tweet metni
        """
        try:
            # Sayfanın başına git
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1.5)

            collected_text = ""

            # SADECE İLK (ANA) TWEET'İ AL - replies değil
            # X'te ana tweet sayfadaki ilk article elementi
            try:
                # İlk article elementini bul (ana tweet)
                first_article = self.driver.find_element(By.XPATH, '(//article[@data-testid="tweet"])[1]')

                # Bu article içindeki tweetText'i al
                tweet_text_elem = first_article.find_element(By.XPATH, './/*[@data-testid="tweetText"]')
                collected_text = tweet_text_elem.text.strip()

            except NoSuchElementException:
                # Alternatif: İlk tweetText'i al
                try:
                    first_tweet_text = self.driver.find_element(By.XPATH, '(//*[@data-testid="tweetText"])[1]')
                    collected_text = first_tweet_text.text.strip()
                except:
                    pass

            # Eğer metin kısa ise, belki thread var - birkaç tweet daha kontrol et
            # Ama sadece ANA KULLANICININ tweetlerini al (aynı username)
            if collected_text and len(collected_text) < 500:
                try:
                    # Sayfadaki URL'den username'i al
                    current_url = self.driver.current_url
                    if "/status/" in current_url:
                        username = current_url.split("x.com/")[1].split("/")[0] if "x.com/" in current_url else ""

                        if username:
                            # Aynı kullanıcının diğer tweetlerini de al (thread)
                            all_articles = self.driver.find_elements(By.XPATH, '//article[@data-testid="tweet"]')
                            thread_texts = [collected_text]

                            for i, art in enumerate(all_articles[1:5]):  # Max 4 tweet daha (thread için)
                                try:
                                    # Bu tweet aynı kullanıcıya mı ait?
                                    user_link = art.find_element(By.XPATH, './/a[contains(@href, "/" + username + "/")]')
                                    if user_link:
                                        text_elem = art.find_element(By.XPATH, './/*[@data-testid="tweetText"]')
                                        t = text_elem.text.strip()
                                        if t and t not in thread_texts:
                                            thread_texts.append(t)
                                except:
                                    break  # Farklı kullanıcı = thread bitti

                            if len(thread_texts) > 1:
                                collected_text = "\n\n".join(thread_texts)
                except:
                    pass

            return collected_text

        except Exception as e:
            print(f"    [!] Tweet içeriği alma hatası: {str(e)[:30]}")
            return ""

    def _scroll_down(self):
        """Sayfayı aşağı kaydır"""
        self.driver.execute_script("window.scrollBy(0, 2000);")  # Daha hızlı scroll
        time.sleep(random.uniform(SCROLL_PAUSE_MIN, SCROLL_PAUSE_MAX))

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
        no_new_tweets_count = 0
        max_no_new_tweets = 10  # Ardışık 10 scroll'da yeni tweet yoksa dur

        try:
            while len(self.tweets_collected) < count:
                # Mevcut tweetleri topla
                articles = self.driver.find_elements(By.XPATH, XPATHS["tweet_article"])
                new_tweets_found = False

                for article in articles:
                    if len(self.tweets_collected) >= count:
                        break

                    tweet = self._parse_tweet_element(article)
                    if tweet:
                        self.tweets_collected.append(tweet)
                        new_tweets_found = True
                        article_tag = " [ARTICLE]" if tweet.has_article else ""
                        show_more_tag = " [SHOW MORE]" if tweet.needs_full_text else ""
                        print(f"  [{len(self.tweets_collected)}/{count}] Tweet toplandı: {tweet.date_str}{article_tag}{show_more_tag}")

                if new_tweets_found:
                    no_new_tweets_count = 0
                else:
                    no_new_tweets_count += 1

                if no_new_tweets_count >= max_no_new_tweets:
                    print("Daha fazla tweet bulunamadı.")
                    break

                # Aşağı kaydır
                self._scroll_down()

        except KeyboardInterrupt:
            print(f"\n\nDurduruldu! {len(self.tweets_collected)} tweet toplandı.")
            raise  # Ana programa ilet

        # Scroll bitti, şimdi show more olan tweetlerin tam metnini al
        self._process_show_more_tweets()

        print(f"Toplam {len(self.tweets_collected)} tweet toplandı.")
        return self.tweets_collected

    def _process_show_more_tweets(self):
        """Show more ve article olan tweetlerin tam metnini al (scroll bittikten sonra)"""
        # Show more tweetler
        show_more_tweets = [t for t in self.tweets_collected if t.needs_full_text]
        # Article tweetler
        article_tweets = [t for t in self.tweets_collected if t.has_article]

        total = len(show_more_tweets) + len(article_tweets)
        if total == 0:
            return

        print(f"\n{total} uzun içerik alınıyor ({len(show_more_tweets)} show more, {len(article_tweets)} article)...")
        current = 0

        # Show more tweetleri işle
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

        # Article tweetleri işle
        for tweet in article_tweets:
            current += 1
            try:
                print(f"  [{current}/{total}] Article içeriği alınıyor: {tweet.tweet_url[:50]}...")
                article_content = self._get_article_content(tweet.tweet_url)
                if article_content:
                    content_preview = article_content[:100].replace('\n', ' ')
                    print(f"    ✓ {len(article_content)} karakter alındı: {content_preview}...")
                    # Article içeriğini tweet metnine ekle
                    if tweet.text:
                        tweet.text = tweet.text + "\n\n--- ARTICLE İÇERİĞİ ---\n\n" + article_content
                    else:
                        tweet.text = article_content
                    tweet.has_article = False
                else:
                    print(f"    ✗ Article içeriği alınamadı!")
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
                    tweet = self._parse_tweet_element(article)
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
