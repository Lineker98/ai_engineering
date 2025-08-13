import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Callable

from langgraph.graph import StateGraph, END, START

from .schemas import MetricSeries, ReportAgentState, MetricsBundle
from ..utils.report_queries import (
    SQL_CASE_GROWTH,
    SQL_UTI,
    SQL_MORTALITY,
    SQL_VACCINATION,
)
from ..utils.helper_functions import save_json_atomic
from ..utils.plots import plot_static_metrics
from pathlib import Path


@dataclass
class SRAGMetricsReport:
    """
    Orquestrador para cálculo de métricas de SRAG (Síndrome Respiratória Aguda Grave) sem uso de IA.

    Este componente executa quatro consultas SQL pré-definidas sobre um banco SQLite contendo dados do SIVEP-Gripe,
    gera séries temporais de métricas (crescimento de casos, taxa de mortalidade, ocupação de UTI e vacinação),
    agrega em um `MetricsBundle` e oferece métodos para salvar os resultados em JSON e gerar gráficos.
    """

    sqlite_path: str = "../../data/marts/srag.sqlite"

    def _query_rows(self, sql: str, params: Optional[Dict[str, Any]] = {}):
        """
        Executa uma consulta SQL no banco SQLite configurado e retorna os resultados como lista de dicionários.

        Args:
            sql (str): Instrução SQL a ser executada.
            params (Optional[Dict[str, Any]]): Parâmetros opcionais para a query.

        Returns:
            List[Dict[str, Any]]: Lista de linhas da consulta, cada uma como dicionário {coluna: valor}.
        """
        conn = sqlite3.connect(self.sqlite_path)
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
        finally:
            conn.close()

    def node_case_growth(self, state: ReportAgentState) -> ReportAgentState:
        """
        Extrai e armazena no estado a métrica de crescimento de casos de SRAG.

        Args:
            state (ReportAgentState): Estado atual do pipeline contendo resultados parciais.

        Returns:
            ReportAgentState: Estado atualizado com a chave 'case_growth' contendo a série temporal.
        """
        rows = self._query_rows(SQL_CASE_GROWTH)
        series = MetricSeries(name="case_growth", rows=rows, sql_used=SQL_CASE_GROWTH)
        res = state["results"]
        res["case_growth"] = series
        return {"results": res}

    def node_mortality(self, state: ReportAgentState) -> ReportAgentState:
        """
        Extrai e armazena no estado a taxa de mortalidade por SRAG.

        Args:
            state (ReportAgentState): Estado atual do pipeline contendo resultados parciais.

        Returns:
            ReportAgentState: Estado atualizado com a chave 'mortality_rate' contendo a série temporal.
        """
        rows = self._query_rows(SQL_MORTALITY)
        series = MetricSeries(name="mortality_rate", rows=rows, sql_used=SQL_MORTALITY)
        res = state["results"]
        res["mortality_rate"] = series
        return {"results": res}

    def node_uti(self, state: ReportAgentState) -> ReportAgentState:
        """
        Extrai e armazena no estado a taxa de ocupação de UTI por casos de SRAG.

        Args:
            state (ReportAgentState): Estado atual do pipeline contendo resultados parciais.

        Returns:
            ReportAgentState: Estado atualizado com a chave 'uti_utilization_rate' contendo a série temporal.
        """
        rows = self._query_rows(SQL_UTI)
        series = MetricSeries(name="uti_utilization_rate", rows=rows, sql_used=SQL_UTI)
        res = state["results"]
        res["uti_utilization_rate"] = series
        return {"results": res}

    def node_vaccination(self, state: ReportAgentState) -> ReportAgentState:
        """
        Extrai e armazena no estado a taxa de vacinação entre pacientes de SRAG.

        Args:
            state (ReportAgentState): Estado atual do pipeline contendo resultados parciais.

        Returns:
            ReportAgentState: Estado atualizado com a chave 'vaccination_rate' contendo a série temporal.
        """
        rows = self._query_rows(SQL_VACCINATION)
        series = MetricSeries(
            name="vaccination_rate", rows=rows, sql_used=SQL_VACCINATION
        )
        res = state["results"]
        res["vaccination_rate"] = series
        return {"results": res}

    def node_aggregate_final(self, state: ReportAgentState):
        """
        Agrega todas as métricas calculadas em um objeto `MetricsBundle`.

        Args:
            state (ReportAgentState): Estado atual contendo todas as métricas calculadas.

        Returns:
            ReportAgentState: Estado atualizado com a chave 'bundle' contendo o pacote final de métricas.
        """
        results = state["results"]
        bundle = MetricsBundle(
            case_growth=results["case_growth"],
            mortality_rate=results["mortality_rate"],
            uti_utilization_rate=results["uti_utilization_rate"],
            vaccination_rate=results["vaccination_rate"],
        )
        return {"bundle": bundle}

    def save_bundle_metrics(
        self, bundle: MetricsBundle, output_path=str
    ) -> Optional[Path]:
        """
        Salva o pacote de métricas (`MetricsBundle`) em um arquivo JSON, com metadados de geração.

        Args:
            bundle (MetricsBundle): Pacote de métricas a ser salvo.
            output_path (str): Caminho de saída do arquivo JSON.

        Returns:
            Optional[Path]: Caminho final do arquivo salvo, ou None se falhar.
        """

        payload = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sqlite_path": self.sqlite_path,
            },
            "metrics": bundle.model_dump(),
        }
        path = save_json_atomic(payload=payload, output_path=output_path)
        return path

    def node_save_and_plot(self, state: ReportAgentState) -> Dict:
        """
        Salva as métricas em JSON e/ou gera gráficos estáticos, conforme parâmetros no estado.

        Args:
            state (ReportAgentState): Estado contendo o bundle de métricas, caminhos de saída e tipo de gráfico.

        Returns:
            dict: Dicionário vazio (nó terminal do pipeline).
        """
        bundle = state["bundle"]
        save_path = state.get("save_path")
        plot_dir = state.get("plot_dir")
        plot_type = state.get("plot_type", "line")

        if not bundle:
            print("[AVISO] Bundle de métricas está vazio. Nada a salvar ou plotar.")
            return {}

        if save_path:
            print(f"Salvando métricas em JSON em: {save_path}")
            self.save_bundle_metrics(bundle, save_path)

        if plot_dir:
            plot_static_metrics(bundle, plot_dir, plot_type=plot_type)

        return {}

    def build_graph(self) -> Callable:
        """
        Constrói e compila o grafo de execução do pipeline de métricas SRAG.

        Returns:
            Callable: Função compilada que executa o fluxo definido.
        """
        graph = StateGraph(ReportAgentState)
        graph.add_node("metrics_case_growth", self.node_case_growth)
        graph.add_node("metrics_mortality", self.node_mortality)
        graph.add_node("metrics_icu", self.node_uti)
        graph.add_node("metrics_vaccination", self.node_vaccination)
        graph.add_node("aggregate_final", self.node_aggregate_final)
        graph.add_node("save_and_plot", self.node_save_and_plot)

        graph.add_edge(START, "metrics_case_growth")
        graph.add_edge("metrics_case_growth", "metrics_mortality")
        graph.add_edge("metrics_mortality", "metrics_icu")
        graph.add_edge("metrics_icu", "metrics_vaccination")
        graph.add_edge("metrics_vaccination", "aggregate_final")
        graph.add_edge("aggregate_final", "save_and_plot")
        graph.add_edge("aggregate_final", END)

        return graph.compile()

    def run(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        save_path: str = None,
        plot_dir: str = None,
        plot_type: str = "line",
    ) -> MetricsBundle:
        """
        Executa o pipeline completo de cálculo de métricas SRAG:
        - Coleta dados via SQL
        - Calcula métricas
        - Agrega resultados
        - Salva e plota se configurado

        Args:
            start_date (Optional[date]): Data inicial para filtro (não implementado nas queries padrão).
            end_date (Optional[date]): Data final para filtro (não implementado nas queries padrão).
            save_path (str): Caminho para salvar o JSON com métricas.
            plot_dir (str): Diretório para salvar gráficos gerados.
            plot_type (str): Tipo de gráfico a ser gerado ('line', 'bar', etc.).

        Returns:
            MetricsBundle: Pacote final contendo todas as métricas calculadas.
        """
        app = self.build_graph()
        init_state = {
            "start_date": start_date,
            "end_date": end_date,
            "save_path": save_path,
            "plot_dir": plot_dir,
            "plot_type": plot_type,
            "results": {},
        }
        output = app.invoke(init_state)
        bundle = output["bundle"]
        return bundle
