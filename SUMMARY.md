# News Scraper Summary

The news scraper is a Python-based utility designed to fetch IT and Developer-focused news from various RSS/Atom feeds, process them using AI for categorization, sentiment analysis, and multi-language translation, and store them in a MongoDB database.

## Key Features
- **RSS/Atom Parsing**: Robust handling of various date formats (RFC 822, ISO 8601).
- **AI Filtering**: Uses OpenAI to identify relevant IT news and filter out consumer tech, ads, or irrelevant content.
- **Multilingual**: Automatically translates every article into 5 languages: Italian (it), English (en), Spanish (es), German (de), and French (fr).
- **Date Filtering**: Optional `--today-only` flag to restrict imports to the current day's news.
- **Target Count**: Adjustable `--target` count to ensure a specific number of new articles are imported.

## Core Components
- `main.py`: The entry point and orchestration logic.
- `scraper.py`: Handles feed fetching and normalization.
- `ai.py`: Interface for OpenAI article processing and translation.
- `db.py`: MongoDB interaction layer.

## Verification
A dedicated `verify_news.py` script ensures that the imported news items meet the quality and localization requirements.
