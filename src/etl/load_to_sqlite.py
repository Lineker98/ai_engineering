import sqlite3
import pandas as pd
from pathlib import Path

def load_to_sqlite(
    df: pd.DataFrame, db_path="data/marts/srag.sqlite", table_name="srag_data"
) -> None:
    """Carrega um DataFrame do pandas para uma tabela SQLite (cria/atualiza a tabela).

    Os dados são gravados usando DataFrame.to_sql com if_exists='replace',
    substituindo a tabela caso ela já exista. O índice do DataFrame **não** é
    persistido como coluna.

    Args:
      df (pd.DataFrame): DataFrame já limpo e pronto para persistência.
      db_path (str, optional): Caminho do arquivo SQLite (.sqlite/.db).
        Defaults to "data/srag.sqlite".
      table_name (str, optional): Nome da tabela destino dentro do banco.
        Defaults to "srag_data".
    """
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, con=conn, if_exists="replace", index=False)
    conn.close()


if __name__ == "__main__":
    data_path = Path("data/staging/int_srag.csv")
    output_path = Path("data/marts/srag.sqlite")
    df = pd.read_csv(data_path)
    load_to_sqlite(df=df, db_path=output_path)
