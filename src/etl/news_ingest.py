import os
from typing import List, Dict, Optional
import httpx
from datetime import datetime
from dotenv import load_dotenv
import trafilatura
from datetime import timezone

from ..utils.helper_functions import save_json_atomic


load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_NEWS_URL = "https://google.serper.dev/news"
TIMEOUT = 20

def search_serper_news(query: str, num_results: int = 5, country: str = "br", lang: str = "pt-br") -> List[Dict]:
    """_summary_

    Args:
        query (str): _description_
        num_results (int, optional): _description_. Defaults to 5.
        country (str, optional): _description_. Defaults to "br".
        lang (str, optional): _description_. Defaults to "pt-BR".

    Raises:
        RuntimeError: _description_

    Returns:
        List[Dict]: _description_
    """
    if not SERPER_API_KEY:
        raise RuntimeError("Defina SERPER_API_KEY no .env")

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "gl": country,
        "hl": lang,
        "num": max(1, min(10, num_results)) 
    }

    with httpx.Client(timeout=TIMEOUT, headers=headers) as client:
        r = client.post(SERPER_NEWS_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        items = data.get("news", [])[:num_results]
        
        # normaliza campos mínimos
        parsed = []
        for it in items:
            parsed.append({
                "title": it.get("title"),
                "link": it.get("link"),
                "source": it.get("source"),
                "date": it.get("date") or it.get("publishedDate"),
                "snippet": it.get("snippet"),
            })
        return parsed
    

def fetch_html(url: str) -> Optional[str]:
    """_summary_

    Args:
        url (str): _description_

    Returns:
        Optional[str]: _description_
    """
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "")
            if "text/html" not in ct:
                return None
            return r.text
    except httpx.HTTPError:
        return None
    

def parse_article(html: str) -> Dict:
    """_summary_

    Args:
        html (str): _description_

    Returns:
        Dict: _description_
    """
    # inclui metadados no texto; se quiser só conteúdo, use without_metadata=True
    text = trafilatura.extract(html, include_comments=False, include_tables=False, favor_recall=True, with_metadata=True)
    meta = trafilatura.metadata.extract_metadata(html)

    title = meta.title if meta else None
    published_at = None
    if meta and meta.date:
        # tenta normalizar ISO
        try:
            published_at = datetime.fromisoformat(meta.date.replace("Z", "+00:00"))
        except Exception:
            published_at = None

    return {
        "title": title,
        "published_at": published_at.isoformat() if published_at else None,
        "text": text,
    }
    
def save_news_results(articles: List[Dict], output_path: str, query: str, country="br", lang="pt-bt") -> None:
    """_summary_

    Args:
        articles (List[Dict]): _description_
        output_path (str): _description_
        query (str): _description_
        country (str, optional): _description_. Defaults to "br".
        lang (str, optional): _description_. Defaults to "pt-bt".
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
    
    return save_json_atomic(payload=payload, output_path=output_path)
    

def ingest_srag_news(query: str, output_path: str, top_k: int = 5) -> List[Dict]:
    """
    Pipeline simples: busca no Serper -> pega até K links -> baixa HTML -> extrai conteúdo.
    Retorna uma lista de dicts pronta para ser resumida por IA.
    """
    results = search_serper_news(query, num_results=top_k)
    out = []
    for item in results:
        url = item.get("link")
        if not url:
            continue
        html = fetch_html(url)
        if not html:
            # mantém pelo menos metadados da busca
            out.append({
                "title": item.get("title"),
                "url": url,
                "source": item.get("source"),
                "date_from_search": item.get("date"),
                "text": None
            })
            continue

        parsed = parse_article(html)
        out.append({
            "title": parsed.get("title") or item.get("title"),
            "url": url,
            "source": item.get("source"),
            "published_at": parsed.get("published_at") or item.get("date"),
            "snippet": item.get("snippet"),
            "text": parsed.get("text"),
        })
        
    save_news_results(articles=out, output_path=output_path, query=query)
    return out
    