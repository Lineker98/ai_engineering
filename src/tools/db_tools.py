import sqlite3
import logging
from typing import Any, Dict, List, Optional
from ..utils.logs_config import setup_logging

logger = logging.getLogger(__name__)
setup_logging()

class DatabaseQueryTool:
    """
    A tool for connecting to and querying a SQLite database
    """
    
    def __init__(self, sqlite_path: str):
        """
        Initializes the tool with the path to the SQLite database.

        Args:
            sqlite_path (str): The file path to the SQLite database.
        """
        self.sqlite_path = sqlite_path
    
    def query_rows(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        Executes a SQL query and returns the results as a list of dictionaries.

        Args:
            sql (str): _The SQL query string to be executed.
            params (Optional[Dict[str, Any]], optional):A dictionary of parameters for the query. Defaults to None.

        Returns:
            List[Dict]: A list of dictionaries, where each represents a row from the query result.
        """
        params = params or {}
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(sql, params)
                rows = cur.fetchall()
                
                # Converto each sqlite3.Row into a dictionary
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []