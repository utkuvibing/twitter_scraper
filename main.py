"""
X (Twitter) Tweet Scraper - Ana Uygulama
Kullanım: python main.py
"""

import sys
import getpass
from datetime import datetime, timedelta

from scraper import XScraper
from document_generator import (
    BASE_OUTPUT_DIR,
    create_word_document,
    create_json_document,
    create_markdown_document,
)
from diagnostics import ScrapeRunLog, record_event, save_run_log


def save_cli_run_log(run_log: ScrapeRunLog, status: str = "completed") -> str:
    """Persist the CLI run log and print the path for the user."""
    run_log.mark_completed(status)
    path = save_run_log(run_log, BASE_OUTPUT_DIR)
    print(f"Run log kaydedildi: {path}")
    if run_log.failure_reason:
        print(f"Failure reason: {run_log.failure_reason}")
    return path


def run_diagnostics_cli() -> int:
    """Open a browser, navigate to a user-provided URL, and check selectors."""
    run_log = ScrapeRunLog(target="diagnostics", scrape_type="diagnostics", mode="selector_check")
    scraper = XScraper(headless=False, run_log=run_log)
    try:
        print("=" * 60)
        print("   X Selector Diagnostics")
        print("=" * 60)
        print("Browser açılacak ve seçilen sayfadaki temel X selector'ları kontrol edilecek.")
        url = input("Kontrol edilecek URL (boş: https://x.com/home): ").strip() or "https://x.com/home"

        scraper.start()
        scraper.driver.get(url)
        input("Sayfa yüklendikten/giriş tamamlandıktan sonra ENTER'a basın...")
        diagnostics = scraper.run_selector_diagnostics()

        print("\nSelector diagnostics:")
        for check in diagnostics["checks"]:
            marker = "OK" if check["ok"] else "MISS"
            print(f"  [{marker}] {check['name']} ({check['stage']}): {check['count']}")

        status = "completed" if diagnostics["ok"] else "failed"
        if not diagnostics["ok"]:
            record_event(
                run_log,
                "selector_diagnostics",
                "error",
                "Required selector checks failed",
                reason="timeline_empty",
                missing_required=diagnostics["missing_required"],
            )
        save_cli_run_log(run_log, status)
        return 0 if diagnostics["ok"] else 2
    except Exception as e:
        record_event(
            run_log,
            "selector_diagnostics",
            "error",
            f"Diagnostics failed: {e}",
            reason="unknown_error",
        )
        save_cli_run_log(run_log, "failed")
        print(f"Diagnostics hatası: {e}")
        return 1
    finally:
        scraper.stop()


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
    if "--diagnostics" in sys.argv:
        return run_diagnostics_cli()

    scraper = None
    tweets = []
    config = None
    run_log = None

    try:
        # İlk kullanıcı bilgilerini al (login dahil)
        config = get_user_input()
        run_log = ScrapeRunLog(
            target=config["target_username"],
            scrape_type=config.get("scrape_type", "profile"),
            mode=config["mode_config"].get("mode"),
        )

        print("=" * 60)
        print("Scraping başlıyor...")
        print("=" * 60)
        print()

        # Scraper'ı başlat
        scraper = XScraper(headless=False, run_log=run_log)  # Browser görünür olsun

        scraper.start()

        # Login (sadece bir kez)
        if config["manual_login"]:
            if not scraper.manual_login():
                record_event(
                    run_log,
                    "manual_login",
                    "error",
                    "Manual login did not complete",
                    reason="manual_login_timeout",
                )
                save_cli_run_log(run_log, "failed")
                print("Giriş başarısız! Program sonlandırılıyor.")
                return 1
        else:
            if not scraper.login(config["x_username"], config["x_password"]):
                record_event(
                    run_log,
                    "login",
                    "error",
                    "Automatic login did not complete",
                    reason="login_failed",
                )
                save_cli_run_log(run_log, "failed")
                print("Giriş başarısız! Program sonlandırılıyor.")
                return 1

        # Ana scraping döngüsü
        while True:
            # Scrape türüne göre navigasyon ve tweet toplama
            scrape_type = config.get("scrape_type", "profile")
            mode = config["mode_config"]
            tweets = []
            if not run_log or run_log.status != "running":
                run_log = ScrapeRunLog(
                    target=config["target_username"],
                    scrape_type=scrape_type,
                    mode=mode.get("mode"),
                )
                scraper.run_log = run_log

            # Önceki toplamları temizle
            scraper.collected_tweet_ids = set()

            if scrape_type == "bookmarks":
                # Bookmarks sayfasına git
                if not scraper.navigate_to_bookmarks():
                    print("Bookmarks sayfasına gidilemedi!")
                    save_cli_run_log(run_log, "failed")
                    if ask_continue():
                        config.update(get_scrape_config())
                        run_log = None
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
                    save_cli_run_log(run_log, "failed")
                    if ask_continue():
                        config.update(get_scrape_config())
                        run_log = None
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
                record_event(
                    run_log,
                    "timeline_loading",
                    "error",
                    "Scrape completed without collected tweets",
                    reason="timeline_empty",
                )
                save_cli_run_log(run_log, "failed")
            else:
                # Tarihe göre sırala (güncel'den eskiye)
                tweets.sort(key=lambda t: t.date if t.date else datetime.min, reverse=True)

                # Çıktı dosyası oluştur
                print()
                output_format = config.get("output_format", "json")

                if output_format == "json":
                    print("JSON dosyası oluşturuluyor...")
                    output_path = create_json_document(
                        tweets,
                        config["output_file"],
                        config["target_username"],
                        scrape_type=scrape_type,
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
                record_event(
                    run_log,
                    "export_saving",
                    "info",
                    "Export saved",
                    path=output_path,
                    format=output_format,
                    total_tweets=len(tweets),
                )
                save_cli_run_log(run_log, "completed")

            # Devam etmek istiyor mu?
            if ask_continue():
                config.update(get_scrape_config())
                run_log = None
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
                    output_path = create_json_document(
                        tweets,
                        output_file,
                        config["target_username"],
                        scrape_type=config.get("scrape_type", "profile"),
                    )
                elif output_format == "md":
                    output_file = f"{base_name}_PARTIAL.md"
                    output_path = create_markdown_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_PARTIAL.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])

                print(f"\nKısmi sonuçlar kaydedildi: {output_path}")
                if run_log:
                    record_event(
                        run_log,
                        "export_saving",
                        "warning",
                        "Partial export saved after interrupt",
                        path=output_path,
                        total_tweets=len(tweets),
                    )
                    save_cli_run_log(run_log, "cancelled")
            except Exception as save_err:
                print(f"\nKaydetme hatası: {save_err}")
                if run_log:
                    record_event(
                        run_log,
                        "export_saving",
                        "error",
                        f"Partial export failed after interrupt: {save_err}",
                        reason="export_failed",
                    )
                    save_cli_run_log(run_log, "failed")
        else:
            print("\nKaydedilecek tweet bulunamadı.")
            if run_log:
                save_cli_run_log(run_log, "cancelled")

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
                    output_path = create_json_document(
                        tweets,
                        output_file,
                        config["target_username"],
                        scrape_type=config.get("scrape_type", "profile"),
                    )
                elif output_format == "md":
                    output_file = f"{base_name}_ERROR.md"
                    output_path = create_markdown_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_ERROR.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])
                print(f"Kaydedildi: {output_path}")
                if run_log:
                    record_event(
                        run_log,
                        "export_saving",
                        "warning",
                        "Error export saved after exception",
                        path=output_path,
                        total_tweets=len(tweets),
                    )
                    save_cli_run_log(run_log, "failed")
            except:
                if run_log:
                    record_event(
                        run_log,
                        "export_saving",
                        "error",
                        "Error export failed after exception",
                        reason="export_failed",
                    )
                    save_cli_run_log(run_log, "failed")
                pass
        elif run_log:
            record_event(
                run_log,
                "unknown_error",
                "error",
                f"Unhandled exception: {e}",
                reason="unknown_error",
            )
            save_cli_run_log(run_log, "failed")

        return 1

    finally:
        if scraper:
            scraper.stop()


if __name__ == "__main__":
    sys.exit(main())
