"""
X (Twitter) Tweet Scraper - Ana Uygulama
Kullanım: python main.py
"""

import sys
import getpass
from datetime import datetime, timedelta

from chrome_auth import default_browser_profile, open_chrome_for_x_login
from scraper import XScraper
from terminal_ui import TerminalUI
from document_generator import (
    BASE_OUTPUT_DIR,
    create_csv_document,
    create_word_document,
    create_json_document,
    create_markdown_document,
)
from diagnostics import ScrapeRunLog, record_event, save_run_log


def save_cli_run_log(run_log: ScrapeRunLog, status: str = "completed") -> str:
    """Persist the CLI run log and print the path for the user."""
    run_log.mark_completed(status)
    path = save_run_log(run_log, BASE_OUTPUT_DIR)
    print(f"Run log saved: {path}")
    if run_log.failure_reason:
        print(f"Failure reason: {run_log.failure_reason}")
    return path


def run_diagnostics_cli(url: str | None = None) -> int:
    """Open a browser, navigate to a user-provided URL, and check selectors."""
    run_log = ScrapeRunLog(target="diagnostics", scrape_type="diagnostics", mode="selector_check")
    scraper = None
    try:
        print("=" * 60)
        print("   X Selector Diagnostics")
        print("=" * 60)
        print("A browser will open and check core X selectors on the selected page.")
        if url is None:
            url = input("URL to inspect (blank for https://x.com/home): ").strip() or "https://x.com/home"

        from x_scraper_cli import CliValidationError, validate_diagnostics_url

        try:
            url = validate_diagnostics_url(url)
        except CliValidationError as exc:
            record_event(
                run_log,
                "selector_diagnostics",
                "error",
                f"Invalid diagnostics URL: {exc}",
                reason="invalid_input",
            )
            save_cli_run_log(run_log, "failed")
            print(f"Diagnostics input error: {exc}")
            return 2

        scraper = XScraper(headless=False, run_log=run_log)
        scraper.start()
        scraper.driver.get(url)
        input("Press ENTER after the page has loaded or sign-in is complete...")
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
        print(f"Diagnostics error: {e}")
        return 1
    finally:
        if scraper:
            scraper.stop()


def _legacy_get_user_input():
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
    print("4. CSV (.csv)")
    format_choice = input("Seçiminiz (1/2/3/4): ").strip()

    if format_choice == "2":
        output_format = "md"
        ext = ".md"
    elif format_choice == "3":
        output_format = "docx"
        ext = ".docx"
    elif format_choice == "4":
        output_format = "csv"
        ext = ".csv"
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


def get_user_input():
    """Collect the initial interactive scrape configuration in English."""
    ui = TerminalUI()
    ui.banner()
    ui.section("Account session", 1)
    ui.choice(1, "Sign in with Google or Apple in normal Chrome", "recommended")
    ui.choice(2, "Sign in with an X username and password")
    login_method = input("Select (1/2): ").strip()

    x_username = ""
    x_password = ""
    manual_login = False
    browser_profile = None
    prepare_browser_profile = False
    if login_method == "2":
        ui.section("X account credentials")
        x_username = input("X username or email: ").strip()
        x_password = getpass.getpass("X password: ")
    else:
        manual_login = True
        browser_profile = default_browser_profile()
        prepare_browser_profile = True
        ui.status("info", "A normal Chrome window will open so you can sign in safely.")

    ui.section("Source", 2)
    ui.choice(1, "Profile posts", "archive posts from a public account")
    ui.choice(2, "Bookmarks", "archive bookmarks from your own account")
    scrape_type_choice = input("Select (1/2): ").strip()
    if scrape_type_choice == "2":
        scrape_type = "bookmarks"
        target_username = "bookmarks"
    else:
        scrape_type = "profile"
        ui.section("Target profile", 3)
        target_username = input("Handle (without @): ").strip().lstrip("@")

    ui.section("Collection range", 4)
    ui.choice(1, "Post count")
    ui.choice(2, "Last N days")
    ui.choice(3, "Date range")
    mode = input("Select (1/2/3): ").strip()
    if mode == "1":
        mode_config = {"mode": "count", "count": int(input("Posts to collect: ").strip())}
    elif mode == "2":
        mode_config = {"mode": "days", "days": int(input("Days to collect: ").strip())}
    elif mode == "3":
        print("Date format: DD.MM.YYYY (for example 01.01.2024)")
        start_date = datetime.strptime(input("Start date: ").strip(), "%d.%m.%Y")
        end_date = datetime.strptime(input("End date: ").strip(), "%d.%m.%Y")
        mode_config = {
            "mode": "date_range",
            "start": start_date,
            "end": end_date.replace(hour=23, minute=59, second=59),
        }
    else:
        ui.status("warning", "Invalid choice; using 50 posts.")
        mode_config = {"mode": "count", "count": 50}

    ui.section("Export", 5)
    ui.choice(1, "JSON", "recommended for data workflows")
    ui.choice(2, "Markdown (.md)")
    ui.choice(3, "Word (.docx)")
    ui.choice(4, "CSV (.csv)")
    format_choice = input("Select (1/2/3/4): ").strip()
    output_format, extension = {
        "2": ("md", ".md"),
        "3": ("docx", ".docx"),
        "4": ("csv", ".csv"),
    }.get(format_choice, ("json", ".json"))
    default_filename = f"{target_username}_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    output_file = input(f"Filename (blank for {default_filename}): ").strip() or default_filename

    return {
        "x_username": x_username,
        "x_password": x_password,
        "target_username": target_username,
        "mode_config": mode_config,
        "output_file": output_file,
        "output_format": output_format,
        "manual_login": manual_login,
        "scrape_type": scrape_type,
        "browser_profile": browser_profile,
        "prepare_browser_profile": prepare_browser_profile,
    }


def _legacy_get_scrape_config():
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
    print("4. CSV (.csv)")
    format_choice = input("Seçiminiz (1/2/3/4): ").strip()

    if format_choice == "2":
        output_format = "md"
        ext = ".md"
    elif format_choice == "3":
        output_format = "docx"
        ext = ".docx"
    elif format_choice == "4":
        output_format = "csv"
        ext = ".csv"
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


def _legacy_ask_continue():
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


def get_scrape_config():
    """Collect the next scrape configuration without asking for credentials."""
    ui = TerminalUI()
    ui.section("Source", 1)
    ui.choice(1, "Profile posts", "archive posts from a public account")
    ui.choice(2, "Bookmarks", "archive bookmarks from your own account")
    scrape_type_choice = input("Select (1/2): ").strip()
    if scrape_type_choice == "2":
        scrape_type = "bookmarks"
        target_username = "bookmarks"
    else:
        scrape_type = "profile"
        ui.section("Target profile", 2)
        target_username = input("Handle (without @): ").strip().lstrip("@")

    ui.section("Collection range", 3)
    ui.choice(1, "Post count")
    ui.choice(2, "Last N days")
    ui.choice(3, "Date range")
    mode = input("Select (1/2/3): ").strip()
    if mode == "1":
        mode_config = {"mode": "count", "count": int(input("Posts to collect: ").strip())}
    elif mode == "2":
        mode_config = {"mode": "days", "days": int(input("Days to collect: ").strip())}
    elif mode == "3":
        print("Date format: DD.MM.YYYY (for example 01.01.2024)")
        start_date = datetime.strptime(input("Start date: ").strip(), "%d.%m.%Y")
        end_date = datetime.strptime(input("End date: ").strip(), "%d.%m.%Y")
        mode_config = {
            "mode": "date_range",
            "start": start_date,
            "end": end_date.replace(hour=23, minute=59, second=59),
        }
    else:
        ui.status("warning", "Invalid choice; using 50 posts.")
        mode_config = {"mode": "count", "count": 50}

    ui.section("Export", 4)
    ui.choice(1, "JSON", "recommended for data workflows")
    ui.choice(2, "Markdown (.md)")
    ui.choice(3, "Word (.docx)")
    ui.choice(4, "CSV (.csv)")
    format_choice = input("Select (1/2/3/4): ").strip()
    output_format, extension = {
        "2": ("md", ".md"),
        "3": ("docx", ".docx"),
        "4": ("csv", ".csv"),
    }.get(format_choice, ("json", ".json"))
    default_filename = f"{target_username}_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    output_file = input(f"Filename (blank for {default_filename}): ").strip() or default_filename
    return {
        "target_username": target_username,
        "mode_config": mode_config,
        "output_file": output_file,
        "output_format": output_format,
        "scrape_type": scrape_type,
    }


def ask_continue():
    """Ask whether to run another archive with the current authenticated session."""
    while True:
        answer = input("Archive another account? (Y/N): ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter Y for yes or N for no.")


def run_interactive():
    """Run the existing prompt-driven workflow."""

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
        print("Starting archive...")
        print("=" * 60)
        print()

        # Scraper'ı başlat
        if config["prepare_browser_profile"]:
            if open_chrome_for_x_login(config["browser_profile"]) != 0:
                record_event(
                    run_log,
                    "manual_login",
                    "error",
                    "Normal Chrome session setup failed",
                    reason="normal_chrome_login_failed",
                )
                save_cli_run_log(run_log, "failed")
                return 1

        scraper = XScraper(
            headless=False,
            run_log=run_log,
            browser_profile=config["browser_profile"],
        )

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
                print("Sign-in failed. Exiting.")
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
                print("Sign-in failed. Exiting.")
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
                    print("Bookmarks page could not be opened.")
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
                    print("Profile page could not be opened.")
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
                print("No posts were collected.")
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
                    print("Writing JSON export...")
                    output_path = create_json_document(
                        tweets,
                        config["output_file"],
                        config["target_username"],
                        scrape_type=scrape_type,
                    )
                elif output_format == "md":
                    print("Writing Markdown export...")
                    output_path = create_markdown_document(
                        tweets, config["output_file"], config["target_username"]
                    )
                elif output_format == "csv":
                    print("Writing CSV export...")
                    output_path = create_csv_document(
                        tweets, config["output_file"], config["target_username"]
                    )
                else:
                    print("Writing Word export...")
                    output_path = create_word_document(
                        tweets, config["output_file"], config["target_username"]
                    )

                print()
                print("=" * 60)
                partial_count = (
                    mode.get("mode") == "count"
                    and len(tweets) < mode.get("count", len(tweets))
                )
                if partial_count:
                    print("PARTIALLY COMPLETED")
                    print(f"Requested: {mode['count']} posts; collected: {len(tweets)} posts.")
                    print("The timeline did not load more posts; see the run log for details.")
                    record_event(
                        run_log,
                        "timeline_loading",
                        "warning",
                        "Count scrape ended before requested tweet count",
                        collected=len(tweets),
                        target=mode["count"],
                    )
                else:
                    print("COMPLETED")
                print(f"Collected {len(tweets)} posts.")
                print(f"File: {output_path}")
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
                save_cli_run_log(run_log, "partial" if partial_count else "completed")

            # Devam etmek istiyor mu?
            if ask_continue():
                config.update(get_scrape_config())
                run_log = None
            else:
                print("\nExiting.")
                break

        return 0

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("CANCELLED - Ctrl+C detected")
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
                print(f"\nSaving {len(tweets)} collected posts...")
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
                elif output_format == "csv":
                    output_file = f"{base_name}_PARTIAL.csv"
                    output_path = create_csv_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_PARTIAL.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])

                print(f"\nPartial results saved: {output_path}")
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
                print(f"\nSave error: {save_err}")
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
            print("\nNo collected posts to save.")
            if run_log:
                save_cli_run_log(run_log, "cancelled")

        return 1

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

        if scraper and hasattr(scraper, 'tweets_collected') and scraper.tweets_collected and not tweets:
            tweets = scraper.tweets_collected

        error_text = str(e).lower()
        error_reason = (
            "browser_window_closed"
            if "no such window" in error_text or "web view not found" in error_text
            else "unknown_error"
        )

        # Hata durumunda da kaydetmeyi dene
        if tweets and config:
            print(f"\nSaving {len(tweets)} collected posts despite the error...")
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
                elif output_format == "csv":
                    output_file = f"{base_name}_ERROR.csv"
                    output_path = create_csv_document(tweets, output_file, config["target_username"])
                else:
                    output_file = f"{base_name}_ERROR.docx"
                    output_path = create_word_document(tweets, output_file, config["target_username"])
                print(f"Saved: {output_path}")
                if run_log:
                    record_event(
                        run_log,
                        "export_saving",
                        "warning",
                        "Error export saved after exception",
                        reason=error_reason,
                        path=output_path,
                        total_tweets=len(tweets),
                    )
                    save_cli_run_log(run_log, "partial")
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
                reason=error_reason,
            )
            save_cli_run_log(run_log, "failed")

        return 1

    finally:
        if scraper:
            scraper.stop()


def main(argv=None):
    """Run the command interface or the backwards-compatible interactive wizard."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return run_interactive()

    import x_scraper_cli

    return x_scraper_cli.run_cli(args, diagnostics_runner=run_diagnostics_cli)


if __name__ == "__main__":
    sys.exit(main())
