import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class NewsScraper:
    def __init__(self):
        self.headers = {"User-Agent": "ITJobHub-NewsScraper/1.0"}

    def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """Fetches and parses an RSS feed using BeautifulSoup."""
        logger.info(f"Fetching feed: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Try parsing as XML
            soup = BeautifulSoup(response.content, "xml")

            articles = []

            # Detect RSS vs Atom
            items = soup.find_all("item")  # RSS
            if not items:
                items = soup.find_all("entry")  # Atom

            feed_title = "Unknown Source"
            if soup.channel and soup.channel.title:
                feed_title = soup.channel.title.text
            elif soup.feed and soup.feed.title:
                feed_title = soup.feed.title.text

            for entry in items:
                article = self._normalize_entry(entry, feed_title)
                if article:
                    articles.append(article)

            logger.info(f"Found {len(articles)} articles in {url}")
            return articles
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
            return []

    def _normalize_entry(self, entry: Any, source_name: str) -> Dict[str, Any]:
        """Normalizes an RSS/Atom entry into a standard dictionary."""
        try:
            title = entry.title.text if entry.title else "No Title"
            link = ""
            if entry.link:
                # Atom: <link href="..." /> or RSS: <link>...</link>
                if entry.link.get("href"):
                    link = entry.link.get("href")
                else:
                    link = entry.link.text

            # Content
            content = ""
            description = entry.find("description")
            content_encoded = entry.find("content:encoded")
            content_tag = entry.find("content")  # Atom

            if content_encoded:
                content = content_encoded.text
            elif content_tag:
                content = content_tag.text
            elif description:
                content = description.text

            # Date
            published_at = datetime.now()
            pub_date = entry.find("pubDate")
            published = entry.find("published")
            updated = entry.find("updated")

            date_str = ""
            if pub_date:
                date_str = pub_date.text
            elif published:
                date_str = published.text
            elif updated:
                date_str = updated.text

            if date_str:
                try:
                    # Try RFC 822 (RSS)
                    published_at = parsedate_to_datetime(date_str)
                except:
                    # Try ISO 8601 (Atom) - simplified
                    try:
                        from dateutil import parser

                        published_at = parser.parse(date_str)
                    except:
                        pass  # Keep now()

            # Ensure timezone-aware datetime is converted to naive or handled consistently if needed
            # For simplicity, we keep it as is, MongoDB handles dates well.

            guid = ""
            guid_tag = entry.find("guid")
            id_tag = entry.find("id")
            if guid_tag:
                guid = guid_tag.text
            elif id_tag:
                guid = id_tag.text
            else:
                guid = link

            author = "Unknown"
            author_tag = entry.find("dc:creator") or entry.find("author")
            if author_tag:
                if author_tag.name == "author" and author_tag.find("name"):
                    author = author_tag.find("name").text
                else:
                    author = author_tag.text

            return {
                "title": title,
                "source_url": link,
                "source_name": source_name,
                "content_raw": content,
                "author": author,
                "published_at": published_at,
                "guid": guid,
                "fetched_at": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Error normalizing entry: {e}")
            return None
