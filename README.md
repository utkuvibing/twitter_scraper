# X Scraper

Python/Selenium scraper for personal X/Twitter archiving, with an interactive CLI and a Tauri desktop interface. It can collect public profile posts or authenticated bookmarks, then export results as JSON, Markdown, or DOCX.

## Current Capabilities

- Profile scraping for public posts
- Bookmark scraping for the signed-in user's saved posts
- Count, last-N-days, and date-range scrape modes
- Best-effort expansion for long tweets and X Articles
- JSON, Markdown, and Word export
- Session cookie reuse in the desktop sidecar
- Pause, resume, cancel, and partial-result handling in supported flows
- Versioned JSON export schema (`schema_version: "0.2"`)
- Safer output handling with sanitized filenames and per-target output folders

## Important Limits

This project automates the X web UI through Selenium. X changes its DOM, labels, and login flows frequently, so selectors and long-form extraction can break without warning. Treat scraped data as best-effort and verify important exports manually.

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

Exports are written under `output/<target>/` by default.

## Desktop Usage

```bash
npm install
npm run tauri dev
```

The desktop app uses `python_sidecar/` for scraping and streams structured events to the React UI.

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

`url` is kept for compatibility; `tweet_url` is the explicit canonical field used by the app.

## Validation

Run the local validation suite without opening a browser:

```bash
python -m unittest discover -s tests
python -m compileall main.py scraper.py document_generator.py export_schema.py python_sidecar
```

For the desktop frontend:

```bash
npm run build
```

## Project Structure

```text
main.py                 Interactive Python CLI
scraper.py              CLI Selenium scraper
document_generator.py   JSON/Markdown/DOCX export writers
export_schema.py        Shared export schema and safe write helpers
python_sidecar/         JSON-line scraper service used by Tauri
src/                    React frontend
src-tauri/              Tauri/Rust backend
tests/                  Browser-free validation tests
```

## License

MIT
