"""
Shared export schema and safe file-writing helpers.

This module is intentionally Selenium-free so it can be validated locally
without a live X/Twitter session.
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from time_utils import ensure_utc

EXPORT_SCHEMA_VERSION = "1.0"

_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_path_segment(value: Optional[str], default: str = "export") -> str:
    """Return a filesystem-safe single path segment."""
    text = str(value or "").strip().lstrip("@")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip(" ._@")

    if not text:
        text = default

    if text.upper() in _WINDOWS_RESERVED_NAMES:
        text = f"_{text}"

    return text[:120]


def ensure_extension(filename: str, extension: str) -> str:
    """Ensure a filename has the expected extension."""
    if not extension.startswith("."):
        extension = f".{extension}"

    filename = os.path.basename(filename or "")
    stem, current_ext = os.path.splitext(filename)
    stem = safe_path_segment(stem, "export")

    if current_ext.lower() == extension.lower():
        return f"{stem}{current_ext}"
    return f"{stem}{extension}"


def resolve_output_path(
    target_username: str,
    filename: str,
    extension: str,
    base_output_dir: str,
    output_dir: Optional[str] = None,
) -> str:
    """Resolve a safe export path under the chosen output directory."""
    base_dir = os.path.abspath(output_dir or base_output_dir)
    target_dir = os.path.join(base_dir, safe_path_segment(target_username, "bookmarks"))
    os.makedirs(target_dir, exist_ok=True)

    safe_filename = ensure_extension(filename, extension)
    return os.path.join(target_dir, safe_filename)


def _get_value(tweet: Any, key: str, default: Any = None) -> Any:
    if isinstance(tweet, dict):
        return tweet.get(key, default)
    return getattr(tweet, key, default)


def _date_to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, str):
        return value
    return str(value)


def normalize_media_urls(values: Iterable[Any]) -> List[str]:
    """Return unique, valid HTTP(S) media URLs while preserving order."""
    normalized: List[str] = []
    seen = set()
    for value in values:
        url = str(value or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or url in seen:
            continue
        seen.add(url)
        normalized.append(url)
    return normalized


def normalize_tweet(tweet: Any) -> Dict[str, Any]:
    """Convert a Tweet object or dict into the public export schema."""
    tweet_url = _get_value(tweet, "tweet_url") or _get_value(tweet, "url", "")
    media_urls = normalize_media_urls(_get_value(tweet, "media_urls", []) or [])

    normalized = {
        "id": str(_get_value(tweet, "id", "")),
        "text": _get_value(tweet, "text", "") or "",
        "date": _date_to_iso(_get_value(tweet, "date")),
        "date_str": _get_value(tweet, "date_str", "") or "",
        "url": tweet_url,
        "tweet_url": tweet_url,
        "has_media": len(media_urls) > 0,
        "media_urls": media_urls,
        "has_article": bool(_get_value(tweet, "has_article", False)),
        "needs_full_text": bool(_get_value(tweet, "needs_full_text", False)),
    }
    return normalized


def csv_safe(value: Any) -> Any:
    """Prevent spreadsheet formula execution without mutating non-CSV exports."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def build_export_payload(
    tweets: Iterable[Any],
    target_username: str,
    scrape_type: str = "profile",
    exported_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the versioned JSON export payload."""
    exported_at = exported_at or datetime.now(timezone.utc)
    normalized_tweets: List[Dict[str, Any]] = [normalize_tweet(tweet) for tweet in tweets]

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "source": "x.com",
        "scrape_type": scrape_type,
        "user": f"@{str(target_username).lstrip('@')}",
        "target": str(target_username).lstrip("@"),
        "exported_at": exported_at.isoformat(),
        "total_tweets": len(normalized_tweets),
        "tweets": normalized_tweets,
    }


def atomic_write_text(path: str, content: str, encoding: str = "utf-8") -> None:
    """Write text via a same-directory temp file, then atomically replace."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".write", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def atomic_save_docx(document: Any, path: str) -> None:
    """Save a python-docx document atomically."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".docx", dir=directory)
    os.close(fd)
    try:
        document.save(tmp_path)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
