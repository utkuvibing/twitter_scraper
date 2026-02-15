"""
JSON stdin/stdout command dispatcher for the Twitter/X Scraper sidecar.
Receives commands via stdin JSON lines, dispatches to scraper/export/analyze,
and emits structured JSON responses via stdout.
"""

import sys
import json
import uuid
import threading
import traceback
from datetime import datetime, timedelta
from typing import Optional

from scraper import XScraper, Tweet
from session_manager import SessionManager
from analytics import compute_analytics

# Import document_generator from parent directory
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from document_generator import (
    create_json_document,
    create_markdown_document,
    create_word_document,
)


class ScraperService:
    """Main service that handles JSON stdio communication"""

    def __init__(self):
        self.scraper: Optional[XScraper] = None
        self.current_scrape_id: Optional[str] = None
        self.current_tweets: list = []
        self._scrape_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def emit(self, msg_type: str, **kwargs):
        """Send a JSON message to stdout"""
        message = {"type": msg_type, **kwargs}
        try:
            line = json.dumps(message, ensure_ascii=False, default=str)
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        except Exception as e:
            # Log serialization errors to stderr so they're visible
            print(f"[EMIT ERROR] type={msg_type}: {e}", file=sys.stderr, flush=True)

    def read_command(self) -> Optional[dict]:
        """Read a JSON command from stdin"""
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError as e:
            self.emit("error", message=f"Invalid JSON: {e}")
            return {"command": "_invalid"}
        except Exception:
            return None

    def handle_login(self, cmd: dict):
        """Handle login command"""
        try:
            if not self.scraper:
                self.scraper = XScraper(
                    headless=False,
                    emit=self.emit,
                    chrome_path=cmd.get("chrome_path"),
                    scroll_pause_min=cmd.get("scroll_pause_min"),
                    scroll_pause_max=cmd.get("scroll_pause_max"),
                )
                self.scraper.start()

            # Try to restore session first
            if self.scraper.try_restore_session():
                self.emit(
                    "login_status",
                    success=True,
                    message="Session restored from saved cookies",
                )
                return

            method = cmd.get("method", "manual")
            if method == "automatic":
                username = cmd.get("username", "")
                password = cmd.get("password", "")
                if not username or not password:
                    self.emit(
                        "error",
                        message="Username and password required for automatic login",
                    )
                    return
                self.scraper.login(username, password)
            else:
                self.scraper.manual_login()

        except Exception as e:
            self.emit("error", message=f"Login failed: {e}")

    def handle_scrape(self, cmd: dict):
        """Handle scrape command - runs in a separate thread"""

        def _do_scrape():
            try:
                if not self.scraper or not self.scraper.driver:
                    self.emit("error", message="Not logged in. Please login first.")
                    return

                scrape_type = cmd.get("type", "profile")
                target = cmd.get("target", "")
                mode = cmd.get("mode", "count")

                # Generate scrape ID
                self.current_scrape_id = str(uuid.uuid4())[:8]
                self.scraper.collected_tweet_ids = set()
                self.scraper._cancelled = False
                self.scraper._paused = False
                self.scraper._pause_event.set()

                # Navigate
                if scrape_type == "bookmarks":
                    if not self.scraper.navigate_to_bookmarks():
                        self.emit("error", message="Could not navigate to bookmarks")
                        return
                else:
                    if not target:
                        self.emit("error", message="Target username is required")
                        return
                    if not self.scraper.navigate_to_profile(target):
                        self.emit("error", message=f"Could not navigate to @{target}")
                        return

                # Scrape based on mode
                tweets = []
                if scrape_type == "bookmarks":
                    if mode == "all":
                        tweets = self.scraper.scrape_bookmarks(get_all=True)
                    else:
                        count = cmd.get("count", 50)
                        tweets = self.scraper.scrape_bookmarks(count=count)
                elif mode == "count":
                    count = cmd.get("count", 50)
                    tweets = self.scraper.scrape_by_count(count)
                elif mode == "days":
                    days = cmd.get("days", 7)
                    tweets = self.scraper.scrape_last_n_days(days)
                elif mode == "date_range":
                    start_str = cmd.get("start_date", "")
                    end_str = cmd.get("end_date", "")
                    if not start_str:
                        self.emit(
                            "error",
                            message="start_date is required for date_range mode",
                        )
                        return
                    start_date = datetime.fromisoformat(start_str)
                    end_date = datetime.fromisoformat(end_str) if end_str else None
                    tweets = self.scraper.scrape_by_date(start_date, end_date)

                # Sort by date
                tweets.sort(
                    key=lambda t: t.date if t.date else datetime.min, reverse=True
                )
                self.current_tweets = tweets

                # Send updated tweets individually (full text may be large)
                self.emit(
                    "log",
                    level="info",
                    message=f"SCRAPE COMPLETE: Sending {len(tweets)} updated tweets...",
                )
                for i, tweet in enumerate(tweets):
                    try:
                        self.emit("tweet_update", tweet=tweet.to_dict())
                    except Exception as e:
                        self.emit(
                            "log",
                            level="warning",
                            message=f"Failed to send tweet_update {i+1}/{len(tweets)}: {str(e)[:80]}",
                        )

                # Emit lightweight complete event (no tweets payload)
                self.emit(
                    "log",
                    level="info",
                    message="SCRAPE COMPLETE: Sending complete event...",
                )
                self.emit(
                    "complete",
                    total=len(tweets),
                    scrape_id=self.current_scrape_id,
                    target=target or "bookmarks",
                    scrape_type=scrape_type,
                )
                self.emit(
                    "log",
                    level="info",
                    message="SCRAPE COMPLETE: Event sent successfully",
                )

            except KeyboardInterrupt:
                tweets = self.scraper.tweets_collected if self.scraper else []
                tweets.sort(
                    key=lambda t: t.date if t.date else datetime.min, reverse=True
                )
                self.current_tweets = tweets
                for tweet in tweets:
                    self.emit("tweet_update", tweet=tweet.to_dict())
                self.emit(
                    "complete",
                    total=len(tweets),
                    scrape_id=self.current_scrape_id,
                    target=cmd.get("target", "bookmarks"),
                    scrape_type=cmd.get("type", "profile"),
                    partial=True,
                )
            except Exception as e:
                self.emit("error", message=f"Scrape error: {e}")
                traceback.print_exc(file=sys.stderr)

        self._scrape_thread = threading.Thread(target=_do_scrape, daemon=True)
        self._scrape_thread.start()

    def handle_pause(self):
        """Pause current scrape"""
        if self.scraper:
            self.scraper.pause()

    def handle_resume(self):
        """Resume current scrape"""
        if self.scraper:
            self.scraper.resume()

    def handle_cancel(self):
        """Cancel current scrape"""
        if self.scraper:
            self.scraper.cancel()

    def handle_export(self, cmd: dict):
        """Handle export command"""
        self.emit(
            "log",
            level="info",
            message=f"EXPORT: Starting export with format={cmd.get('format', 'json')}",
        )
        try:
            if not self.current_tweets:
                self.emit("log", level="error", message="EXPORT: No tweets to export!")
                self.emit("error", message="No tweets to export. Run a scrape first.")
                return

            self.emit(
                "log",
                level="info",
                message=f"EXPORT: Have {len(self.current_tweets)} tweets",
            )

            fmt = cmd.get("format", "json")
            target = cmd.get("target", "export")
            filename = cmd.get("filename", "")
            output_dir = cmd.get("output_dir", "")

            self.emit(
                "log",
                level="info",
                message=f"EXPORT: fmt={fmt}, target={target}, output_dir='{output_dir}'",
            )

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ext = {"json": ".json", "md": ".md", "docx": ".docx"}.get(fmt, ".json")
                filename = f"{target}_tweets_{timestamp}{ext}"
                self.emit(
                    "log",
                    level="info",
                    message=f"EXPORT: Generated filename={filename}",
                )

            self.emit(
                "log", level="info", message=f"EXPORT: Creating {fmt} document..."
            )
            if fmt == "json":
                path = create_json_document(
                    self.current_tweets, filename, target, output_dir
                )
            elif fmt == "md":
                path = create_markdown_document(
                    self.current_tweets, filename, target, output_dir
                )
            elif fmt == "docx":
                path = create_word_document(
                    self.current_tweets, filename, target, output_dir
                )
            else:
                self.emit("log", level="error", message=f"EXPORT: Unknown format {fmt}")
                self.emit("error", message=f"Unknown export format: {fmt}")
                return

            self.emit("log", level="info", message=f"EXPORT: Success! Path={path}")
            self.emit(
                "export_complete", format=fmt, path=path, message=f"Exported to {path}"
            )
        except Exception as e:
            self.emit("log", level="error", message=f"EXPORT ERROR: {str(e)}")
            import traceback

            self.emit(
                "log",
                level="debug",
                message=f"EXPORT TRACEBACK: {traceback.format_exc()}",
            )
            self.emit("error", message=f"Export error: {e}")

    def handle_analyze(self, cmd: dict):
        """Handle analyze command"""
        try:
            api_key = cmd.get("api_key", "")
            tweets_data = cmd.get("tweets") or [
                t.to_dict() for t in self.current_tweets
            ]

            if not tweets_data:
                self.emit("error", message="No tweets to analyze")
                return

            if api_key:
                # AI analysis with OpenAI
                try:
                    from ai_analyzer import AIAnalyzer

                    analyzer = AIAnalyzer(api_key)
                    result = analyzer.analyze(tweets_data)
                    self.emit("analysis_result", **result)
                except ImportError:
                    self.emit("error", message="AI analyzer module not available")
                except Exception as e:
                    self.emit("error", message=f"AI analysis error: {e}")
            else:
                # Basic analytics (no AI)
                result = compute_analytics(tweets_data)
                self.emit("analysis_result", **result)

        except Exception as e:
            self.emit("error", message=f"Analysis error: {e}")

    def handle_status(self):
        """Handle status request"""
        if self.scraper:
            status = "paused" if self.scraper._paused else "running"
            if self.scraper._cancelled:
                status = "cancelled"
            self.emit(
                "status",
                status=status,
                collected=len(self.scraper.tweets_collected)
                if self.scraper.tweets_collected
                else 0,
                scrape_id=self.current_scrape_id,
            )
        else:
            self.emit("status", status="idle", collected=0)

    def handle_stop(self):
        """Handle stop/shutdown command"""
        if self.scraper:
            try:
                self.scraper.cancel()
                self.scraper.stop()
            except:
                pass
        self.emit("log", level="info", message="Service stopped")

    def handle_settings(self, cmd: dict):
        """Handle settings command"""
        action = cmd.get("action", "get")
        if action == "get":
            settings = {
                "chrome_path": self.scraper.chrome_path if self.scraper else None,
                "scroll_pause_min": self.scraper.scroll_pause_min
                if self.scraper
                else 2.0,
                "scroll_pause_max": self.scraper.scroll_pause_max
                if self.scraper
                else 4.0,
                "headless": self.scraper.headless if self.scraper else False,
            }
            self.emit("settings", settings=settings)
        elif action == "set":
            new_settings = cmd.get("settings", {})
            if self.scraper:
                if "chrome_path" in new_settings:
                    self.scraper.chrome_path = new_settings["chrome_path"]
                if "scroll_pause_min" in new_settings:
                    self.scraper.scroll_pause_min = float(
                        new_settings["scroll_pause_min"]
                    )
                if "scroll_pause_max" in new_settings:
                    self.scraper.scroll_pause_max = float(
                        new_settings["scroll_pause_max"]
                    )
            self.emit("log", level="info", message="Settings updated")

    def run(self):
        """Main event loop - reads commands from stdin, dispatches handlers"""
        self.emit("ready", version="1.0.0")

        while True:
            try:
                cmd = self.read_command()
                if cmd is None:
                    break  # stdin closed

                command = cmd.get("command", "")

                if command == "_invalid":
                    continue
                elif command == "login":
                    self.handle_login(cmd)
                elif command == "scrape":
                    self.handle_scrape(cmd)
                elif command == "pause":
                    self.handle_pause()
                elif command == "resume":
                    self.handle_resume()
                elif command == "cancel":
                    self.handle_cancel()
                elif command == "export":
                    self.handle_export(cmd)
                elif command == "analyze":
                    self.handle_analyze(cmd)
                elif command == "status":
                    self.handle_status()
                elif command == "settings":
                    self.handle_settings(cmd)
                elif command == "stop":
                    self.handle_stop()
                    break
                elif command == "login_confirm":
                    # Manual login confirmation from frontend
                    pass
                else:
                    self.emit("error", message=f"Unknown command: {command}")

            except KeyboardInterrupt:
                self.handle_stop()
                break
            except Exception as e:
                self.emit("error", message=f"Service error: {e}")
                traceback.print_exc(file=sys.stderr)


def main():
    service = ScraperService()
    service.run()


if __name__ == "__main__":
    main()
