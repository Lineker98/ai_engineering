import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END, START

from .schemas import MetricSeries, ReportAgentState, MetricsBundle
from ..utils.report_queries import (
    SQL_CASE_GROWTH,
    SQL_UTI,
    SQL_MORTALITY,
    SQL_VACCINATION
)
from pathlib import Path
import json, os, tempfile

@dataclass
class SRAGMetricsReport:
    """
    Orquestrador de métricas SRAG sem IA.
    - Executa 4 queries mensais pré-definidas em SQLite.
    - Cada nó adiciona uma MetricSeries ao estado.
    """
    sqlite_path: str = "../../data/marts/srag.sqlite"
    
    def _query_rows(self, sql: str, params: Optional[Dict[str, Any]] = {}):
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute(sql, params) # Executar a query desejada
            cols = [d[0] for d in cur.description] if cur.description else [] # obter o nome das colunas retornadas pela query
            rows = cur.fetchall() # obter resultado da consulta
            return [dict(zip(cols, r)) for r in rows] # Estruturar em uma lista de dicionário col: value
        finally:
            conn.close()
        
    def node_case_growth(self, state: ReportAgentState) -> ReportAgentState:
        """_summary_

        Args:
            state (ReportAgentState): _description_

        Returns:
            ReportAgentState: _description_
        """
        rows = self._query_rows(SQL_CASE_GROWTH)
        series = MetricSeries(name='case_growth', rows=rows, sql_used=SQL_CASE_GROWTH)
        res = state["results"]
        res['case_growth'] = series
        return {"results": res}
    
    def node_mortality(self, state: ReportAgentState) -> ReportAgentState:
        """_summary_

        Args:
            state (ReportAgentState): _description_

        Returns:
            ReportAgentState: _description_
        """
        rows = self._query_rows(SQL_MORTALITY)
        series = MetricSeries(name='mortality_rate', rows=rows, sql_used=SQL_MORTALITY)
        res = state["results"]
        res['mortality_rate'] = series
        return {"results": res}
        
    def node_uti(self, state: ReportAgentState) -> ReportAgentState:
        """_summary_

        Args:
            state (ReportAgentState): _description_

        Returns:
            ReportAgentState: _description_
        """
        rows = self._query_rows(SQL_UTI)
        series = MetricSeries(name='uti_utilization_rate', rows=rows, sql_used=SQL_UTI)
        res = state["results"]
        res['uti_utilization_rate'] = series
        return {"results": res}
    
        
    def node_vaccination(self, state: ReportAgentState) -> ReportAgentState:
        """_summary_

        Args:
            state (ReportAgentState): _description_

        Returns:
            ReportAgentState: _description_
        """
        rows = self._query_rows(SQL_VACCINATION)
        series = MetricSeries(name='vaccination_rate', rows=rows, sql_used=SQL_VACCINATION)
        res = state['results']
        res['vaccination_rate'] = series
        return {"results": res}
    
    def node_aggregate_final(self, state: ReportAgentState):
        """_summary_

        Args:
            state (ReportAgentState): _description_

        Returns:
            ReportAgentState: _description_
        """
        results = state['results']
        bundle = MetricsBundle(
            case_growth=results['case_growth'],
            mortality_rate=results['mortality_rate'],
            uti_utilization_rate=results["uti_utilization_rate"],
            vaccination_rate=results["vaccination_rate"]
            
        )
        return {"bundle": bundle}
    
    def build_graph(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        graph = StateGraph(ReportAgentState)
        graph.add_node("metrics_case_growth", self.node_case_growth)
        graph.add_node("metrics_mortality", self.node_mortality)
        graph.add_node("metrics_icu", self.node_uti)
        graph.add_node("metrics_vaccination", self.node_vaccination)
        graph.add_node("aggregate_final", self.node_aggregate_final)

        graph.add_edge(START, "metrics_case_growth")
        graph.add_edge("metrics_case_growth", "metrics_mortality")
        graph.add_edge("metrics_mortality", "metrics_icu")
        graph.add_edge("metrics_icu", "metrics_vaccination")
        graph.add_edge("metrics_vaccination", "aggregate_final")
        graph.add_edge("aggregate_final", END)

        return graph.compile()
    
    def save_bundle_metrics(self, bundle: MetricsBundle, output_path=str) -> Optional[Path]:
        """_summary_

        Args:
            bundle (MetricsBundle): _description_
            output_path (_type_, optional): _description_. Defaults to str.
        """
        path = Path(output_path)
        print(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        payload = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sqlite_path": self.sqlite_path,
            },
            "metrics": bundle.model_dump()
        }
        
        tmp_name = None
        try:
            # Cria um arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(path.parent), delete=False) as tmp:
                json.dump(payload, tmp, ensure_ascii=False, indent=2)
                tmp_name = tmp.name
            
            # Substitui de forma atômica
            os.replace(tmp_name, path)
            return path
        except Exception as e:
            print(f"[ERRO] Falha ao salvar métricas: {e}")
            return None
        finally:
            # se sobrou arquivo temporário não usado, remove
            if tmp_name and Path(tmp_name).exists():
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass
    
    def run(self, start_date: Optional[date] = None, end_date: Optional[date] = None, save_path: str = None) -> MetricsBundle:
        """_summary_

        Args:
            start_date (Optional[date], optional): _description_. Defaults to None.
            end_date (Optional[date], optional): _description_. Defaults to None.

        Returns:
            MetricsBundle: _description_
        """
        app = self.build_graph()
        init = {"start_date": start_date, "end_date": end_date, "results": {}}
        output = app.invoke(init)
        bundle = output["bundle"]
        self.save_bundle_metrics(bundle, save_path)
        return bundle