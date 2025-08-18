import logging
import json
from pathlib import Path
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any

from .schemas import OrchestratorState
from .srag_metrics_agent import SRAGMetricsReport
from .srag_news_summary_agent import SummaryAgent
from ..report.generate_pdf import run_report
from .prompt import FINAL_REPORT_SYSTEM, FINAL_REPORT_USER
from ..etl.news_ingest import ingest_srag_news

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Orchestrates the execution of the SRAG metrics and News Summary agents
    to produce a final, synthesized report.
    """

    def __init__(
        self,
        model="gpt-4o-mini",
        temperature=0,
        sqlite_path="data/marts/srag.sqlite",
        news_input_path="data/marts/srag_news.json",
        output_dir="src/report",
    ):
        """Inicializa o agente orquestrador.

        Args:
            model (str, optional): O nome do modelo de linguagem a ser usado. Padrão: 'gpt-4o-mini'.
            temperature (int, optional): A temperatura para a geração do LLM, controlando a aleatoriedade. Padrão: 0.
        """
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.chain = self._build_orchestrator_chain()
        self.sqlite_path = sqlite_path
        self.news_input_path = news_input_path
        self.output_dir = output_dir

    def _build_orchestrator_chain(self):
        """Constrói a cadeia de processamento LangChain para sintetizar o relatório final.

        Esta cadeia combina um prompt do sistema e do usuário com o modelo de linguagem
        configurado para gerar o relatório executivo consolidado.

        Returns:
            Runnable: Um objeto executável da LangChain.
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", FINAL_REPORT_SYSTEM), ("user", FINAL_REPORT_USER)]
        )
        return prompt | self.llm

    def node_run_metrics_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Executa o agente de métricas de SRAG para coletar e salvar dados quantitativos.

        Este nó do grafo aciona o `SRAGMetricsReport`, que consulta o banco de dados,
        gera as métricas, salva os resultados em um arquivo JSON e cria gráficos visuais.

        Args:
            state (OrchestratorState): O estado atual do pipeline, contendo `sqlite_path` e `output_dir`.

        Returns:
            OrchestratorState: Um dicionário contendo o `metrics_bundle` com os resultados para atualizar o estado.
        """
        logger.info("--- ORCHESTRATOR: EXECUTING METRICS AGENT ---")

        metrics_agent = SRAGMetricsReport(sqlite_path=self.sqlite_path)

        # We want to save plots and JSON in a subdirectory
        metrics_output_path = f"{self.output_dir}/summaries/srag_metrics.json"
        metrics_plot_dir = f"{self.output_dir}/imgs/"

        bundle = metrics_agent.run(
            save_path=metrics_output_path, plot_dir=metrics_plot_dir
        )

        logger.info("--- ORCHESTRATOR: METRICS AGENT COMPLETED ---")
        return {"metrics_bundle": bundle}
    
    def node_ingest_news(self, state: OrchestratorState) -> Dict[str, Any]:
        """_summary_

        Args:
            state (OrchestratorState): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        logger.info("--- ORCHESTRATOR: EXECUTING NEWS INGESTION ---")
        # This function will search, parse, and save the news to news_path
        ingest_srag_news(
            query="SRAG site:saude.gov.br", # Or get this from the state
            output_path=self.news_input_path,
            top_k=10
        )
        return {}

    def node_run_news_agent(self, state: OrchestratorState) -> OrchestratorState:
        """Executa o agente de resumo de notícias para coletar e salvar dados qualitativos.

        Este nó aciona o `SummaryAgent`, que processa os artigos de notícias,
        gera resumos individuais e um resumo executivo agregado, salvando o resultado em JSON.

        Args:
            state (OrchestratorState): O estado atual do pipeline, contendo `news_input_path` e `output_dir`.

        Returns:
            OrchestratorState: Um dicionário contendo o `news_summary_output` para atualizar o estado.
        """
        logger.info("--- ORCHESTRATOR: EXECUTING NEWS SUMMARY AGENT ---")
        output_dir = f"{self.output_dir}/summaries/"

        news_agent = SummaryAgent()
        summary_output = news_agent.run(
            news_json_path=self.news_input_path, save_dir=output_dir
        )

        logger.info("--- ORCHESTRATOR: NEWS SUMMARY AGENT COMPLETED ---")
        return {"news_summary_output": summary_output}

    def node_create_final_report(self, state: OrchestratorState) -> OrchestratorState:
        """Sintetiza as métricas e os resumos de notícias em um relatório executivo final.

        Utiliza um LLM para combinar os dados quantitativos e qualitativos dos nós anteriores,
        gerando um relatório coeso em formato Markdown que é salvo em um arquivo.

        Args:
            state (OrchestratorState): O estado atual, contendo `metrics_bundle` e `news_summary_output`.

        Returns:
           OrchestratorState: Um dicionário contendo o `final_report` (conteúdo em string) para atualizar o estado.
        """
        logger.info("--- ORCHESTRATOR: CREATING FINAL SYNTHESIZED REPORT ---")
        metrics_bundle = state.get("metrics_bundle")
        news_summary = state.get("news_summary_output")

        if not metrics_bundle or not news_summary:
            final_report = (
                "Could not generate final report: missing metrics or news data."
            )
            logger.warning(final_report)
            return {"final_report": final_report}

        # Invoke the chain with the data
        serializable_news_summary = {
            "summaries": [
                summary.model_dump() for summary in news_summary.get("summaries", [])
            ],
            "executive_summary": (
                news_summary.get("executive_summary").model_dump()
                if news_summary.get("executive_summary")
                else None
            ),
            "errors": news_summary.get("errors", []),
        }
        news_json_string = json.dumps(
            serializable_news_summary, indent=2, ensure_ascii=False
        )

        response = self.chain.invoke(
            {
                "metrics_json": metrics_bundle.model_dump_json(indent=2),
                "news_json": news_json_string,
            }
        )

        final_report = response.content

        # Save the final report to a file
        output_dir = Path(self.output_dir)
        report_path = output_dir / "final_executive_report.md"

        report_path.write_text(final_report, encoding="utf-8")
        logger.info(f"Final report saved to {report_path}")

        return {"final_report": final_report}

    def node_generate_pdf(self, state: OrchestratorState) -> OrchestratorState:
        """Gera a versão final do relatório em formato PDF.

        Este nó utiliza uma função externa (`run_report`) para converter os dados
        e artefatos gerados em um documento PDF formatado.

        Args:
            state (OrchestratorState): O estado atual, contendo o `output_dir`.

        Returns:
            OrchestratorState: Um dicionário com o `pdf_output_path` para atualizar o estado.
        """
        logger.info("--- ORQUESTRADOR: GERANDO RELATÓRIO EM PDF ---")
        try:
            output_path = f"{self.output_dir}/relatorio_epidemiologico_srag.pdf"

            run_report(output_path=output_path)
            logger.info(f"Relatório em PDF gerado com sucesso em: {output_path}")
            return {"pdf_output_path": str(output_path)}
        except Exception as e:
            logger.error(f"Falha ao gerar o relatório em PDF: {e}")
            return {}

    def build_graph(self) -> StateGraph:
        """Constrói e compila o grafo de execução do pipeline.

        Define todos os nós e as arestas que conectam o fluxo de trabalho,
        desde a coleta de dados até a geração do PDF final.

        Returns:
            StateGraph: A aplicação LangGraph compilada e pronta para ser executada.
        """
        graph = StateGraph(OrchestratorState)

        graph.add_node("run_metrics", self.node_run_metrics_agent)
        graph.add_node("run_news", self.node_run_news_agent)
        graph.add_node("final_report", self.node_create_final_report)
        graph.add_node("generate_pdf", self.node_generate_pdf)

        # Define the workflow
        graph.add_edge(START, "run_metrics")
        graph.add_edge("run_metrics", "run_news")
        graph.add_edge("run_news", "final_report")
        graph.add_edge("final_report", "generate_pdf")
        graph.add_edge("generate_pdf", END)

        return graph.compile()

    def run(self):
        """Ponto de entrada principal para executar todo o pipeline de orquestração.

        Returns:
            dict: O estado final do pipeline após a execução completa.
        """
        app = self.build_graph()
        final_state = app.invoke(input={})

        logger.info("--- PIPELINE COMPLETE ---")
        return final_state
