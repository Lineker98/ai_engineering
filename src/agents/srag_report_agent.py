import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END, START

from .schemas import MetricSeries
from ..utils.report_queries import (
    SQL_CASE_GROWTH,
    SQL_ICU,
    SQL_MORTALITY,
    SQL_VACCINATION
)

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