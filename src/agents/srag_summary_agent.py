import json
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from typing import Dict, Any, List, Optional
from pathlib import Path
from glob import glob
from datetime import timezone, datetime

from .schemas import (
    NewsSummaryState,
    NewsItemSummary,
    NewsExecutiveSummary,
    NewsArticleRaw
)
from .prompt import (
    PER_ARTICLE_SYSTEM,
    PER_ARTICLE_USER,
    AGG_SYSTEM,
    AGG_USER
)
from ..utils.helper_functions import save_json_atomic

class SummaryAgent:
    
    def __init__(self, model='gpt-4o-mini', temperature=0):
        """_summary_

        Args:
            model (str, optional): _description_. Defaults to 'gpt-4o-mini'.
            temperature (int, optional): _description_. Defaults to 0.
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self._per_article_chain = self._build_per_article_chain()
        self._aggegate_chain = self._build_aggregate_chain()
        self.model_name = model
        
    def _build_per_article_chain(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", PER_ARTICLE_SYSTEM), ("user", PER_ARTICLE_USER)]
        )
        return prompt | self.llm.with_structured_output(NewsItemSummary)
    
    def _build_aggregate_chain(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        prompt = ChatPromptTemplate(
            [("system", AGG_SYSTEM), ("user", AGG_USER)]
        )
        return prompt | self.llm.with_structured_output(NewsExecutiveSummary)
    
    @staticmethod
    def _coerce_article(article: Dict[str, Any]) -> NewsArticleRaw:
        """_summary_

        Args:
            article (Dict[str, Any]): _description_

        Returns:
            NewsArticleRaw: _description_
        """
        return NewsArticleRaw(
            title=article.get('title'),
            url=article.get('url'),
            source=article.get('source'),
            published_at=article.get('published_at'),
            snippet=article.get('snippet'),
            text=article.get('text'),
        )
        
    @staticmethod
    def _pick_text_or_snippet(a: NewsArticleRaw, max_chars: int = 8000) -> str:
        """_summary_

        Args:
            a (NewsArticleRaw): _description_
            max_chars (int, optional): _description_. Defaults to 8000.

        Returns:
            str: _description_
        """
        txt = (a.text or a.snippet or "").strip()
        if not txt:
            return "(sem conteúdo textual disponível)"
        return txt[:max_chars]
    
    @staticmethod
    def _extract_from_json_obj(obj: Any) -> List[Dict[str, Any]]:
        """
        Aceita formatos:
          - {"articles": [...]}   (nosso formato)
          - [...]                 (lista direta de artigos)
        Ignora outros formatos.

        Args:
            obj (Any): _description_

        Returns:
            List[Dict[str, Any]]: _description_
        """
        if isinstance(obj, dict) and isinstance(obj.get("articles"), list):
            return obj["articles"]
        if isinstance(obj, list):
            return obj
        return []

    @staticmethod
    def _map_keys(article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza chaves vindas de Serper/trafilatura para o formato esperado pelo agente.

        Args:
            article (Dict[str, Any]): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        return {
            "title": article.get("title"),
            "url": article.get("url") or article.get("link"),
            "source": article.get("source"),
            "published_at": article.get("published_at") or article.get("date") or article.get("publishedDate"),
            "snippet": article.get("snippet"),
            "text": article.get("text"),
        }

    def _load_articles_from_path(self, path: str | Path, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Lê um arquivo .json ou uma pasta (varios .json), normaliza e deduplica por URL.
        Em duplicatas, fica com o item que tiver 'text' mais longo (melhor conteúdo).
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
        """_summary_

        Args:
            state (NewsSummaryState): _description_

        Returns:
            NewsSummaryState: _description_
        """
        articles = state.get("articles") or []
        summaries: List[NewsItemSummary] = []
        errors = list(state.get("errors") or [])
        
        for index, article_raw in enumerate(articles):
            try:
                article = self._coerce_article(article_raw)
                text_or_snippet = self._pick_text_or_snippet(article)
                summary = self._per_article_chain.invoke({
                    "title": article.title or "(Sem título)",
                    "source": article.source or "(sem fonte)",
                    "published_at": article.published_at or "(desconhecida)",
                    "url": article.url or "",
                    "text_or_snippet": text_or_snippet,
                })
                summaries.append(summary)
            except Exception as e:
                errors.append(f"article_{index}: {e}")
        return {"summaries": summaries, "errors": errors}
    
    def node_executive_summary(self, state: NewsSummaryState) -> NewsSummaryState:
        """_summary_

        Args:
            state (NewsSummaryState): _description_

        Returns:
            NewsSummaryState: _description_
        """
        summaries = state.get('summaries') or []
        if not summaries:
            executive_summary = NewsExecutiveSummary(
                overall_summary="Nenhum artigo válido para reumir",
                highlights=[],
                consensus=None,
                disagreements=None,
                sources_covered=[]
            )
            return {"executive_summary": executive_summary}
        
        try:
            summaries_json = json.dumps([summary.model_dump() for summary in summaries], ensure_ascii=False)
            executive_summary = self._aggegate_chain.invoke({"summaries_json": summaries_json})
            return {"executive_summary": executive_summary}
        except Exception as e:
            errors = list(state.get('errors') or [])
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
        """_summary_

        Args:
            state (NewsSummaryState): _description_

        Returns:
            NewsSummaryState: _description_
        """
        output_dir = state.get('save_dir')
        if not output_dir:
            return {}
        
        try:
            path = Path(output_dir)
            path.mkdir(parents=True, exist_ok=True)
            payload = {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "model": self.model_name,
                    **(state.get("meta") or {}),
                },
                "summaries": [summary.model_dump() for summary in state.get("summaries") or []],
                "executive_summary": (state.get("executive_summary").model_dump() if state.get("executive_summary") else None),
                "errors": state.get("errors") or [],
            }
            save_json_atomic(payload, path / "news_summaries.json")
        except Exception as e:
            errors = list(state.get("errors") or [])
            errors.append(f"save: {e}")
            return {"errors": errors}

        return {}
    
    def build_graph(self):
        graph = StateGraph(NewsSummaryState)
        graph.add_node('summarize_news', self.node_summarize)
        graph.add_node('executive_summary', self.node_executive_summary)
        graph.add_node('save_outputs', self.node_save)
        
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
        app = self.build_graph()
        init: NewsSummaryState = {
            "articles": articles,
            "save_dir": save_dir,
            "meta": meta or {},
            "errors": [],
        }
        out = app.invoke(init)
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
        path = Path(news_json_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        articles = data.get("articles", [])
        return self.run_from_articles(articles, save_dir=save_dir, meta=meta)
            