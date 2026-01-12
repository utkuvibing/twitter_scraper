# Twitter/X Scraper

A Python GUI application to scrape tweets from X (Twitter) profiles.

## Features

- Scrape tweets from any public X profile
- Filter original tweets (exclude replies and retweets)
- Export to Word document (.docx)
- User-friendly GUI interface

## Requirements

- Python 3.8+
- Chrome browser installed
- ChromeDriver (automatically managed)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/twitter_scraper.git
cd twitter_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

1. Enter your X (Twitter) credentials
2. Enter the target username to scrape
3. Set the number of tweets to fetch
4. Click "Start" to begin scraping
5. Export results to Word document

## Files

- `main.py` - GUI application (Tkinter)
- `scraper.py` - Tweet scraping logic (Selenium)
- `document_generator.py` - Word document export
- `config.py` - Configuration and selectors

## Disclaimer

This tool is for educational purposes only. Please respect X's Terms of Service and rate limits. Use responsibly.
