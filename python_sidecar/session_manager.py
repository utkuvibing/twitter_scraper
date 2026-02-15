"""
Session Manager - Cookie persistence for Chrome/Selenium sessions.
Saves and loads cookies so users don't need to re-login each time.
"""

import json
import os
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime


class SessionManager:
    """Manages browser session persistence via cookies"""

    def __init__(self, session_dir: Optional[str] = None, emit: Optional[Callable] = None):
        if session_dir is None:
            session_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), ".sessions"
            )
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)
        self._emit = emit or (lambda msg_type, **kwargs: None)

    def _get_cookie_path(self, profile: str = "default") -> str:
        return os.path.join(self.session_dir, f"{profile}_cookies.json")

    def save_cookies(self, driver, profile: str = "default") -> bool:
        """Save browser cookies to file"""
        try:
            cookies = driver.get_cookies()
            cookie_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "domain": "x.com",
            }
            cookie_path = self._get_cookie_path(profile)
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            self._emit("log", level="info", message=f"Cookies saved for profile: {profile}")
            return True
        except Exception as e:
            self._emit("log", level="error", message=f"Failed to save cookies: {e}")
            return False

    def load_cookies(self, driver, profile: str = "default") -> bool:
        """Load cookies from file into browser"""
        cookie_path = self._get_cookie_path(profile)
        if not os.path.exists(cookie_path):
            self._emit("log", level="info", message="No saved cookies found")
            return False

        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)

            # Check if cookies are too old (7 days)
            saved_at = datetime.fromisoformat(cookie_data.get("saved_at", ""))
            age_days = (datetime.now() - saved_at).days
            if age_days > 7:
                self._emit("log", level="warning", message="Saved cookies are too old, will need fresh login")
                self.clear_cookies(profile)
                return False

            # Navigate to domain first
            driver.get("https://x.com")
            time.sleep(1)

            # Add cookies
            for cookie in cookie_data.get("cookies", []):
                try:
                    # Remove problematic fields
                    for field in ["sameSite", "storeId", "hostOnly"]:
                        cookie.pop(field, None)
                    driver.add_cookie(cookie)
                except Exception:
                    continue

            # Refresh to apply cookies
            driver.refresh()
            time.sleep(2)

            # Check if login is valid
            current_url = driver.current_url.lower()
            if "login" in current_url or "flow" in current_url:
                self._emit("log", level="warning", message="Saved cookies expired, need fresh login")
                self.clear_cookies(profile)
                return False

            self._emit("log", level="info", message="Session restored from saved cookies")
            return True

        except Exception as e:
            self._emit("log", level="error", message=f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self, profile: str = "default") -> bool:
        """Delete saved cookies for a profile"""
        cookie_path = self._get_cookie_path(profile)
        try:
            if os.path.exists(cookie_path):
                os.remove(cookie_path)
            return True
        except Exception:
            return False

    def has_saved_session(self, profile: str = "default") -> bool:
        """Check if there are saved cookies for a profile"""
        cookie_path = self._get_cookie_path(profile)
        if not os.path.exists(cookie_path):
            return False
        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            saved_at = datetime.fromisoformat(cookie_data.get("saved_at", ""))
            age_days = (datetime.now() - saved_at).days
            return age_days <= 7
        except Exception:
            return False

    def list_profiles(self) -> List[str]:
        """List all saved session profiles"""
        profiles = []
        for f in os.listdir(self.session_dir):
            if f.endswith("_cookies.json"):
                profiles.append(f.replace("_cookies.json", ""))
        return profiles
