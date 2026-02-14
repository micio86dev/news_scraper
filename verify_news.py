import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv


def verify():
    load_dotenv()
    db_url = (
        os.getenv("MONGO_URI_STAGE")
        or os.getenv("MONGO_URI_PROD")
        or os.getenv("DATABASE_URL")
        or os.getenv("MONGO_URI")
        or os.getenv("MONGODB_URI")
    )
    if not db_url:
        print(
            "❌ MongoDB connection URL not found (checked MONGO_URI_STAGE, MONGO_URI_PROD, DATABASE_URL, MONGO_URI, MONGODB_URI)"
        )
        return

    # Log attempt (obfuscated)
    safe_uri = db_url.split("@")[-1] if "@" in db_url else db_url
    print(f"🔌 Testing connection to MongoDB at {safe_uri}...")

    # Smart Fallback Logic for Verification
    try:
        client = MongoClient(db_url, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ Connection successful")
    except Exception as e:
        is_stage = "stage" in db_url
        if "localhost" in db_url and "27017" in db_url and is_stage:
            print(
                f"⚠️ Connection to localhost:27017 failed. Retrying on port 27018 (Smart Fallback)..."
            )
            fallback_url = db_url.replace("27017", "27018")
            try:
                client = MongoClient(
                    fallback_url,
                    serverSelectionTimeoutMS=5000,
                    directConnection=True,
                    authSource="admin",
                )
                client.admin.command("ping")
                print("✅ Fallback connection to localhost:27018 successful")
            except Exception as fallback_e:
                print(f"❌ Fallback connection failed: {fallback_e}")
                return
        else:
            print(f"❌ Connection failed: {e}")
            return

    db = client.get_database()
    collection = db.news

    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)

    # Count ALL articles in DB
    total_count = collection.count_documents({})
    print(f"Total articles in DB: {total_count}")

    # Count articles added today (by fetched_at)
    count_today = collection.count_documents({"fetched_at": {"$gte": today_start}})
    print(f"Total articles added during today's sessions: {count_today}")

    # Check the latest 5 articles in DB
    articles = list(collection.find().sort("_id", -1).limit(5))

    languages = ["it", "en", "es", "de", "fr"]
    all_ok = True

    if not articles:
        print("FAILED: No articles found in DB.")
        all_ok = False

    for idx, art in enumerate(articles):
        print(f"Checking Article {idx+1}: {art.get('title')}")
        translations = art.get("translations", [])
        trans_langs = [t.get("language") for t in translations]

        missing = [l for l in languages if l not in trans_langs]
        if missing:
            print(f"  FAILED: Missing languages: {missing}")
            all_ok = False
        else:
            print(f"  OK: All languages present (it, en, es, de, fr).")

    # Consider it PASSED if at least 5 news items were added/present and translations are OK
    if all_ok and total_count >= 5:
        print("\nOVERALL VERIFICATION: PASSED")
    else:
        print("\nOVERALL VERIFICATION: FAILED")


if __name__ == "__main__":
    verify()
