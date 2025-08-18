import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Callable, List
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .schemas import MetricSeries, ReportAgentState, MetricsBundle
from ..utils.report_queries import (
    SQL_CASE_GROWTH,
    SQL_UTI,
    SQL_MORTALITY,
    SQL_VACCINATION,
    SQL_CASOS_DIARIOS_30_DIAS,
    SQL_CASOS_MENSAIS_12_MESES,
)
from .prompt import SUMMARY_METRIC_SYSTEM, SUMMARY_METRIC_USER
from ..utils.helper_functions import save_json_atomic
from ..utils.plots import plot_static_metrics
from ..utils.logs_config import setup_logging
from ..tools.db_tools import DatabaseQueryTool


setup_logging()
logger = logging.getLogger(__name__)


class SRAGMetricsReport:
    """
    Orquestrador para cálculo de métricas de SRAG (Síndrome Respiratória Aguda Grave) sem uso de IA.

    Este componente executa quatro consultas SQL pré-definidas sobre um banco SQLite contendo dados do SIVEP-Gripe,
    gera séries temporais de métricas (crescimento de casos, taxa de mortalidade, ocupação de UTI e vacinação),
    agrega em um `MetricsBundle` e oferece métodos para salvar os resultados em JSON e gerar gráficos.
    """

    def __init__(self, sqlite_path: str, model="gpt-4o-mini", temperature=0):
        self.sqlite_path = sqlite_path
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.chain = self._build_summary_chain()
        self.db_tool = DatabaseQueryTool(sqlite_path=sqlite_path)

    def _build_summary_chain(self):
        """Constructs and returns a LangChain processing chain for metric summaries.

        This private method creates a `ChatPromptTemplate` from predefined system and user messages.
        It then pipes this prompt template to the class's language model (`self.llm`) to form a complete,
        executable chain. This chain is designed to be invoked with data to generate an AI-powered summary.

        Returns:
            The LangChain-style object representing the processing chain.
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", SUMMARY_METRIC_SYSTEM), ("user", SUMMARY_METRIC_USER)]
        )
        return prompt | self.llm

    def node_case_growth(self, state: ReportAgentState) -> ReportAgentState:
        """Extracts and stores the SRAG case growth metric in the pipeline state.

        This function queries a database for monthly SRAG case growth data, generates an
        AI-powered summary of the findings, and then packages this information into a
        `MetricSeries` object. It then updates the provided `ReportAgentState` with this
        new metric under the 'case_growth' key.

        Args:
            state (ReportAgentState): The current state of the pipeline, which contains partial results.

        Returns:
            ReportAgentState: The updated state, with a new key 'case_growth' containing the time series data.
        """
        logger.info("Query and analyze results for cases growth.")
        rows = self.db_tool.query_rows(sql=SQL_CASE_GROWTH)
        description = "Taxa de aumento de casos de SRAG - Grão mensal"
        name = "case_growth"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_CASE_GROWTH,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_mortality(self, state: ReportAgentState) -> ReportAgentState:
        """Extracts and stores the SRAG mortality rate in the pipeline state.

        This function queries a database for monthly SRAG mortality rate data, generates an
        AI-powered summary of the findings, and then packages this information into a
        `MetricSeries` object. It then updates the provided `ReportAgentState` with this
        new metric under the 'mortality_rate' key.

        Args:
            state (ReportAgentState): The current state of the pipeline, which contains partial results.

        Returns:
            ReportAgentState: The updated state, with a new key 'mortality_rate' containing the time series data.
        """
        logger.info("Query and analyze results for mortality rate.")
        rows = self.db_tool.query_rows(sql=SQL_MORTALITY)
        description = "Taxa de mortalidade de SRAG - Grão mensal"
        name = "mortality_rate"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_MORTALITY,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_uti(self, state: ReportAgentState) -> ReportAgentState:
        """Extracts and stores the SRAG UTI utilization rate in the pipeline state.

        This function queries a database for monthly SRAG UTI utilization rate data, generates an
        AI-powered summary of the findings, and then packages this information into a `MetricSeries` object.
        It then updates the provided `ReportAgentState` with this new metric under the 'uti_utilization_rate' key.

        Args:
            state (ReportAgentState): The current state of the pipeline, which contains partial results.

        Returns:
            ReportAgentState: The updated state, with a new key 'uti_utilization_rate' containing the time series data.
        """
        logger.info("Query and analyze results for UTI utilization.")
        rows = self.db_tool.query_rows(sql=SQL_UTI)
        description = "Taxa de ocupação de UTI - Grão mensal"
        name = "uti_utilization_rate"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_UTI,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_vaccination(self, state: ReportAgentState) -> ReportAgentState:
        """Extracts and stores the SRAG patient vaccination rate in the pipeline state.

        This function queries a database for monthly COVID-19 vaccination rates among
        Severe Acute Respiratory Syndrome (SRAG) patients. It then generates an AI-powered summary
        of this data, packages it into a `MetricSeries` object, and updates the `ReportAgentState`
        with this new metric under the 'vaccination_rate' key.

        Args:
            state (ReportAgentState): The current state of the pipeline, which contains partial results.

        Returns:
            ReportAgentState: The updated state, with a new key 'vaccination_rate' containing the time series data.
        """
        logger.info("Query and analyze results for Vacciation rate.")
        rows = self.db_tool.query_rows(sql=SQL_VACCINATION)
        description = "Taxa de vacinação contra COVID-19 - Grão mensal"
        name = "vaccination_rate"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_VACCINATION,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_casos_diarios(self, state: ReportAgentState) -> ReportAgentState:
        """Queries daily case data, generates an AI summary, and adds it to the agent's state.

        Args:
            state (ReportAgentState): The current state of the agent, containing a dictionary of results from previous processing steps.

        Returns:
            ReportAgentState: The updated state of the agent, with the `daily_cases` metric added to the results.
        """
        logger.info("Query and analyze results for Daily cases for the last 30 days.")
        rows = self.db_tool.query_rows(sql=SQL_CASOS_DIARIOS_30_DIAS)
        description = "Casos diários de SRAG nos últimos 30 Dias"
        name = "daily_cases"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_CASOS_DIARIOS_30_DIAS,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_casos_mensais(self, state: ReportAgentState) -> ReportAgentState:
        """Queries monthly case data, generates an AI summary, and adds it to the agent's state.

        This function acts as a processing node that executes a SQL query to retrieve the monthly count of
        Severe Acute Respiratory Syndrome (SRAG) cases over the last 12 months.
        It then uses an AI model to generate a summary of this data before packaging the results into a `MetricSeries` object.
        Finally, it updates the `ReportAgentState` with this new metric.

        Args:
            state (ReportAgentState): The current state of the agent, containing a dictionary of results from previous processing steps.

        Returns:
            ReportAgentState: The updated state of the agent, with the `monthly_cases` metric added to the results.
        """
        logger.info("Query and analyze results for Monthlt cases for the last 12 months.")
        rows = self.db_tool.query_rows(sql=SQL_CASOS_MENSAIS_12_MESES)
        description = "Casos mensais de SRAG nos últimos 12 meses"
        name = "monthly_cases"
        ia_summary = self.chain.invoke(
            {"name": name, "rows": rows, "description": description}
        )
        series = MetricSeries(
            name=name,
            rows=rows,
            sql_used=SQL_CASOS_DIARIOS_30_DIAS,
            description=description,
            ia_summary=ia_summary.content,
        )
        res = state["results"]
        res[name] = series
        return {"results": res}

    def node_aggregate_final(self, state: ReportAgentState) -> ReportAgentState:
        """Aggregates all calculated metrics into a single MetricsBundle object.

        This final node in the processing pipeline retrieves all individual metric series from the agent's state dictionary.
        It then bundles them together into a structured `MetricsBundle` object,
        which is then stored in the state under the 'bundle' key for final use.

        Args:
            state (ReportAgentState): The current state containing all previously calculated and stored metrics.

        Returns:
            ReportAgentState: The updated state, with a new key 'bundle' containing the final aggregated metrics.
        """
        results = state["results"]
        bundle = MetricsBundle(
            case_growth=results["case_growth"],
            mortality_rate=results["mortality_rate"],
            uti_utilization_rate=results["uti_utilization_rate"],
            vaccination_rate=results["vaccination_rate"],
            daily_cases=results["daily_cases"],
            monthly_cases=results["monthly_cases"],
        )
        return {"bundle": bundle}

    def save_bundle_metrics(
        self, bundle: MetricsBundle, output_path=str
    ) -> Optional[Path]:
        """Saves a MetricsBundle object to a JSON file with generation metadata.

        This function prepares a payload by adding generation metadata, such as the
        timestamp and source database path, to the provided `MetricsBundle`. It then
        uses the `save_json_atomic` function to safely write this data to the
        specified JSON file.

        Args:
            bundle (MetricsBundle): The MetricsBundle object containing all the
                                    metrics to be saved.
            output_path (str): The file path where the JSON file will be saved.

        Returns:
            Optional[Path]: A Path object for the saved file on success, or None on failure.
        """

        payload = {
            "meta": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sqlite_path": self.db_tool.sqlite_path,
            },
            "metrics": bundle.model_dump(),
        }
        path = save_json_atomic(payload=payload, output_path=output_path)
        return path

    def node_save_and_plot(self, state: ReportAgentState) -> Dict:
        """Saves metrics to a JSON file and/or generates static plots based on the state parameters.

        This function acts as a terminal node in the pipeline. It checks the provided state for a metrics bundle,
        a save path, and a plot directory. If these are present, it calls the appropriate helper functions
        to save the metrics as a JSON file and/or generate static chart images.

        Args:
            state (ReportAgentState): The state object containing the final metrics bundle, output paths for saving, and the desired plot type.

        Returns:
            Dict: An empty dictionary, signaling that this is a terminal node and no further state needs to be passed.
        """
        bundle = state["bundle"]
        save_path = state.get("save_path")
        plot_dir = state.get("plot_dir")
        plot_type = state.get("plot_type", "line")

        if not bundle:
            logger.info("[AVISO] Bundle de métricas está vazio. Nada a salvar ou plotar.")
            return {}

        if save_path:
            logger.info(f"Saving static metrics at {save_path}")
            self.save_bundle_metrics(bundle, save_path)

        if plot_dir:
            logger.info(f"Ploting and saving static metrics at {plot_dir}")
            plot_static_metrics(bundle, plot_dir, plot_type=plot_type)

        return {}

    def build_graph(self) -> Callable:
        """Constructs and compiles the execution graph for the SRAG metrics pipeline.

        This method defines a linear workflow using the `StateGraph` library.
        It adds a series of processing nodes, each corresponding to a specific metric extraction or finalization step.
        The edges are defined to create a sequential flow from start to end, and the entire graph is
        then compiled into a single, executable function.

        Args:
            self: The instance of the class containing the node methods.

        Returns:
            Callable: The compiled function that executes the defined workflow.
        """
        graph = StateGraph(ReportAgentState)
        graph.add_node("metrics_case_growth", self.node_case_growth)
        graph.add_node("metrics_mortality", self.node_mortality)
        graph.add_node("metrics_UTI", self.node_uti)
        graph.add_node("metrics_vaccination", self.node_vaccination)
        graph.add_node("daily_cases", self.node_casos_diarios)
        graph.add_node("monthly_cases", self.node_casos_mensais)
        graph.add_node("aggregate_final", self.node_aggregate_final)
        graph.add_node("save_and_plot", self.node_save_and_plot)

        graph.add_edge(START, "metrics_case_growth")
        graph.add_edge("metrics_case_growth", "metrics_mortality")
        graph.add_edge("metrics_mortality", "metrics_UTI")
        graph.add_edge("metrics_UTI", "metrics_vaccination")
        graph.add_edge("metrics_vaccination", "daily_cases")
        graph.add_edge("daily_cases", "monthly_cases")
        graph.add_edge("monthly_cases", "aggregate_final")
        graph.add_edge("aggregate_final", "save_and_plot")
        graph.add_edge("save_and_plot", END)

        return graph.compile()

    def run(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        save_path: str = None,
        plot_dir: str = None,
        plot_type: str = "line",
    ) -> MetricsBundle:
        """Executes the complete SRAG metrics calculation pipeline.

        This function serves as the main entry point for the entire workflow.
        It builds and runs a state-based graph that performs the following steps:
        - Collects data from a SQL database.
        - Calculates various metrics.
        - Aggregates all results into a single bundle.
        - Optionally saves the metrics to a JSON file and/or generates plots based on the provided parameters.

        Args:
            start_date (Optional[date], optional): The start date for filtering data. Note that this is not
                implemented in the standard queries. Defaults to None.
            end_date (Optional[date], optional): The end date for filtering data.
                Also not implemented in the standard queries. Defaults to None.
            save_path (str, optional): The file path where the metrics JSON file will be saved. Defaults to None.
            plot_dir (str, optional): The directory where the generated plot images will be saved. Defaults to None.
            plot_type (str, optional): The type of chart to generate (e.g., 'line' or 'bar'). Defaults to 'line'.

        Returns:
            MetricsBundle: The final bundle containing all the calculated metrics.
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
        logger.info("EXECUTING STATIC METRICS AGENT")
        output = app.invoke(init_state)
        logger.info(f"Succesfull generate all necessary metrics!")
        bundle = output["bundle"]
        return bundle
