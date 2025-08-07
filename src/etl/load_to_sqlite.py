import sqlite3
import pandas as pd

def load_to_sqlite(df: pd.DataFrame, db_path='data/srag.sqlite', table_name='srag_data') -> None:
    """
    This function aims to load the SRAG data into a SQLite Database

    Args:
        df (pd.DataFrame): Pandas Dataframe with the data already prepared to be load.
        db_path (str, optional): Path to store the sqlite. Defaults to 'data/srag.sqlite'.
        table_name (str, optional): The table name of sqlite data. Defaults to 'srag_data'.
    """
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, con=conn, if_exists='append', index=False)
    conn.close()