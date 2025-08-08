from typing import Annotated, Optional, TypedDict, List
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class AgentSQLResult(BaseModel):
    sql: str = Field(..., description="SQL usada")
    answer: str = Field(..., description="Resposta final, concisa")
    rationale: str = Field(..., description="Justificativa breve (1 frase)")


class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    structured: Optional[AgentSQLResult]