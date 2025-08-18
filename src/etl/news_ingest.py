from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from datetime import timezone

from ..utils.helper_functions import save_json_atomic
from ..utils.logs_config import setup_logging
from ..tools.news_fetcher_tool import NewsFetcherTool
import logging

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()


def save_news_results(
    articles: List[Dict], output_path: str, query: str, country="br", lang="pt-br"
) -> None:
    """
    Saves the crawled results (metadata + articles) to a JSON file.

    Args:
        articles (List[Dict]): The list of processed article dictionaries.
        output_path (str): The file path where the JSON will be saved.
        query (str): The original search query used.
        country (str, optional): The country code used for the search. Defaults to "br".
        lang (str, optional): The language code used for the search. Defaults to "pt-br".
    """
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "country": country,
            "lang": lang,
            "count": len(articles),
            "source": "serper.google.news",
        },
        "articles": articles,
    }
    logger.info(f"Saving SRAG news JSON at {output_path}.")
    save_json_atomic(payload=payload, output_path=output_path)


def ingest_srag_news(
    fetcher_api_key: str, query: str, output_path: str, top_k: int = 5
) -> List[Dict]:
    """
    Main pipeline for ingesting news about SRAG.

    This function orchestrates the process of searching, fetching, parsing, and saving news articles
    by using the NewsFetcherTool to handle external interactions.

    Args:
        query (str): The search term for finding relevant news.
        output_path (str): The path to save the final JSON file with the processed articles.
        top_k (int, optional): The maximum number of articles to process. Defaults to 5.

    Returns:
        List[Dict]: A list of the processed article dictionaries.
    """
    # 1. Initialize the tool
    news_tool = NewsFetcherTool(api_key=fetcher_api_key)

    # 2. Use the tool to search for news
    search_results = news_tool.search_news(query, num_results=top_k)

    processed_articles = []
    logger.info(f"Fetching and parsing {len(search_results)} articles.")

    for item in search_results:
        url = item.get("link")
        if not url:
            continue

        # 3. Use the tool to fetch HTML
        html = news_tool.fetch_article_html(url)

        # If fetching fails, keep the basic search metadata
        if not html:
            processed_articles.append(
                {
                    "title": item.get("title"),
                    "url": url,
                    "source": item.get("source"),
                    "date_from_search": item.get("date"),
                    "snippet": item.get("snippet"),
                    "text": None,
                }
            )
            continue

        # 4. Use the tool to parse the article
        parsed_content = news_tool.parse_article_content(html)

        # 5. Combine search metadata with parsed content
        processed_articles.append(
            {
                "title": parsed_content.get("title") or item.get("title"),
                "url": url,
                "source": item.get("source"),
                "published_at": parsed_content.get("published_at") or item.get("date"),
                "snippet": item.get("snippet"),
                "text": parsed_content.get("text"),
            }
        )

    # 6. Save the final results
    save_news_results(articles=processed_articles, output_path=output_path, query=query)

    return processed_articles
