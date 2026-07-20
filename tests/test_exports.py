import json
import os
import tempfile
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from document_generator import (
    create_json_document,
    create_markdown_document,
    create_word_document,
)
from export_schema import (
    EXPORT_SCHEMA_VERSION,
    build_export_payload,
    ensure_extension,
    normalize_tweet,
    resolve_output_path,
    safe_path_segment,
)


@dataclass
class DummyTweet:
    id: str = "123"
    text: str = "Hello from a scraped tweet"
    date: datetime = datetime(2026, 5, 12, 10, 30, tzinfo=timezone.utc)
    date_str: str = "May 12, 2026"
    media_urls: List[str] = field(default_factory=lambda: ["https://pbs.twimg.com/media/example.jpg"])
    tweet_url: str = "https://x.com/example/status/123"
    needs_full_text: bool = False
    has_article: bool = False
    likes: int = 5
    retweets: int = 2
    replies: int = 1
    views: int = 100


class ExportSchemaTests(unittest.TestCase):
    def test_safe_path_segment_removes_path_control_characters(self):
        self.assertEqual(safe_path_segment("../@bad:user?name"), "bad_user_name")
        self.assertEqual(safe_path_segment("CON"), "_CON")
        self.assertEqual(safe_path_segment("", default="fallback"), "fallback")

    def test_ensure_extension_preserves_expected_extension(self):
        self.assertEqual(ensure_extension("../tweets.json", ".json"), "tweets.json")
        self.assertEqual(ensure_extension("tweets", "md"), "tweets.md")
        self.assertEqual(ensure_extension("tweets.txt", ".json"), "tweets.json")

    def test_resolve_output_path_stays_under_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = resolve_output_path("@bad/user", "../escape.json", ".json", tmp)
            expected_dir = os.path.join(os.path.abspath(tmp), "bad_user")
            self.assertEqual(os.path.dirname(path), expected_dir)
            self.assertEqual(os.path.basename(path), "escape.json")

    def test_normalize_tweet_supports_object_and_dict_inputs(self):
        normalized = normalize_tweet(DummyTweet())
        self.assertEqual(normalized["id"], "123")
        self.assertTrue(normalized["has_media"])
        self.assertEqual(normalized["tweet_url"], normalized["url"])
        self.assertEqual(normalized["likes"], 5)

        normalized_dict = normalize_tweet({"id": "456", "url": "https://x.com/u/status/456"})
        self.assertEqual(normalized_dict["tweet_url"], "https://x.com/u/status/456")

    def test_build_export_payload_is_versioned(self):
        payload = build_export_payload(
            [DummyTweet()],
            "@example",
            exported_at=datetime(2026, 5, 12, 10, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(payload["schema_version"], EXPORT_SCHEMA_VERSION)
        self.assertEqual(payload["source"], "x.com")
        self.assertEqual(payload["target"], "example")
        self.assertEqual(payload["total_tweets"], 1)
        self.assertEqual(payload["tweets"][0]["id"], "123")

    def test_build_export_payload_preserves_bookmark_scrape_type(self):
        payload = build_export_payload(
            [DummyTweet()],
            "bookmarks",
            scrape_type="bookmarks",
            exported_at=datetime(2026, 5, 12, 10, 30, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["scrape_type"], "bookmarks")
        self.assertEqual(payload["target"], "bookmarks")


class DocumentExportTests(unittest.TestCase):
    def test_json_markdown_and_docx_exports_write_files(self):
        tweets = [DummyTweet()]
        with tempfile.TemporaryDirectory() as tmp:
            json_path = create_json_document(tweets, "../unsafe.json", "@example", output_dir=tmp)
            md_path = create_markdown_document(tweets, "archive.md", "@example", output_dir=tmp)
            docx_path = create_word_document(tweets, "archive.docx", "@example", output_dir=tmp)

            self.assertTrue(os.path.isfile(json_path))
            self.assertTrue(os.path.isfile(md_path))
            self.assertTrue(os.path.isfile(docx_path))
            self.assertEqual(os.path.dirname(json_path), os.path.join(tmp, "example"))

            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            self.assertEqual(payload["schema_version"], EXPORT_SCHEMA_VERSION)
            self.assertEqual(payload["tweets"][0]["tweet_url"], tweets[0].tweet_url)

            with open(md_path, "r", encoding="utf-8") as f:
                markdown = f.read()

            self.assertIn(f"**Schema:** {EXPORT_SCHEMA_VERSION}", markdown)
            self.assertIn("Hello from a scraped tweet", markdown)

    def test_json_export_preserves_bookmark_scrape_type(self):
        tweets = [DummyTweet()]
        with tempfile.TemporaryDirectory() as tmp:
            json_path = create_json_document(
                tweets,
                "bookmarks.json",
                "bookmarks",
                output_dir=tmp,
                scrape_type="bookmarks",
            )

            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            self.assertEqual(payload["scrape_type"], "bookmarks")
            self.assertEqual(payload["target"], "bookmarks")


if __name__ == "__main__":
    unittest.main()
