# IT Job Hub - News Scraper

Standalone Python scraper to fetch, categorize, and store IT news articles into MongoDB.

## Features
- Fetches news from RSS feeds or direct URLs.
- Uses OpenAI to categorize, tag, and translate articles (IT, ES, FR, DE, EN).
- Checks for duplicates in MongoDB to avoid reposting.
- Supports dry-run mode for testing.

## Setup

1. **Install Python 3.10+**
2. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in the details.
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure `DATABASE_URL` matches your backend configuration.*

## Usage

**Run Scraper:**
```bash
python main.py
```

**Options:**
- `--dry-run`: Fetch and process articles but do not save to DB.
- `--limit <number>`: Limit the number of articles to process (default: 10).
- `--source <url>`: Override configured sources with a specific URL.

```bash
python main.py --dry-run --limit 5
```
