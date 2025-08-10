from typing import Annotated, Optional, TypedDict, Sequence, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from datetime import date


class AgentSQLResult(BaseModel):
    sql: str = Field(..., description="SQL usada")
    answer: str = Field(..., description="Resposta final, concisa")
    rationale: str = Field(..., description="Justificativa breve (1 frase)")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    structured: Optional[AgentSQLResult]
    
    
## Schemas to Report Agent
class MetricsSeries(BaseModel):
    name: str
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    sql_used: str = ""
    
class MetricsBundle(BaseModel):
    case_growth: Optional[MetricsSeries] = None
    mortality_rate: Optional[MetricsSeries] = None
    uti_utilization_rate: Optional[MetricsSeries] = None
    vaccination_rate: Optional[MetricsSeries] = None

class ReportAgentState(TypedDict):
    start_date: Optional[date]
    end_date: Optional[date]
    results: Dict[str, MetricsSeries]
    