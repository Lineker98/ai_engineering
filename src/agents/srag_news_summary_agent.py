import json
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List, Optional
from pathlib import Path
from glob import glob
from datetime import timezone, datetime
import logging

from .schemas import (
    NewsSummaryState,
    NewsItemSummary,
    NewsExecutiveSummary,
    NewsArticleRaw,
)
from .prompt import PER_ARTICLE_SYSTEM, PER_ARTICLE_USER, AGG_SYSTEM, AGG_USER
from ..utils.helper_functions import save_json_atomic
from ..utils.logs_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
class SummaryAgent:
    """
    Agente de sumarização de notícias.

    Responsável por:
      - Carregar artigos (JSON único ou diretório com vários JSONs).
      - Normalizar chaves e deduplicar por URL.
      - Resumir cada artigo com LLM (saída estruturada em `NewsItemSummary`).
      - Agregar os resumos em um sumário executivo (`NewsExecutiveSummary`).
      - Persistir o resultado em JSON (metadados, resumos, sumário executivo e erros).
    """

    def __init__(self, model="gpt-4o-mini", temperature=0):
        """
        Inicializa o agente e compila as chains de LLM para: (i) resumo por artigo e (ii) agregação executiva.

        Args:
            model (str, optional): Nome do modelo a ser usado pelo LLM. Padrão: 'gpt-4o-mini'.
            temperature (int, optional): Temperatura do LLM (controle de aleatoriedade). Padrão: 0.
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self._per_article_chain = self._build_per_article_chain()
        self._aggegate_chain = self._build_aggregate_chain()
        self.model_name = model

    def _build_per_article_chain(self):
        """
        Constrói a chain de resumo por artigo.

        A chain recebe (title, source, published_at, url, text_or_snippet) e produz um
        `NewsItemSummary` via `with_structured_output`.

        Returns:
            Runnable: Pipeline de prompt + LLM para gerar `NewsItemSummary`.
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", PER_ARTICLE_SYSTEM), ("user", PER_ARTICLE_USER)]
        )
        return prompt | self.llm.with_structured_output(NewsItemSummary)

    def _build_aggregate_chain(self):
        """
        Constrói a chain de agregação executiva.

        A chain recebe um JSON com a lista de resumos (`summaries_json`) e devolve um
        `NewsExecutiveSummary` (visão geral, destaques, consensos, divergências e fontes).

        Returns:
            Runnable: Pipeline de prompt + LLM para gerar `NewsExecutiveSummary`.
        """
        prompt = ChatPromptTemplate([("system", AGG_SYSTEM), ("user", AGG_USER)])
        return prompt | self.llm.with_structured_output(NewsExecutiveSummary)

    @staticmethod
    def _coerce_article(article: Dict[str, Any]) -> NewsArticleRaw:
        """
        Converte um dicionário arbitrário de artigo para o schema `NewsArticleRaw`,
        preenchendo ausências com `None`.

        Args:
            article (Dict[str, Any]): Dicionário bruto de artigo.

        Returns:
            NewsArticleRaw: Objeto normalizado com campos esperados pelo agente.
        """
        return NewsArticleRaw(
            title=article.get("title"),
            url=article.get("url"),
            source=article.get("source"),
            published_at=article.get("published_at"),
            snippet=article.get("snippet"),
            text=article.get("text"),
        )

    @staticmethod
    def _pick_text_or_snippet(a: NewsArticleRaw, max_chars: int = 8000) -> str:
        """
        Seleciona o texto preferencial para sumarização: `text` (se existir) ou `snippet`.
        Corta para no máximo `max_chars` caracteres.

        Args:
            a (NewsArticleRaw): Artigo normalizado.
            max_chars (int, optional): Limite máximo de caracteres. Padrão: 8000.

        Returns:
            str: Conteúdo textual para o LLM, ou mensagem padrão caso ausente.
        """
        txt = (a.text or a.snippet or "").strip()
        if not txt:
            return "(sem conteúdo textual disponível)"
        return txt[:max_chars]

    @staticmethod
    def _extract_from_json_obj(obj: Any) -> List[Dict[str, Any]]:
        """
        Extrai a lista de artigos a partir de diferentes formatos de JSON.

        Aceita:
          - {"articles": [...]}  (formato preferido)
          - [...]                (lista direta de artigos)
        Ignora outros formatos.

        Args:
            obj (Any): Objeto JSON carregado.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários de artigos (possivelmente vazia).
        """
        if isinstance(obj, dict) and isinstance(obj.get("articles"), list):
            return obj["articles"]
        if isinstance(obj, list):
            return obj
        return []

    @staticmethod
    def _map_keys(article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza chaves de diferentes fontes (ex.: Serper, trafilatura) para o formato interno.

        Mapeamentos contemplados: title, url/link, source, published_at/date/publishedDate,
        snippet, text.

        Args:
            article (Dict[str, Any]): Artigo com chaves heterogêneas.

        Returns:
            Dict[str, Any]: Dicionário com chaves padronizadas.
        """
        return {
            "title": article.get("title"),
            "url": article.get("url") or article.get("link"),
            "source": article.get("source"),
            "published_at": article.get("published_at")
            or article.get("date")
            or article.get("publishedDate"),
            "snippet": article.get("snippet"),
            "text": article.get("text"),
        }

    def _load_articles_from_path(
        self, path: str | Path, recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Carrega artigos de um arquivo `.json` único OU de todos os `.json` em um diretório,
        normaliza as chaves e deduplica por URL (ou, se ausente, por título).

        Regras de deduplicação:
          - Mantém o item com `text` mais longo (conteúdo mais rico).

        Args:
            path (str | Path): Caminho para arquivo JSON ou pasta contendo JSONs.
            recursive (bool, optional): Se True, varre recursivamente a pasta. Padrão: True.

        Returns:
            List[Dict[str, Any]]: Lista de artigos normalizados e deduplicados.
        """
        p = Path(path)
        files: List[Path]
        if p.is_file():
            files = [p]
        else:
            pattern = "**/*.json" if recursive else "*.json"
            files = [Path(fp) for fp in glob(str(p / pattern), recursive=recursive)]

        all_items: List[Dict[str, Any]] = []
        for f in files:
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
                items = self._extract_from_json_obj(obj)
                if items:
                    all_items.extend(self._map_keys(it) for it in items)
            except Exception as e:
                print(f"[WARN] Falha ao ler {f}: {e}")

        # dedup por URL (ou título se URL ausente)
        dedup: Dict[str, Dict[str, Any]] = {}
        for it in all_items:
            key = (it.get("url") or "").strip() or (it.get("title") or "").strip()
            if not key:
                continue
            prev = dedup.get(key)
            if prev is None:
                dedup[key] = it
            else:
                if len((it.get("text") or "")) > len((prev.get("text") or "")):
                    dedup[key] = it
        return list(dedup.values())

    def node_load(self, state: NewsSummaryState) -> NewsSummaryState:
        """
        Nó opcional de carregamento: se `articles` não estiver no estado, tenta ler de `input_path`.

        Args:
            state (NewsSummaryState): Estado atual; pode conter `input_path` para leitura.

        Returns:
            NewsSummaryState: Estado com `articles` carregados, ou com `errors` em caso de falha.
        """
        if state.get("articles"):
            return {}

        input_path = state.get("input_path")
        if not input_path:
            return {}

        try:
            articles = self._load_articles_from_path(input_path)
            return {"articles": articles}
        except Exception as e:
            errs = list(state.get("errors") or [])
            errs.append(f"load: {e}")
            return {"errors": errs}

    def node_summarize(self, state: NewsSummaryState) -> NewsSummaryState:
        """
        Produz resumos estruturados para cada artigo presente em `state['articles']`,
        acumulando erros por índice de artigo quando houver exceções.

        Args:
            state (NewsSummaryState): Estado contendo `articles` (lista de dicts).

        Returns:
            NewsSummaryState: Estado com `summaries` (List[NewsItemSummary]) e `errors` (List[str]).
        """
        articles = state.get("articles") or []
        summaries: List[NewsItemSummary] = []
        errors = list(state.get("errors") or [])
        
        logging.info("Summarizing news by news.")
        for index, article_raw in enumerate(articles):
            try:
                article = self._coerce_article(article_raw)
                text_or_snippet = self._pick_text_or_snippet(article)
                summary = self._per_article_chain.invoke(
                    {
                        "title": article.title or "(Sem título)",
                        "source": article.source or "(sem fonte)",
                        "published_at": article.published_at or "(desconhecida)",
                        "url": article.url or "",
                        "text_or_snippet": text_or_snippet,
                    }
                )
                summaries.append(summary)
            except Exception as e:
                logging.error(f"Error {e} try to summarize nes {article.title} from {article.url}")
                errors.append(f"article_{index}: {e}")
        return {"summaries": summaries, "errors": errors}

    def node_executive_summary(self, state: NewsSummaryState) -> NewsSummaryState:
        """
        Agrega a lista de `summaries` em um `NewsExecutiveSummary`
        com objetivo de gerar um resumo com base em todos os outros
        resumos singulares de cada página. Se não houver resumos,
        retorna um objeto com mensagem padrão. Em exceção, registra o erro e retorna
        um sumário executivo vazio.

        Args:
            state (NewsSummaryState): Estado contendo `summaries` (List[NewsItemSummary]).

        Returns:
            NewsSummaryState: Estado com `executive_summary`, com resumos de todos
            os resumos de cada página e, se houver, `errors` atualizados.
        """
        summaries = state.get("summaries") or []
        if not summaries:
            executive_summary = NewsExecutiveSummary(
                overall_summary="Nenhum artigo válido para reumir",
                highlights=[],
                consensus=None,
                disagreements=None,
                sources_covered=[],
            )
            return {"executive_summary": executive_summary}

        logging.info("Start to summarize all news summary")
        try:
            summaries_json = json.dumps(
                [summary.model_dump() for summary in summaries], ensure_ascii=False
            )
            executive_summary = self._aggegate_chain.invoke(
                {"summaries_json": summaries_json}
            )
            return {"executive_summary": executive_summary}
        except Exception as e:
            logging.error(f"Error trying to summarize all news summary {e}")
            errors = list(state.get("errors") or [])
            errors.append(f"aggregate: {e}")
            executive_summary = NewsExecutiveSummary(
                overall_summary="Falha ao agregar os resumos.",
                highlights=[],
                consensus=None,
                disagreements=None,
                sources_covered=[],
            )
            return {"executive_summary": executive_summary, "errors": errors}

    def node_save(self, state: NewsSummaryState) -> NewsSummaryState:
        """
        Persiste os artefatos gerados em `save_dir/news_summaries.json`.

        Estrutura salva:
          - meta: generated_at, model e metadados adicionais do estado (`meta`)
          - summaries: lista serializada de `NewsItemSummary` ou seja, resumos unitários.
          - executive_summary: `NewsExecutiveSummary` ou seja, resumo geral
          - errors: lista de mensagens de erro

        Args:
            state (NewsSummaryState): Estado contendo `save_dir`, `summaries`, `executive_summary` e `errors`.

        Returns:
            NewsSummaryState: Dicionário vazio em sucesso; estado com `errors` se houver falha.
        """
        output_dir = state.get("save_dir")
        if not output_dir:
            return {}

        logging.error("Saving news report!")
        try:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            payload = {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "model": self.model_name,
                    **(state.get("meta") or {}),
                },
                "summaries": [
                    summary.model_dump() for summary in state.get("summaries") or []
                ],
                "executive_summary": (
                    state.get("executive_summary").model_dump()
                    if state.get("executive_summary")
                    else None
                ),
                "errors": state.get("errors") or [],
            }
            save_json_atomic(payload, path / "news_summaries.json")
        except Exception as e:
            logging.error(f"Error trying to save news report {e}")
            errors = list(state.get("errors") or [])
            errors.append(f"save: {e}")
            return {"errors": errors}

        return {}

    def build_graph(self):
        """
        Constrói o grafo do pipeline de sumarização/agragação/salvamento.

        Fluxo:
          START -> summarize_news -> executive_summary -> save_outputs -> END

        Returns:
            Runnable: Aplicação compilada do LangGraph pronta para `invoke`.
        """
        graph = StateGraph(NewsSummaryState)
        graph.add_node("summarize_news", self.node_summarize)
        graph.add_node("executive_summary", self.node_executive_summary)
        graph.add_node("save_outputs", self.node_save)

        graph.add_edge(START, "summarize_news")
        graph.add_edge("summarize_news", "executive_summary")
        graph.add_edge("executive_summary", "save_outputs")
        graph.add_edge("save_outputs", END)

        return graph.compile()

    def run_from_articles(
        self,
        articles: List[Dict[str, Any]],
        save_dir: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa o pipeline a partir de uma lista de artigos em memória.

        Args:
            articles (List[Dict[str, Any]]): Lista de artigos (dicts) já disponíveis.
            save_dir (Optional[str], optional): Diretório para salvar o JSON de saída. Padrão: None.
            meta (Optional[Dict[str, Any]], optional): Metadados adicionais a incluir no arquivo. Padrão: None.

        Returns:
            Dict[str, Any]: Dicionário com `summaries`, `executive_summary` e `errors` produzidos pelo pipeline.
        """
        app = self.build_graph()
        init: NewsSummaryState = {
            "articles": articles,
            "save_dir": save_dir,
            "meta": meta or {},
            "errors": [],
        }
        out = app.invoke(init)
        graph_image = app.get_graph(xray=True).draw_mermaid_png()
        with open("diagrams/SummaryAgent.png", "wb") as f:
            f.write(graph_image)
        return {
            "summaries": out.get("summaries", []),
            "executive_summary": out.get("executive_summary"),
            "errors": out.get("errors", []),
        }

    def run(
        self,
        news_json_path: str | Path,
        save_dir: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executa o pipeline lendo artigos de um arquivo JSON..

        O arquivo deve conter ao menos a chave `articles` com uma lista de itens.

        Args:
            news_json_path (str | Path): Caminho do arquivo JSON com artigos (`{"articles": [...]}`).
            save_dir (Optional[str], optional): Diretório de saída para persistência dos resultados. Padrão: None.
            meta (Optional[Dict[str, Any]], optional): Metadados adicionais a incluir no payload salvo. Padrão: None.

        Returns:
            Dict[str, Any]: Dicionário com `summaries`, `executive_summary` e `errors` produzidos pelo pipeline.
        """
        logging.info("EXECUTING NEWS SUMMARIZER AGENT")
        path = Path(news_json_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        articles = data.get("articles", [])
        return self.run_from_articles(articles, save_dir=save_dir, meta=meta)
