import os
from typing import List, Dict, Optional
import httpx
from datetime import datetime
from dotenv import load_dotenv
import trafilatura
from datetime import timezone

from ..utils.helper_functions import save_json_atomic
from ..utils.logs_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_NEWS_URL = "https://google.serper.dev/news"
TIMEOUT = 20


def search_serper_news(
    query: str, num_results: int = 5, country: str = "br", lang: str = "pt-br"
) -> List[Dict]:
    """Consulta a API do Serper (Google News) e retorna notícias normalizadas.

    A requisição é feita via HTTP POST para o endpoint de notícias do Serper,
    respeitando um limite de 1–10 resultados. Os campos de cada item são
    normalizados para um subconjunto mínimo útil ao pipeline.

    Args:
        query (str): Termo de busca (por exemplo, "SRAG site:gov.br").
        num_results (int, optional): Quantidade de itens a retornar (1–10).
            Defaults to 5.
        country (str, optional): Código do país (gl). Defaults to "br".
        lang (str, optional): Código de idioma (hl). Defaults to "pt-br".

    Returns:
        List[Dict]: Lista de dicionários com chaves:
            - ``title`` (str | None)
            - ``link`` (str | None)
            - ``source`` (str | None)
            - ``date`` (str | None) — data retornada pelo Serper
            - ``snippet`` (str | None)
    """
    logger.info(f"Searching news with Serper API.")
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
        "num": max(1, min(10, num_results)),
    }

    with httpx.Client(timeout=TIMEOUT, headers=headers) as client:
        r = client.post(SERPER_NEWS_URL, json=payload)
        r.raise_for_status()
        data = r.json()
        items = data.get("news", [])[:num_results]

        # normaliza campos mínimos
        parsed = []
        for it in items:
            parsed.append(
                {
                    "title": it.get("title"),
                    "link": it.get("link"),
                    "source": it.get("source"),
                    "date": it.get("date") or it.get("publishedDate"),
                    "snippet": it.get("snippet"),
                }
            )
        return parsed


def fetch_html(url: str) -> Optional[str]:
    """Baixa o HTML bruto de uma URL, seguindo redirecionamentos.

    Retorna ``None`` se a resposta não for ``text/html`` ou se ocorrer
    algum erro de rede/HTTP.

    Args:
        url (str): URL do artigo/notícia.

    Returns:
        Optional[str]: Conteúdo HTML como string, ou ``None`` quando indisponível.
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
    """Extrai texto e metadados de um HTML de notícia usando o trafilatura.

    Faz uma tentativa de normalizar a data de publicação para ISO 8601
    (timezone-aware) quando a biblioteca conseguir identificar a data.

    Args:
        html (str): HTML bruto do documento.

    Returns:
        Dict: Dicionário com chaves:
            - ``title`` (str | None): Título inferido pelos metadados.
            - ``published_at`` (str | None): Data ISO 8601 (UTC offset) se detectada.
            - ``text`` (str | None): Texto extraído (inclui metadados no corpo).
    """
    # inclui metadados no texto; se quiser só conteúdo, use without_metadata=True
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
        with_metadata=True,
    )
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


def save_news_results(
    articles: List[Dict], output_path: str, query: str, country="br", lang="pt-bt"
) -> None:
    """Salva em JSON os resultados do *crawl* (metadados + artigos).

    A função cria um payload com metadados de geração (timestamp UTC,
    parâmetros da busca e contagem de itens) e a lista de artigos, então
    persiste via ``save_json_atomic``.

    Args:
        articles (List[Dict]): Lista de artigos (cada item é um dict já normalizado).
        output_path (str): Caminho de saída do arquivo JSON (arquivo ou diretório).
        query (str): Termo de busca utilizado.
        country (str, optional): Código do país (gl). Defaults to "br".
        lang (str, optional): Código de idioma (hl). Defaults to "pt-bt".

    Returns:
        None: Efeito colateral é a criação/atualização do arquivo JSON.
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
    return save_json_atomic(payload=payload, output_path=output_path)


def ingest_srag_news(query: str, output_path: str, top_k: int = 5) -> List[Dict]:
    """Pipeline de ingestão de notícias sobre SRAG.

    Fluxo:
      1) Busca notícias no Serper (Google News).
      2) Seleciona até ``top_k`` itens e tenta baixar o HTML de cada link.
      3) Extrai texto/título/data com trafilatura quando possível.
      4) Salva um JSON com metadados e lista de artigos.
      5) Retorna a lista de artigos (prontos para sumarização por IA).

    Args:
        query (str): Termo de pesquisa (ex.: "SRAG site:saude.gov.br").
        output_path (str): Caminho onde o JSON consolidado será salvo.
        top_k (int, optional): Quantidade máxima de artigos a processar. Defaults to 5.

    Returns:
        List[Dict]: Lista de artigos com chaves típicas:
            - ``title`` (str | None)
            - ``url`` (str)
            - ``source`` (str | None)
            - ``published_at`` (str | None) ou ``date_from_search`` quando parsing falhar
            - ``snippet`` (str | None)
            - ``text`` (str | None)
    """
    results = search_serper_news(query, num_results=top_k)
    out = []
    logger.info(f"Fetch and Parsing SRAG news.")
    for item in results:
        url = item.get("link")
        if not url:
            continue
        html = fetch_html(url)
        if not html:
            # mantém pelo menos metadados da busca
            out.append(
                {
                    "title": item.get("title"),
                    "url": url,
                    "source": item.get("source"),
                    "date_from_search": item.get("date"),
                    "text": None,
                }
            )
            continue

        parsed = parse_article(html)
        out.append(
            {
                "title": parsed.get("title") or item.get("title"),
                "url": url,
                "source": item.get("source"),
                "published_at": parsed.get("published_at") or item.get("date"),
                "snippet": item.get("snippet"),
                "text": parsed.get("text"),
            }
        )

    save_news_results(articles=out, output_path=output_path, query=query)
    return out
