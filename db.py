import logging
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: Optional[str] = None, db_name: Optional[str] = None):
        self.db_url = (
            db_url
            or os.getenv("DATABASE_URL")
            or os.getenv("MONGO_URI")
            or os.getenv("MONGODB_URI")
        )
        # Support MONGO_DB env var for explicit database selection
        self.db_name = db_name or os.getenv("MONGO_DB")

        if not self.db_url:
            raise ValueError(
                "MongoDB connection URL not found in environment variables (checked DATABASE_URL, MONGO_URI, MONGODB_URI)."
            )

        try:
            # Log connection attempt (obfuscated URI)
            safe_uri = self.db_url.split("@")[-1] if "@" in self.db_url else self.db_url
            logger.info(f"Connecting to MongoDB at {safe_uri}")

            self.client = MongoClient(self.db_url)

            # If explicit DB name is provided, use it. Otherwise fall back to URI default.
            if self.db_name:
                self.db = self.client[self.db_name]
            else:
                self.db = self.client.get_database()

            self.collection = self.db.news
            self._ensure_indexes()
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def _ensure_indexes(self):
        """Creates necessary indexes for the news collection."""
        try:
            self.collection.create_index(
                [("source_url", ASCENDING)], unique=True, sparse=True
            )
            self.collection.create_index([("published_at", DESCENDING)])
            self.collection.create_index([("category", ASCENDING)])
            self.collection.create_index([("slug", ASCENDING)], unique=True)
        except Exception as e:
            logger.warning(f"Index creation failed (non-fatal): {e}")

    def is_duplicate(self, url: str) -> bool:
        """Checks if an article with the given URL already exists."""
        return self.collection.count_documents({"source_url": url}, limit=1) > 0

    def save_article(self, article: Dict[str, Any]) -> Optional[Any]:
        """Saves a news article to MongoDB."""
        try:
            # Ensure slug exists
            if "slug" not in article or not article["slug"]:
                # Simple Fallback slug generation if not provided (though main.py should handle it)
                import re

                slug = article["title"].lower()
                slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
                article["slug"] = f"{slug}-{int(datetime.now().timestamp())}"

            # Ensure translations is handled if present (optional validation)
            if "translations" not in article:
                article["translations"] = []

            result = self.collection.insert_one(article)
            logger.info(
                f"Saved article: {article.get('title', 'Unknown')} (ID: {result.inserted_id})"
            )
            return result.inserted_id
        except Exception as e:
            if "E11000 duplicate key error" in str(e):
                logger.warning(
                    f"Duplicate key error for article: {article.get('title')}"
                )
            else:
                logger.error(f"Error saving article: {e}")
            return None
