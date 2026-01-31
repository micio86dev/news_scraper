import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class NewsScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_full_content(self, url: str) -> str:
        """Fetches the full HTML of a page and extracts the main content."""
        logger.info(f"Fetching full content from: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove noise
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            # Strategy 1: Look for common article containers
            article = soup.find("article")
            if not article:
                # Strategy 2: Look for common class/id patterns
                article = soup.find(
                    class_=lambda x: x
                    and ("content" in x or "post" in x or "article" in x)
                )

            if article:
                return self._clean_html(str(article))

            # Fallback: Cleaned body
            return self._clean_html(str(soup.body))
        except Exception as e:
            logger.error(f"Error fetching full content from {url}: {e}")
            return ""

    def _clean_html(self, html_content: str) -> str:
        """Strips HTML tags and returns clean text."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Get text, using newline as separator for block elements
        text = soup.get_text(separator="\n")

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        # Re-join with single newlines
        return "\n".join(line for line in lines if line)

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
                    # Try ISO 8601 (Atom) and other formats
                    try:
                        clean_date = date_str.replace("Z", "+00:00")
                        published_at = datetime.fromisoformat(clean_date)
                    except Exception as e:
                        logger.warning(f"Failed to parse date '{date_str}': {e}")
                        # Fallback to regex for YYYY-MM-DD
                        import re

                        match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
                        if match:
                            published_at = datetime.strptime(match.group(1), "%Y-%m-%d")
                        else:
                            published_at = datetime.now()
                        logger.warning(f"Failed to parse date '{date_str}': {e}")
                        published_at = datetime.now()

            # Ensure timezone-aware datetime is converted to naive UTC for consistent comparison if needed
            # or Ensure it's compared correctly. For now, let's keep it and handle in main.py.
            # If the published_at has no tzinfo, it's naive.

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
                "content": self._clean_html(content),
                "author": author,
                "published_at": published_at,
                "guid": guid,
                "fetched_at": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Error normalizing entry: {e}")
            return None
