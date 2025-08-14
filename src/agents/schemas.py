from typing import Annotated, Optional, TypedDict, Sequence, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from datetime import date
from enum import Enum


class AgentSQLResult(BaseModel):
    sql: str = Field(..., description="SQL usada")
    answer: str = Field(..., description="Resposta final, concisa")
    rationale: str = Field(..., description="Justificativa breve (1 frase)")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    structured: Optional[AgentSQLResult]
    
    
# ------------ Schemas to Report Agent static metrics ---------------
class MetricSeries(BaseModel):
    name: str
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    sql_used: str = ""
    description: str = ""
    ia_summary: Optional[str] = ""
    
class MetricsBundle(BaseModel):
    case_growth: Optional[MetricSeries] = None
    mortality_rate: Optional[MetricSeries] = None
    uti_utilization_rate: Optional[MetricSeries] = None
    vaccination_rate: Optional[MetricSeries] = None
    daily_cases: Optional[MetricSeries] = None
    monthly_cases: Optional[MetricSeries] = None

class ReportAgentState(TypedDict):
    start_date: Optional[date]
    end_date: Optional[date]
    results: Dict[str, MetricSeries]
    bundle: MetricsBundle
    save_path: Optional[str] = None
    plot_dir: Optional[str] = None
    plot_type: str = 'line'
    
# ------------ Schemas to Report Agent build report ---------------
class NewsArticleRaw(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[str] = Field(None, description="ISO-8601 se houver")
    snippet: Optional[str] = None
    text: Optional[str] = None

class NewsExecutiveSummary(BaseModel):
    overall_summary: str = Field(..., description="Síntese integrando os artigos em cerca de 20 à 30 linhas")
    highlights: List[str] = Field(default_factory=list, description="bullet points com os destaques e fatos")
    consensus: Optional[str] = None
    disagreements: Optional[str] = None
    sources_covered: List[str] = Field(default_factory=list)
    

class NewsItemSummary(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[str] = None
    summary: str = Field(..., description="Resumo objetivo em 10–15 linhas, sem especulação")
    key_points: List[str] = Field(default_factory=list, description="Fatos/achados principais")
    coverage_scope: Optional[str] = Field(
        default=None,
        description="Escopo: local/regional/nacional/mundial, se dedutível do texto"
    )
    limitations: Optional[str] = Field(
        default=None,
        description="Limitações do conteúdo (ex.: dados parciais, fonte opinativa)"
    )

class NewsSummaryState(TypedDict):
    articles: List[Dict[str, Any]]
    summaries: List[NewsItemSummary]
    executive_summary: NewsExecutiveSummary           
    save_dir: Optional[str]                  
    meta: Dict[str, Any]                     
    errors: List[str]