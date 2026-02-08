# X (Twitter) Scraper

A Python-based automation tool that scrapes tweets from X (Twitter) profiles and bookmarks using Selenium WebDriver. Built as an AI-assisted project leveraging vibe coding methodology.

## Features

- **Profile Scraping** - Collect tweets from any public X profile (original posts only, replies filtered out)
- **Bookmark Scraping** - Export your saved bookmarks with full content
- **Multiple Scraping Modes** - By count, date range, or last N days
- **Full Content Extraction** - Automatically expands "Show more" truncated tweets and X Articles
- **Multi-Format Export** - Save as JSON (analysis-ready), Markdown, or Word (.docx)
- **Smart Filtering** - Skips promotional tweets, deduplicates content automatically
- **Anti-Detection** - Human-like typing, randomized delays, stealth browser configuration
- **Graceful Interruption** - Ctrl+C saves all collected data with `_PARTIAL` suffix
- **Session Reuse** - Scrape multiple profiles in one session without re-logging in
- **Dual Login Support** - Manual login (Google/Apple OAuth) or automatic credentials

## Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome installed

### Installation

```bash
git clone https://github.com/utkuvibing/twitter_scraper.git
cd twitter_scraper
pip install -r requirements.txt
```

### Usage

```bash
python main.py
```

The interactive CLI will guide you through:
1. Choose login method (manual recommended for OAuth)
2. Select source (profile or bookmarks)
3. Set scraping mode (count / date range / last N days)
4. Pick output format (JSON / Markdown / Word)

## Output Example

**JSON output** (ideal for data analysis and LLM pipelines):
```json
{
  "source": "twitter",
  "user": "@username",
  "total_tweets": 150,
  "tweets": [
    {
      "id": "1234567890",
      "text": "Tweet content here...",
      "date": "2025-02-08T14:30:00+00:00",
      "url": "https://x.com/username/status/1234567890",
      "has_media": true,
      "media_urls": ["..."],
      "has_article": false
    }
  ]
}
```

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.8+ | Core language |
| Selenium WebDriver | Browser automation & DOM interaction |
| webdriver-manager | Automatic ChromeDriver management |
| python-docx | Word document generation |

## How It Works

The scraper controls a real Chrome browser to navigate X's web interface, scroll through content, and extract tweet data from the DOM. This approach handles X's dynamic JavaScript rendering without requiring API access.

Key technical decisions:
- **Browser automation over API** - No rate limits, no API costs, access to bookmarks
- **Scroll-parse loop** - Continuously scrolls and parses new DOM elements as they load
- **Deferred full-text fetch** - Collects tweet stubs first, then opens truncated tweets in new tabs for full content
- **CDP stealth** - Uses Chrome DevTools Protocol to mask automation fingerprints

## Disclaimer

This tool is for **educational and personal archiving purposes only**. Please respect X's Terms of Service. Use responsibly.

## License

MIT
