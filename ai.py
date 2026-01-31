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
        Analyze the following technical article and extract the required information in JSON format.

        CRITICAL: This scraper is STRICTLY for an assumption-free "DevBoards.io" for developers and software engineers.
        We ONLY want news related to:
        - Programming languages and frameworks (Python, JS, Rust, React, etc.)
        - Software development practices (Architecture, Agile, Testing)
        - DevOps, Cloud (AWS/Azure/GCP), and Infrastructure
        - Cybersecurity (technical)
        - Artificial Intelligence & Machine Learning (technical/development focus)
        - Database technologies

        EXCLUDE specifically:
        - Consumer electronics (Phones, Laptops, Headphones, Electric Bikes, Gadgets)
        - General "Tech" news (Social media policy, generic business news, video games)
        - Science news unrelated to computing

        Title: {title}
        Content: {content[:10000]}

        Output Fields:
        - is_relevant: Boolean (true if it matches the inclusion criteria above, false otherwise).
        - summary: A concise summary of the article (max 2-3 sentences) in the original language.
        - category: The primary category (e.g., "AI", "DevOps", "Cybersecurity", "Development", "Cloud", "Data Science", "Blockchain").
        - tags: A list of relevant technical tags (max 5).
        - language: The language of the article ("en", "it", etc.).
        - sentiment: "positive", "neutral", or "negative".
        - translations: An array of exactly 5 objects, one for each supported language: en, it, es, de, fr. 
          CRITICAL: YOU MUST INCLUDE ALL 5 LANGUAGES (EN, IT, ES, DE, FR) IN THE LIST WITHOUT EXCEPTION. 
          Even if the original article is in English, you MUST include an "en" entry with the original content.
          Each language object must have:
            - language: "en" | "it" | "es" | "de" | "fr"
            - title: Translated title
            - summary: Translated summary
            - content: A detailed, full-length translated version of the article body. Use Markdown for formatting (headers, lists, bold text) where appropriate to make it readable.

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
