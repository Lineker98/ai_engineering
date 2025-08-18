from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from datetime import timezone
import os

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
    """_summary_

    Args:
        articles (List[Dict]): _description_
        output_path (str): _description_
        query (str): _description_
        country (str, optional): _description_. Defaults to "br".
        lang (str, optional): _description_. Defaults to "pt-br".
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


def ingest_srag_news(fetcher_api_key: str, query: str, output_path: str, top_k: int = 5) -> List[Dict]:
    """
    Main pipeline for ingesting news about SRAG.
    This function now uses the NewsFetcherTool to handle external interactions.
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
            processed_articles.append({
                "title": item.get("title"),
                "url": url,
                "source": item.get("source"),
                "date_from_search": item.get("date"),
                "snippet": item.get("snippet"),
                "text": None,
            })
            continue

        # 4. Use the tool to parse the article
        parsed_content = news_tool.parse_article_content(html)
        
        # 5. Combine search metadata with parsed content
        processed_articles.append({
            "title": parsed_content.get("title") or item.get("title"),
            "url": url,
            "source": item.get("source"),
            "published_at": parsed_content.get("published_at") or item.get("date"),
            "snippet": item.get("snippet"),
            "text": parsed_content.get("text"),
        })

    # 6. Save the final results
    save_news_results(articles=processed_articles, output_path=output_path, query=query)
    
    return processed_articles