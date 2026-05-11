"""
X (Twitter) Tweet Scraper - Ana Uygulama
Kullanım: python main.py
"""

import sys
import getpass
from datetime import datetime, timedelta

from scraper import XScraper
from document_generator import create_word_document, create_json_document, create_markdown_document


def get_user_input():
    """Kullanıcıdan gerekli bilgileri al"""
    print("=" * 60)
    print("   X (Twitter) Tweet Scraper")
    print("   Sadece Posts - Replies Hariç")
    print("=" * 60)
    print()

    # Login yöntemi seçimi
    print("[1] Giriş Yöntemi")
    print("-" * 40)
    print("1. Manuel giriş (Google/Apple ile giriş için - ÖNERİLEN)")
    print("2. Kullanıcı adı + şifre ile otomatik giriş")
    login_method = input("Seçiminiz (1/2): ").strip()
    print()

    x_username = ""
    x_password = ""
    manual_login = False

    if login_method == "2":
        print("[1b] X Hesap Bilgileri")
        print("-" * 40)
        x_username = input("X Kullanıcı adı veya email: ").strip()
        x_password = getpass.getpass("X Şifre: ")
    else:
        manual_login = True
        print("Manuel giriş seçildi - Browser'da kendiniz giriş yapacaksınız.")
    print()

    # Scrape türü seçimi
    print("[2] Scrape Türü")
    print("-" * 40)
    print("1. Profil tweetleri (bir kullanıcının postları)")
    print("2. Bookmarks (kendi kayıtlı tweetleriniz)")
    scrape_type_choice = input("Seçiminiz (1/2): ").strip()
    print()

    if scrape_type_choice == "2":
        scrape_type = "bookmarks"
        target_username = "bookmarks"
    else:
        scrape_type = "profile"
        # Hedef profil
        print("[3] Scrape Edilecek Hesap")
        print("-" * 40)
        target_username = input("Hedef hesap kullanıcı adı (@olmadan): ").strip()
        if target_username.startswith("@"):
            target_username = target_username[1:]
        print()

    # Scraping modu
    print("[4] Scraping Modu")
    print("-" * 40)
    print("1. Belirli sayıda tweet")
    print("2. Son X gün içindeki tweetler")
    print("3. Tarih aralığı")
    mode = input("Seçiminiz (1/2/3): ").strip()
    print()

    mode_config = {}

    if mode == "1":
        count = int(input("Kaç tweet toplanacak? ").strip())
        mode_config = {"mode": "count", "count": count}

    elif mode == "2":
        days = int(input("Son kaç gün? ").strip())
        mode_config = {"mode": "days", "days": days}

    elif mode == "3":
        print("Tarih formatı: GG.AA.YYYY (örn: 01.01.2024)")
        start_str = input("Başlangıç tarihi (eski): ").strip()
        end_str = input("Bitiş tarihi (yeni): ").strip()

        start_date = datetime.strptime(start_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_str, "%d.%m.%Y")
        end_date = end_date.replace(hour=23, minute=59, second=59)

        mode_config = {"mode": "date_range", "start": start_date, "end": end_date}

    else:
        print("Geçersiz seçim. Varsayılan: 50 tweet")
        mode_config = {"mode": "count", "count": 50}

    print()

    # Çıktı formatı
    print("[5] Çıktı Formatı")
    print("-" * 40)
    print("1. JSON (MCP-ready, önerilen)")
    print("2. Markdown (.md)")
    print("3. Word (.docx)")
    format_choice = input("Seçiminiz (1/2/3): ").strip()

    if format_choice == "2":
        output_format = "md"
        ext = ".md"
    elif format_choice == "3":
        output_format = "docx"
        ext = ".docx"
    else:
        output_format = "json"
        ext = ".json"

    default_filename = f"{target_username}_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    output_file = input(f"Dosya adı (boş bırakın: {default_filename}): ").strip()
    if not output_file:
        output_file = default_filename

    print()

    return {
        "x_username": x_username,
        "x_password": x_password,
        "target_username": target_username,
        "mode_config": mode_config,
        "output_file": output_file,
        "output_format": output_format,
        "manual_login": manual_login,
        "scrape_type": scrape_type,
    }


def get_scrape_config():
    """Sadece scrape edilecek hesap ve mod bilgilerini al (login hariç)"""
    print()

    # Scrape türü seçimi
    print("[1] Scrape Türü")
    print("-" * 40)
    print("1. Profil tweetleri (bir kullanıcının postları)")
    print("2. Bookmarks (kendi kayıtlı tweetleriniz)")
    scrape_type_choice = input("Seçiminiz (1/2): ").strip()
    print()

    if scrape_type_choice == "2":
        scrape_type = "bookmarks"
        target_username = "bookmarks"
    else:
        scrape_type = "profile"
        # Hedef profil
        print("[2] Scrape Edilecek Hesap")
        print("-" * 40)
        target_username = input("Hedef hesap kullanıcı adı (@olmadan): ").strip()
        if target_username.startswith("@"):
            target_username = target_username[1:]
        print()

    # Scraping modu
    print("[3] Scraping Modu")
    print("-" * 40)
    print("1. Belirli sayıda tweet")
    print("2. Son X gün içindeki tweetler")
    print("3. Tarih aralığı")
    mode = input("Seçiminiz (1/2/3): ").strip()
    print()

    mode_config = {}

    if mode == "1":
        count = int(input("Kaç tweet toplanacak? ").strip())
        mode_config = {"mode": "count", "count": count}

    elif mode == "2":
        days = int(input("Son kaç gün? ").strip())
        mode_config = {"mode": "days", "days": days}

    elif mode == "3":
        print("Tarih formatı: GG.AA.YYYY (örn: 01.01.2024)")
        start_str = input("Başlangıç tarihi (eski): ").strip()
        end_str = input("Bitiş tarihi (yeni): ").strip()

        start_date = datetime.strptime(start_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_str, "%d.%m.%Y")
        end_date = end_date.replace(hour=23, minute=59, second=59)

        mode_config = {"mode": "date_range", "start": start_date, "end": end_date}

    else:
        print("Geçersiz seçim. Varsayılan: 50 tweet")
        mode_config = {"mode": "count", "count": 50}

    print()

    # Çıktı formatı
    print("[4] Çıktı Formatı")
    print("-" * 40)
    print("1. JSON (MCP-ready, önerilen)")
    print("2. Markdown (.md)")
    print("3. Word (.docx)")
    format_choice = input("Seçiminiz (1/2/3): ").strip()

    if format_choice == "2":
        output_format = "md"
        ext = ".md"
    elif format_choice == "3":
        output_format = "docx"
        ext = ".docx"
    else:
        output_format = "json"
        ext = ".json"

    default_filename = f"{target_username}_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    output_file = input(f"Dosya adı (boş bırakın: {default_filename}): ").strip()
    if not output_file:
        output_file = default_filename

    print()

    return {
        "target_username": target_username,
        "mode_config": mode_config,
        "output_file": output_file,
        "output_format": output_format,
        "scrape_type": scrape_type,
    }


def ask_continue():
    """Kullanıcıya devam etmek isteyip istemediğini sor"""
    print()
    print("=" * 60)
    while True:
        answer = input("Başka bir hesap scrapelemek istiyor musunuz? (E/H): ").strip().lower()
        if answer in ['e', 'evet', 'y', 'yes']:
            return True
        elif answer in ['h', 'hayır', 'n', 'no']:
            return False
        else:
            print("Lütfen 'E' (Evet) veya 'H' (Hayır) girin.")


def main():
    """Ana uygulama"""
    scraper = None
    tweets = []
    config = None

    try:
        # İlk kullanıcı bilgilerini al (login dahil)
        config = get_user_input()

        print("=" * 60)
        print("Scraping başlıyor...")
        print("=" * 60)
        print()

        # Scraper'ı başlat
        scraper = XScraper(headless=False)  # Browser görünür olsun

        scraper.start()

        # Login (sadece bir kez)
        if config["manual_login"]:
            if not scraper.manual_login():
                print("Giriş başarısız! Program sonlandırılıyor.")
                return 1
        else:
            if not scraper.login(config["x_username"], config["x_password"]):
                print("Giriş başarısız! Program sonlandırılıyor.")
                return 1

        # Ana scraping döngüsü
        while True:
            # Scrape türüne göre navigasyon ve tweet toplama
            scrape_type = config.get("scrape_type", "profile")
            mode = config["mode_config"]
            tweets = []

            # Önceki toplamları temizle
            scraper.collected_tweet_ids = set()

            if scrape_type == "bookmarks":
                # Bookmarks sayfasına git
                if not scraper.navigate_to_bookmarks():
                    print("Bookmarks sayfasına gidilemedi!")
                    if ask_continue():
                        config.update(get_scrape_config())
                        continue
                    else:
                        break

                # Bookmark'ları topla
                if mode["mode"] == "count":
                    tweets = scraper.scrape_bookmarks(count=mode["count"])
                else:
                    # days ve date_range için tüm bookmark'ları çek, sonra filtrele
                    tweets = scraper.scrape_bookmarks(get_all=True)
                    if mode["mode"] == "days":
                        cutoff = datetime.now() - timedelta(days=mode["days"])
                        tweets = [t for t in tweets if t.date and t.date >= cutoff]
                    elif mode["mode"] == "date_range":
                        tweets = [t for t in tweets if t.date and mode["start"] <= t.date <= mode["end"]]
            else:
                # Profile git
                if not scraper.navigate_to_profile(config["target_username"]):
                    print("Profile gidilemedi!")
                    if ask_continue():
                        config.update(get_scrape_config())
                        continue
                    else:
                        break

                # Tweet topla
                if mode["mode"] == "count":
                    tweets = scraper.scrape_by_count(mode["count"])

                elif mode["mode"] == "days":
                    tweets = scraper.scrape_last_n_days(mode["days"])

                elif mode["mode"] == "date_range":
                    tweets = scraper.scrape_by_date(mode["start"], mode["end"])

            if not tweets:
                print("Hiç tweet toplanamadı!")
            else:
                # Tarihe göre sırala (güncel'den eskiye)
                tweets.sort(key=lambda t: t.date if t.date else datetime.min, reverse=True)

                # Çıktı dosyası oluştur
                print()
                output_format = config.get("output_format", "json")

                if output_format == "json":
                    print("JSON dosyası oluşturuluyor...")
                    output_path = create_json_document(
                        tweets, config["output_file"], config["target_username"]
                    )
                elif output_format == "md":
                    print("Markdown dosyası oluşturuluyor...")
                    output_path = create_markdown_document(
                        tweets, config["output_file"], config["target_username"]
                    )
                else:
                    print("Word document oluşturuluyor...")
                    output_path = create_word_document(
                        tweets, config["output_file"], config["target_username"]
                    )

                print()
                print("=" * 60)
                print("TAMAMLANDI!")
                print(f"Toplam {len(tweets)} tweet toplandı.")
                print(f"Dosya: {output_path}")
                print("=" * 60)

            # Devam etmek istiyor mu?
            if ask_continue():
                config.update(get_scrape_config())
            else:
                print("\nProgram sonlandırılıyor...")
                break

        return 0

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("İPTAL EDİLDİ - Ctrl+C algılandı")
        print("=" * 60)

        # ÖNCELİKLE tweetleri al (browser kapatılmadan önce)
        if scraper and hasattr(scraper, 'tweets_collected') and scraper.tweets_collected:
            tweets = scraper.tweets_collected

        # Şimdi browser'ı kapat
        if scraper:
            try:
                scraper.stop()
                scraper = None
            except:
                pass

        # Toplanan tweetleri kaydet
        if tweets and config:
            try:
                print(f"\n{len(tweets)} tweet toplandı, kaydediliyor...")
                tweets.sort(key=lambda t: t.date if t.date else datetime.min, reverse=True)

                # Dosya adını güncelle
                output_format = config.get("output_format", "json")
                base_name = config["output_file"].rsplit(".", 1)[0]

                if output_format == "json":
                    output_file = f"{base_name}_PARTIAL.json"
                    output_path = create_json_document(tweets, output_file, config["target_username"])
                elif output_format == "md":
                    output_file = f"{base_name}_PARTIAL.md"
                    output_path = create_markdown_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_PARTIAL.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])

                print(f"\nKısmi sonuçlar kaydedildi: {output_path}")
            except Exception as save_err:
                print(f"\nKaydetme hatası: {save_err}")
        else:
            print("\nKaydedilecek tweet bulunamadı.")

        return 1

    except Exception as e:
        print(f"\nHata oluştu: {e}")
        import traceback
        traceback.print_exc()

        # Hata durumunda da kaydetmeyi dene
        if tweets and config:
            print(f"\nHataya rağmen {len(tweets)} tweet kaydediliyor...")
            output_format = config.get("output_format", "json")
            base_name = config["output_file"].rsplit(".", 1)[0]
            try:
                if output_format == "json":
                    output_file = f"{base_name}_ERROR.json"
                    output_path = create_json_document(tweets, output_file, config["target_username"])
                elif output_format == "md":
                    output_file = f"{base_name}_ERROR.md"
                    output_path = create_markdown_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_ERROR.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])
                print(f"Kaydedildi: {output_path}")
            except:
                pass

        return 1

    finally:
        if scraper:
            scraper.stop()


if __name__ == "__main__":
    sys.exit(main())
