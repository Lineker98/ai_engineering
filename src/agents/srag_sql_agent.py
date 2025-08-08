from __future__ import annotations

from typing import Dict, Any
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .schemas import AgentState, AgentSQLResult
from .prompt import build_normalize_prompt

class SRAGSQLAgentApp:
    
    def __init__(
        self,
        sqlite_uri: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
    ):

        self.llm = ChatOpenAI(model=model, temperature=temperature)
        
        df_path = Path(sqlite_uri).resolve()
        if not df_path.exists():
            raise FileNotFoundError(f"[ERRO] Arquivo SQLite não encontrado: {df_path}")
        self.db = SQLDatabase.from_uri(f"sqlite:///{df_path}")
        self.tools = SQLDatabaseToolkit(db=self.db, llm=self.llm).get_tools()
        
        # Vincular tools ao LLM (evita recriar a cada chamada)
        self.bound_llm = self.llm.bind_tools(self.tools)
        
        # LLM com saída estruturada
        self.srucutured_llm = self.llm.with_structured_output(AgentSQLResult)
        self.normalize_prompt = build_normalize_prompt()
        
        # Constrói e compila o grafo
        self.app = self._build_and_compile_graph()

    
    def agent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Node agente: gera a próxima mensagem usando as ferramentas SQL

        Args:
            state (AgentState): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        return {"messages": [self.bound_llm.invoke(state['messages'])]}
    
    def final_node(self, state: AgentState) -> Dict[str, Any]:
        """_summary_

        Args:
            state (AgentState): _description_

        Returns:
            Dict[str, Any]: _description_
        """
        msgs = self.normalize_prompt.format_messages()
        response = self.srucutured_llm.invoke(msgs + state['messages'])
        return {"structured": response}
        
        
    # Roteamento
    @staticmethod
    def route_after_agent(state: AgentState) -> str:
        """
        Se houver chamada de ferramenta pendente, vá a 'tools'; senão, 'final'

        Args:
            state (AgentState): _description_

        Returns:
            str: _description_
        """
        return "tools" if tools_condition(state) == "tools" else "final"

    def _build_and_compile_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node('agent', self.agent_node)
        graph.add_node('tools', ToolNode(self.tools))
        graph.add_node("final", self.final_node)
        
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            'agent', 
            self.route_after_agent,
            {'tools': 'tools', 'final': 'final'}
        )
        
        graph.add_edge("tools", "agent")
        graph.add_edge("final", END)
        
        return graph.compile()

    def run(self, user_message: str) -> AgentSQLResult:
        response = self.app.invoke({
            "messages": [("user", user_message)]
        })
        result = response.get('structured')
        if not isinstance (result, AgentSQLResult):
            raise ValueError('Falha ao obter saída estruturada AgentSQLResult')
        return result