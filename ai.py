import json
import logging
import os
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

_SYSTEM_PROMPT = "You are a tech news editor and analyst."


def _coerce_to_dict(parsed: Any) -> Optional[Dict]:
    # LLMs occasionally return a top-level JSON array even with json_object mode
    # set — drop list-only responses; unwrap a 1-element list of dicts.
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        return parsed[0]
    logger.warning(
        f"AI response is not a dict (got {type(parsed).__name__}); skipping."
    )
    return None


def _build_prompt(title: str, content: str) -> str:
    return f"""
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
        Content: {content[:4000]}

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


class NewsAI:
    """Article processing with Groq (Llama) as the primary provider and the
    Gemini API as fallback — mirrors the job_scraper LLM strategy.

    The OpenAI configuration is kept (constructor args + OPENAI_API_KEY read)
    so it can be reused later, but it is intentionally not exercised here.
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-4o-mini",
        timeout: int = 120,
    ):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_model = groq_model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.gemini_model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        # Retained for future reuse; not called.
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_model = openai_model
        self.timeout = timeout

        if not self.groq_api_key and not self.gemini_api_key:
            logger.warning(
                "Neither GROQ_API_KEY nor GEMINI_API_KEY set; AI processing disabled."
            )

    def process_article(self, title: str, content: str) -> Optional[Dict]:
        """Summarize, categorize, tag and translate the article.

        Returns a dict on success, None if every available provider fails.
        """
        prompt = _build_prompt(title, content)

        if self.groq_api_key:
            result = self._call_groq(prompt)
            if result is not None:
                return result
            logger.warning("Groq processing failed; falling back to Gemini.")

        if self.gemini_api_key:
            return self._call_gemini(prompt)

        logger.warning("No AI provider available; skipping AI processing.")
        return None

    def _call_groq(self, prompt: str) -> Optional[Dict]:
        try:
            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                    "max_tokens": 8000,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return _coerce_to_dict(json.loads(content))
        except Exception as e:
            logger.error(f"Error processing news with Groq: {e}")
            return None

    def _call_gemini(self, prompt: str) -> Optional[Dict]:
        try:
            resp = requests.post(
                GEMINI_URL.format(model=self.gemini_model),
                params={"key": self.gemini_api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.2,
                        "maxOutputTokens": 8000,
                    },
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return _coerce_to_dict(json.loads(text))
        except Exception as e:
            logger.error(f"Error processing news with Gemini: {e}")
            return None
