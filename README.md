# X Scraper

Python/Selenium CLI scraper for personal X/Twitter archiving. It can collect public profile posts or authenticated bookmarks, then export results as JSON, Markdown, or DOCX.

This repository is intentionally CLI-only. The previous Tauri/React desktop prototype was removed so the project stays easier to run, test, and maintain.

## Capabilities

- Profile scraping for public posts
- Bookmark scraping for the signed-in user's saved posts
- Count, last-N-days, and date-range scrape modes
- Best-effort expansion for long tweets and X Articles
- JSON, Markdown, and Word export
- Versioned JSON export schema (`schema_version: "0.2"`)
- Safer output handling with sanitized filenames and per-target output folders
- Selector diagnostics and structured run logs (`schema_version: "0.3"`)

## Limits

This project automates the X web UI through Selenium. X changes its DOM, labels, login flows, and timeline behavior frequently, so selectors and long-form extraction can break without warning. Treat scraped data as best-effort and verify important exports manually.

This project does not bypass access controls, does not include credentials, and should only be used for educational or personal archiving workflows that you are authorized to perform.

## Install

```bash
git clone https://github.com/utkuvibing/twitter_scraper.git
cd twitter_scraper
pip install -r requirements.txt
```

Chrome must be installed. `webdriver-manager` downloads the matching ChromeDriver.

## CLI Usage

```bash
python main.py
```

The CLI prompts for:

1. Login method
2. Profile or bookmarks source
3. Count, date range, or last-N-days mode
4. JSON, Markdown, or DOCX export

Exports are written under `output/<target>/` by default. Each scrape also writes a run log under `output/<target>/logs/`.

## Selector Diagnostics

Run selector diagnostics without starting a scrape:

```bash
python main.py --diagnostics
```

The CLI opens Chrome, lets you navigate or log in, then checks the currently loaded page for core X selectors such as login fields, tweet articles, tweet text, status links, long-tweet controls, and article links. A diagnostics run writes a structured log under `output/diagnostics/logs/`.

Diagnostics only reports what is detectable on the current page. It does not guarantee a full scrape will succeed, and it does not bypass login, rate limits, private content, or platform restrictions.

## Run Logs

Every CLI scrape writes a JSON run log under:

```text
output/<target>/logs/
```

Run logs include:

- scrape stage (`login`, `profile_navigation`, `bookmarks_navigation`, `timeline_loading`, `tweet_parsing`, `full_text_extraction`, `article_extraction`, `export_saving`)
- severity level
- failure reason codes such as `login_failed`, `profile_navigation_failed`, `timeline_empty`, `tweet_parse_failed`, `full_text_failed`, `article_extraction_failed`, or `export_failed`
- selector names where a selector was involved
- timing and diagnostic details

These logs are intended for debugging X DOM changes and incomplete runs. They do not contain credentials.

## JSON Export Schema

JSON exports use a stable top-level shape:

```json
{
  "schema_version": "0.2",
  "source": "x.com",
  "scrape_type": "profile",
  "user": "@example",
  "target": "example",
  "exported_at": "2026-05-12T10:30:00+00:00",
  "total_tweets": 1,
  "tweets": [
    {
      "id": "1234567890",
      "text": "Tweet content",
      "date": "2026-05-12T10:30:00+00:00",
      "date_str": "May 12, 2026",
      "url": "https://x.com/example/status/1234567890",
      "tweet_url": "https://x.com/example/status/1234567890",
      "has_media": false,
      "media_urls": [],
      "has_article": false,
      "needs_full_text": false,
      "likes": 0,
      "retweets": 0,
      "replies": 0,
      "views": 0
    }
  ]
}
```

`url` is kept for compatibility; `tweet_url` is the explicit canonical field used by current exports.

## Validation

Run the browser-free validation suite:

```bash
python -m unittest discover -s tests
python -m compileall main.py scraper.py document_generator.py export_schema.py diagnostics.py config.py
```

## Project Structure

```text
main.py                 Interactive Python CLI
scraper.py              Selenium scraper
config.py               Selector definitions and runtime constants
document_generator.py   JSON/Markdown/DOCX export writers
export_schema.py        Export schema and safe write helpers
diagnostics.py          Selector diagnostics and structured run logs
tests/                  Browser-free validation tests
```

## License

MIT
