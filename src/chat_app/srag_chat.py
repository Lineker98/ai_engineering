from langchain_core.messages import HumanMessage, AIMessage
from ..agents.schemas import AgentSQLResult
from .guardrails import guard_sql
from .logging_audit import log_audit

class SRAGSQLAgentChat:
    def __init__(self, agent_app):
        self.agent_app = agent_app
        self.history = []

    def ask(self, user_input: str) -> AgentSQLResult:
        self.history.append(HumanMessage(content=user_input))
        result = self.agent_app.app.invoke({"messages": self.history})
        structured = result.get("structured")

        if structured is None:
            raise RuntimeError("Nenhuma resposta estruturada retornada")
        if guard_sql(structured.sql):
            raise ValueError("Consulta SQL bloqueada por segurança!")

        self.history.append(AIMessage(content=f"{structured.answer}\n\n SQL usada:\n{structured.sql}"))
        log_audit(user_input, structured.sql, structured.answer)
        return structured