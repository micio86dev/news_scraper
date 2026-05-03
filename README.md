# DevBoards.io — News Scraper

Standalone Python scraper: fetches tech news from RSS feeds, classifies and translates articles using OpenAI GPT-4o-mini, stores results in MongoDB.

## Tech Stack

- **Language**: Python 3.10+
- **AI**: OpenAI GPT-4o-mini (categorization + 5-language translation)
- **Database**: MongoDB (shared `itjobhub` db with backend)
- **HTTP**: requests + BeautifulSoup4

## Prerequisites

- Python 3.10+
- MongoDB accessible at `DATABASE_URL`
- OpenAI API key

## Setup

```bash
cd apps/news_scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env
```

## Environment Variables

```bash
OPENAI_API_KEY=your-openai-api-key      # Required
DATABASE_URL=mongodb://localhost:27017/itjobhub?replicaSet=rs0&w=1&journal=true
MONGO_DB=itjobhub
RSS_FEEDS=https://www.theverge.com/rss/index.xml,https://hnrss.org/frontpage,https://www.infoq.com/feed/
```

## Usage

```bash
# Standard run: fetch up to 10 articles, save 5 new relevant ones from today
python main.py

# Options:
python main.py --dry-run              # Process but do not save
python main.py --limit 20             # Fetch up to 20 articles per feed
python main.py --target 10            # Save up to 10 new articles
python main.py --today-only False     # Include older articles
python main.py --source https://...   # Override RSS_FEEDS with single URL
```

## Pipeline

```
RSS/Atom feeds
    └─► fetch articles (filter by today if --today-only)
            └─► dedup check (source_url unique index)
                    └─► fetch full content if article < 2000 chars
                            └─► OpenAI GPT-4o-mini:
                                  - relevance check
                                  - category + tags + sentiment
                                  - translations (en + it + es + de + fr)
                                        └─► validate 5 languages present
                                                └─► save to MongoDB
```

## AI Classification

**Include**: programming languages, frameworks, DevOps/Cloud, Cybersecurity, AI/ML (technical), Databases.

**Exclude**: consumer electronics, generic business news, video games.

**Categories**: AI | DevOps | Cybersecurity | Development | Cloud | Data Science | Blockchain

## MongoDB Collection: `news`

```
{ title, slug (unique), summary, content, source_url (unique),
  category, tags, language, sentiment, published_at, is_published,
  views_count, clicks_count,
  translations: [{ language, title, summary, content }] }
```

## Automated Runs

Daily at 03:00 UTC via GitHub Actions (`apps/devops/workflows/news_scraper/import-script-news.yml`).
Requires GitHub Secrets: `OPENAI_API_KEY`, `MONGO_URI_STAGE`/`MONGO_URI_PROD`.

## Testing

```bash
pytest
```

## Notes

- Articles missing any of the 5 translations are discarded.
- `--target` caps OpenAI API spend per run.
- Writes directly to MongoDB — bypasses backend REST API.
- `POST /news/import` on the backend handles single-article API imports.
