import logging
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url: Optional[str] = None, db_name: Optional[str] = None):
        # Env Priority: Stage/Prod specific > DATABASE_URL (legacy/local) > MONGODB_URI (generic)
        self.db_url = (
            db_url
            or os.getenv("MONGO_URI_STAGE")
            or os.getenv("MONGO_URI_PROD")
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

            # Smart Connection Logic for Stage on Localhost
            # Issue: If 27017 (Prod) is running, the scraper connects to it by default even if we want Stage.
            # Fix: If we detect 'stage' in DB/URI and we are on localhost:27017, FORCE 27018.
            is_stage = (self.db_name and "stage" in self.db_name) or (
                "stage" in self.db_url
            )

            if "localhost" in self.db_url and "27017" in self.db_url and is_stage:
                logger.info("🕵️‍♂️ DETECTED STAGE ENVIRONMENT ON LOCALHOST:27017")
                logger.warning(
                    "🚀 PROACTIVELY SWITCHING TO PORT 27018 TO AVOID PRODUCTION DB!"
                )

                self.db_url = self.db_url.replace("27017", "27018")
                # We must use directConnection=True to bypass replica set discovery if any
                self.client = MongoClient(
                    self.db_url, directConnection=True, authSource="admin"
                )
            else:
                # Standard connection
                self.client = MongoClient(self.db_url)

            # Trigger connection with Ping
            try:
                self.client.admin.command("ping")
                logger.info(f"✅ Connection successful to {self.db_url.split('@')[-1]}")
            except Exception as e:
                # Fallback: Check if we are on 27018 and it failed, maybe revert or just log
                logger.error(f"❌ Connection failed: {e}")
                raise e

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
