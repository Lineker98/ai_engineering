import httpx
import trafilatura
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

from ..utils.helper_functions import save_json_atomic
from ..utils.logs_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

# TODO: Let this flexible to change by instantiating the class
SERPER_NEWS_URL = "https://google.serper.dev/news"
TIMEOUT = 20


class NewsFetcherTool:
    """
    A tool to handle searching, fetching, and parsing online news articles.
    Encapsulates interactions with external services like Serper and Trafilatura.
    """

    def __init__(self, api_key: str):
        """
        Initializes the tool with the necessary API key.

        Args:
            api_key (str): The API key for the Serper service.

        Raises:
            ValueError: If the API key is not provided.
        """
        if not api_key:
            raise ValueError("SERPER_API_KEY must be provided.")
        self.api_key = api_key
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def search_news(
        self, query: str, num_results: int = 5, country: str = "br", lang: str = "pt-br"
    ) -> List[Dict]:
        """
        Searches for news using the Serper API and returns normalized results.

        Args:
            query (str): The search term to be used (e.g., "SRAG site:gov.br").
            num_results (int, optional): The number of results to return (1-10). Defaults to 5.
            country (str, optional): The country code for the search. Defaults to "br".
            lang (str, optional): The language code for the search. Defaults to "pt-br".

        Returns:
            List[Dict]: A list of dictionaries, each representing a news article from the search.
        """
        logger.info(f"Searching news with query: '{query}'")
        payload = {
            "q": query,
            "gl": country,
            "hl": lang,
            "num": max(1, min(10, num_results)),
        }

        try:
            with httpx.Client(timeout=TIMEOUT, headers=self.headers) as client:
                r = client.post(SERPER_NEWS_URL, json=payload)
                r.raise_for_status()
                data = r.json()
                items = data.get("news", [])[:num_results]
                return [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "source": it.get("source"),
                        "date": it.get("date") or it.get("publishedDate"),
                        "snippet": it.get("snippet"),
                    }
                    for it in items
                ]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during news search: {e}")
            return []

    def fetch_article_html(self, url: str) -> Optional[str]:
        """
        Downloads the raw HTML from a URL, mimicking a browser.

        Args:
            url (str): The URL of the article to fetch.

        Returns:
            Optional[str]: The HTML content as a string, or None if fetching fails or content is not HTML.
        """
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            with httpx.Client(
                timeout=TIMEOUT, follow_redirects=True, headers=browser_headers
            ) as client:
                r = client.get(url)
                r.raise_for_status()
                if "text/html" in r.headers.get("Content-Type", ""):
                    return r.text
                logger.warning(f"Content at {url} is not HTML.")
                return None
        except httpx.RequestError as e:
            logger.error(f"Network error fetching {url}: {e}")
            return None

    def parse_article_content(self, html: str) -> Dict:
        """
        Extracts text and metadata from HTML using Trafilatura.

        Args:
            html (str): The raw HTML content of an article page.

        Returns:
            Dict: A dictionary containing the extracted title, publication date, and text.
        """
        text_content = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_recall=True,
            with_metadata=True,
        )
        metadata = trafilatura.metadata.extract_metadata(html)

        published_at = None
        if metadata and metadata.date:
            try:
                dt_object = datetime.fromisoformat(metadata.date.replace("Z", "+00:00"))
                published_at = dt_object.isoformat()
            except (ValueError, TypeError):
                published_at = None  # Keep it as None if parsing fails

        return {
            "title": metadata.title if metadata else None,
            "published_at": published_at,
            "text": text_content,
        }
