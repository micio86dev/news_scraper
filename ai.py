import json
import logging
import os
from typing import Dict, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class NewsAI:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def process_article(self, title: str, content: str) -> Optional[Dict]:
        """
        Uses OpenAI to summarize, categorize, and tag the article.
        Returns a dictionary with processed data.
        """
        if not self.client:
            logger.warning("OpenAI client not initialized. Skipping AI processing.")
            return None

        prompt = f"""
        Analyze the following IT news article and extract/generate the required information in JSON format.

        Title: {title}
        Content Snippet: {content[:3000]} # Limit content to avoid token limits

        Output Fields:
        - summary: A concise summary of the article (max 2-3 sentences) in the same language of the article.
        - category: The primary category (e.g., "AI", "DevOps", "Cybersecurity", "Development", "Cloud", "Hardware", "Mobile", "Data Science", "Blockchain", "General").
        - tags: A list of relevant technical tags (max 5).
        - language: The language of the article ("en", "it", etc.).
        - sentiment: "positive", "neutral", or "negative".

        Return ONLY valid JSON.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a tech news editor and analyst.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"Error processing news with AI: {e}")
            return None
