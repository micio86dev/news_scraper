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
    parser = argparse.ArgumentParser(description="DevBoards.io News Scraper")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without saving to DB"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Max articles to process per feed"
    )
    parser.add_argument(
        "--target", type=int, default=5, help="Target number of new articles to add"
    )

    def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ("yes", "true", "t", "y", "1"):
            return True
        elif v.lower() in ("no", "false", "f", "n", "0"):
            return False
        else:
            raise argparse.ArgumentTypeError("Boolean value expected.")

    parser.add_argument(
        "--today-only",
        type=str2bool,
        default=True,
        help="Only process articles from today (default: True)",
    )
    parser.add_argument("--source", type=str, help="Specific RSS feed URL to scrape")

    args = parser.parse_args()

    # If --today-only is passed as a flag it might be tricky with default=True
    # Let's adjust to be more explicit if needed, but for now default is True.

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
    target_met = False

    # Get today's date range (naive comparison for simplicity, or localized if needed)
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)

    for source_url in sources:
        if target_met:
            break

        logger.info(f"Processing source: {source_url}")
        articles = scraper.fetch_feed(source_url)

        # Note: We don't limit here anymore because we want to find 5 from today across all sources
        # unless args.limit is specifically used as a safety cap per source.
        source_articles_checked = 0

        for article in articles:
            if target_met:
                break

            if source_articles_checked >= args.limit:
                break

            source_articles_checked += 1

            # Date Filtering
            pub_date = article["published_at"]
            # Handle possible TZ awareness
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)

            is_today = pub_date >= today_start

            if args.today_only and not is_today:
                logger.debug(
                    f"Skipping article from {pub_date} (not today): {article['title']}"
                )
                continue

            # Check for duplicates first to save AI tokens
            if db and db.is_duplicate(article["source_url"]):
                logger.info(f"Skipping duplicate: {article['title']}")
                continue

            logger.info(f"Processing: {article['title']} (Published: {pub_date})")

            # Try to fetch full content if feed content is short or snippet-like
            logger.info(
                f"Article '{article['title']}' initial content length: {len(article['content_raw'])}"
            )
            if article["source_url"] and (
                len(article["content_raw"]) < 2000
                or "Read the full story" in article["content_raw"]
            ):
                logger.info(
                    f"Attempting full content fetch for: {article['title']} from {article['source_url']}"
                )
                full_text = scraper.fetch_full_content(article["source_url"])
                if full_text and len(full_text) > len(article["content_raw"]):
                    article["content_raw"] = full_text
                    logger.info(
                        f"Fetched full content for: {article['title']} ({len(full_text)} chars)"
                    )
                else:
                    logger.warning(
                        f"Full content fetch failed or returned shorter text for: {article['title']}"
                    )
            else:
                logger.info(
                    f"Skipping full content fetch for: {article['title']} (length: {len(article['content_raw'])})"
                )

            # AI Processing
            ai_data = ai.process_article(article["title"], article["content_raw"])

            if not ai_data:
                logger.warning(
                    f"AI processing failed for {article['title']}. key content: {article['content_raw'][:50]}..."
                )
                # Fallback remains same as before but ensured it exists
                ai_data = {
                    "is_relevant": True,
                    "summary": article["content_raw"][:200] + "...",
                    "category": "General",
                    "tags": [],
                    "language": "en",
                    "sentiment": "neutral",
                    "translations": [
                        {
                            "language": "it",
                            "title": f"[IT] {article['title']}",
                            "summary": "Sommario automatico",
                            "content": "Contenuto tradotto automaticamente.",
                        },
                        {
                            "language": "es",
                            "title": f"[ES] {article['title']}",
                            "summary": "Resumen automático",
                            "content": "Contenido traducido automáticamente.",
                        },
                        {
                            "language": "fr",
                            "title": f"[FR] {article['title']}",
                            "summary": "Résumé automatique",
                            "content": "Contenu traduit automatiquement.",
                        },
                        {
                            "language": "de",
                            "title": f"[DE] {article['title']}",
                            "summary": "Automatische Zusammenfassung",
                            "content": "Automatisch übersetzter Inhalt.",
                        },
                        {
                            "language": "en",
                            "title": article["title"],
                            "summary": article["content_raw"][:200],
                            "content": "Original Content",
                        },
                    ],
                }

            # CRITICAL: Validate translations
            required_langs = ["en", "it", "es", "de", "fr"]
            trans_langs = [t.get("language") for t in ai_data.get("translations", [])]
            missing_langs = [l for l in required_langs if l not in trans_langs]

            if missing_langs:
                logger.warning(
                    f"AI response missing required languages {missing_langs} for {article['title']}. Skipping."
                )
                continue
                logger.warning(
                    f"AI processing failed for {article['title']}. key content: {article['content_raw'][:50]}..."
                )
                # Fallback remains same as before but ensured it exists
                ai_data = {
                    "is_relevant": True,
                    "summary": article["content_raw"][:200] + "...",
                    "category": "General",
                    "tags": [],
                    "language": "en",
                    "sentiment": "neutral",
                    "translations": [
                        {
                            "language": "it",
                            "title": f"[IT] {article['title']}",
                            "summary": "Sommario automatico",
                            "content": "Contenuto tradotto automaticamente.",
                        },
                        {
                            "language": "es",
                            "title": f"[ES] {article['title']}",
                            "summary": "Resumen automático",
                            "content": "Contenido traducido automáticamente.",
                        },
                        {
                            "language": "fr",
                            "title": f"[FR] {article['title']}",
                            "summary": "Résumé automatique",
                            "content": "Contenu traduit automatiquement.",
                        },
                        {
                            "language": "de",
                            "title": f"[DE] {article['title']}",
                            "summary": "Automatische Zusammenfassung",
                            "content": "Automatisch übersetzter Inhalt.",
                        },
                        {
                            "language": "en",
                            "title": article["title"],
                            "summary": article["content_raw"][:200],
                            "content": "Original Content",
                        },
                    ],
                }

            if ai_data.get("is_relevant") is False:
                logger.info(f"Skipping irrelevant article (AI): {article['title']}")
                continue

            # Merge data
            full_article = {
                **article,
                **ai_data,
                "slug": generate_slug(article["title"]),
                "views_count": 0,
                "clicks_count": 0,
                "is_published": True,
            }

            # Save
            if args.dry_run:
                logger.info(
                    f"[DRY RUN] Would save: {full_article['title']} - {full_article['category']}"
                )
                total_added += 1  # Count for dry run too
            else:
                if db.save_article(full_article):
                    total_added += 1

            if total_added >= args.target:
                logger.info(f"Target of {args.target} articles reached.")
                target_met = True

    logger.info(f"Scraping completed. Added {total_added} new articles.")


if __name__ == "__main__":
    main()
