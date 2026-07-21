import codecs
import csv
import json
import os
import tempfile
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from document_generator import (
    create_csv_document,
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
    media_urls: List[str] = field(
        default_factory=lambda: ["https://pbs.twimg.com/media/example.jpg"]
    )
    tweet_url: str = "https://x.com/example/status/123"
    needs_full_text: bool = False
    has_article: bool = False
    likes: int = 5
    retweets: int = 2
    replies: int = 1
    views: int = 100


class ExportSchemaTests(unittest.TestCase):
    def test_media_urls_are_validated_and_deduplicated_in_order(self):
        tweet = DummyTweet(
            media_urls=[
                "https://pbs.twimg.com/media/one.jpg",
                "not-a-url",
                "https://pbs.twimg.com/media/one.jpg",
                "https://pbs.twimg.com/media/two.jpg",
            ]
        )

        normalized = normalize_tweet(tweet)

        self.assertEqual(
            normalized["media_urls"],
            [
                "https://pbs.twimg.com/media/one.jpg",
                "https://pbs.twimg.com/media/two.jpg",
            ],
        )

    def test_naive_export_dates_are_explicitly_normalized_to_utc(self):
        normalized = normalize_tweet(DummyTweet(date=datetime(2026, 5, 12, 10, 30)))

        self.assertEqual(normalized["date"], "2026-05-12T10:30:00+00:00")

    def test_default_output_is_below_the_current_working_directory(self):
        from document_generator import default_output_dir

        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                expected = str((Path(tmp) / "output").resolve())
                self.assertEqual(default_output_dir(), expected)
            finally:
                os.chdir(previous)

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
        self.assertNotIn("likes", normalized)
        self.assertNotIn("retweets", normalized)
        self.assertNotIn("replies", normalized)
        self.assertNotIn("views", normalized)

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
    def test_markdown_quotes_archive_text_instead_of_treating_it_as_markup(self):
        tweet = DummyTweet(text="# injected heading\n[click](javascript:alert(1))")
        with tempfile.TemporaryDirectory() as tmp:
            path = create_markdown_document([tweet], "archive.md", "example", output_dir=tmp)
            with open(path, encoding="utf-8") as markdown_file:
                markdown = markdown_file.read()

        self.assertIn("> # injected heading", markdown)
        self.assertIn("> [click](javascript:alert(1))", markdown)
        self.assertNotIn("\n# injected heading", markdown)

    def test_markdown_export_labels_are_english(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = create_markdown_document([DummyTweet()], "archive.md", "example", output_dir=tmp)
            with open(path, encoding="utf-8") as markdown_file:
                markdown = markdown_file.read()

        self.assertIn("# @example - Post Archive", markdown)
        self.assertIn("**Total:** 1 post", markdown)
        self.assertIn("**Date:**", markdown)
        self.assertIn("[Post link]", markdown)

    def test_csv_mitigates_formula_injection_without_changing_json_text(self):
        dangerous = DummyTweet(text='=HYPERLINK("https://evil.invalid")')
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = create_csv_document([dangerous], "archive.csv", "example", output_dir=tmp)
            json_path = create_json_document([dangerous], "archive.json", "example", output_dir=tmp)

            with open(csv_path, encoding="utf-8-sig", newline="") as csv_file:
                row = next(csv.DictReader(csv_file))
            with open(json_path, encoding="utf-8") as json_file:
                payload = json.load(json_file)

        self.assertEqual(row["text"], '\'=HYPERLINK("https://evil.invalid")')
        self.assertEqual(payload["tweets"][0]["text"], dangerous.text)

    def test_csv_mitigates_every_spreadsheet_formula_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tweets = [
                DummyTweet(id=str(index), text=f"{prefix}payload")
                for index, prefix in enumerate("=+-@")
            ]
            path = create_csv_document(tweets, "archive.csv", "example", output_dir=tmp)
            with open(path, encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(
            [row["text"] for row in rows], ["'=payload", "'+payload", "'-payload", "'@payload"]
        )

    def test_csv_export_uses_normalized_schema_and_spreadsheet_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = create_csv_document(
                [DummyTweet()], "archive.csv", "@example", output_dir=tmp
            )

            with open(csv_path, "rb") as f:
                payload = f.read()

        self.assertTrue(payload.startswith(codecs.BOM_UTF8))
        rows = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
        self.assertEqual(rows[0]["tweet_url"], "https://x.com/example/status/123")
        self.assertEqual(rows[0]["media_urls"], "https://pbs.twimg.com/media/example.jpg")
        self.assertNotIn("likes", rows[0])

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
