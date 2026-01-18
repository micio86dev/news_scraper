import argparse
import logging
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from scraper import NewsScraper
from ai import NewsAI
from db import Database

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_slug(title: str) -> str:
    """Generates a URL-friendly slug from the title."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def main():
    # Load env vars
    load_dotenv()

    # Parse CLI Arguments
    parser = argparse.ArgumentParser(description="IT Job Hub News Scraper")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without saving to DB"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Max articles to process per feed"
    )
    parser.add_argument("--source", type=str, help="Specific RSS feed URL to scrape")

    args = parser.parse_args()

    logger.info("Starting News Scraper...")
    if args.dry_run:
        logger.info("Running in DRY-RUN mode. No data will be saved.")

    # Initialize components
    scraper = NewsScraper()
    ai = NewsAI()

    db = None
    if not args.dry_run:
        try:
            db = Database()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return

    # Determine sources
    sources = []
    if args.source:
        sources.append(args.source)
    else:
        env_feeds = os.getenv("RSS_FEEDS", "")
        if env_feeds:
            sources = [s.strip() for s in env_feeds.split(",") if s.strip()]

    if not sources:
        logger.warning(
            "No RSS feeds found. Please provide --source or set RSS_FEEDS in .env"
        )
        return

    total_added = 0

    for source_url in sources:
        logger.info(f"Processing source: {source_url}")
        articles = scraper.fetch_feed(source_url)

        # Limit articles
        articles = articles[: args.limit]

        for article in articles:
            # Check for duplicates first to save AI tokens
            if db and db.is_duplicate(article["source_url"]):
                logger.info(f"Skipping duplicate: {article['title']}")
                continue

            logger.info(f"Processing: {article['title']}")

            # AI Processing
            ai_data = ai.process_article(article["title"], article["content_raw"])

            if not ai_data:
                logger.warning(
                    f"AI processing failed for {article['title']}. key content: {article['content_raw'][:50]}..."
                )
                # Fallback or skip? Let's skip for now or provide defaults
                ai_data = {
                    "summary": article["content_raw"][:200] + "...",
                    "category": "General",
                    "tags": [],
                    "language": "en",
                    "sentiment": "neutral",
                }

            # Merge data
            full_article = {
                **article,
                **ai_data,
                "slug": generate_slug(article["title"]),
                "views": 0,
                "likes": 0,
            }

            # Save
            if args.dry_run:
                logger.info(
                    f"[DRY RUN] Would save: {full_article['title']} - {full_article['category']}"
                )
            else:
                if db.save_article(full_article):
                    total_added += 1

    logger.info(f"Scraping completed. Added {total_added} new articles.")


if __name__ == "__main__":
    main()
