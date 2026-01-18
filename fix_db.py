import os
from dotenv import load_dotenv
from pymongo import MongoClient
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_database():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found")
        return

    try:
        client = MongoClient(db_url)
        db = client.get_database()
        collection = db.news

        # Update 1: Set is_published = True where missing
        result = collection.update_many(
            {"is_published": {"$exists": False}}, {"$set": {"is_published": True}}
        )
        logger.info(f"Updated {result.modified_count} documents with is_published=True")

        # Update 2: Rename 'views' to 'views_count'
        result_views = collection.update_many(
            {"views": {"$exists": True}}, {"$rename": {"views": "views_count"}}
        )
        logger.info(
            f"Renamed 'views' to 'views_count' in {result_views.modified_count} documents"
        )

        # Update 3: Ensure clicks_count exists
        result_clicks = collection.update_many(
            {"clicks_count": {"$exists": False}}, {"$set": {"clicks_count": 0}}
        )
        logger.info(f"Added 'clicks_count' to {result_clicks.modified_count} documents")

        # Update 4: Remove 'likes' field if it exists (as it might be confusing, though harmless)
        result_likes = collection.update_many(
            {"likes": {"$exists": True}}, {"$unset": {"likes": ""}}
        )
        logger.info(
            f"Removed 'likes' field from {result_likes.modified_count} documents"
        )

    except Exception as e:
        logger.error(f"Error updating database: {e}")


if __name__ == "__main__":
    fix_database()
