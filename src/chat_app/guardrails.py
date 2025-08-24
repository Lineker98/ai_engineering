
FORBIDDEN_SQL = ["drop", "delete", "insert", "update", "alter"]

def guard_sql(sql: str) -> bool:
    """_summary_

    Args:
        sql (str): _description_

    Returns:
        bool: _description_
    """
    sql_lower = sql.lower()
    return any(cmd in sql_lower for cmd in FORBIDDEN_SQL)
