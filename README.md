# DevBoards.io - News Scraper

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
- `--limit <number>`: Maximum number of articles to *fetch* from sources (default: 10).
- `--target <number>`: Target number of *new relevant* articles to save (default: 5).
- `--today-only <bool>`: Only process articles published today (default: True).
- `--source <url>`: Override configured sources with a specific URL.

```bash
# Example: Fetch 5 news from today with all translations
python main.py --target 5 --today-only True
```

## Localization
The scraper automatically generates translations for:
- **Italian (it)**
- **English (en)**
- **Spanish (es)**
- **French (fr)**
- **German (de)**

Each article is verified for completeness before being saved to the database.
