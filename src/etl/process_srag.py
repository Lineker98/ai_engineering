import pandas as pd
from typing import List, Dict
from pathlib import Path


def convert_to_datetime(
    df: pd.DataFrame, columns_formats: Dict, errors="coerce"
) -> pd.DataFrame:
    """
    Converte colunas específicas de um DataFrame para o formato datetime.

    Args:
        df (pd.DataFrame): DataFrame contendo as colunas a serem convertidas.
        columns_formats (Dict): Dicionário no formato {coluna: formato}, onde o formato segue o padrão strftime
            ou None para inferência automática.
        errors (str, optional): Estratégia de tratamento de erros ('ignore', 'raise', 'coerce').
            Defaults to 'coerce'.

    Returns:
        pd.DataFrame: O DataFrame original com as colunas convertidas para datetime.
    """
    for col, format in columns_formats.items():
        df[col] = pd.to_datetime(df[col], format=format, errors=errors)
    print("Conversão de dados realizada!")
    return df


def load_dataframes(base_path: List[str], sep=";", encoding="latin1", low_memory=False) -> pd.DataFrame:
    """
    Carrega um arquivo CSV em um DataFrame do pandas.

    Args:
        df_path (str): Caminho para o arquivo CSV.
        sep (str, optional): Delimitador das colunas. Defaults to ';'.
        encoding (str, optional): Codificação do arquivo. Defaults to 'latin1'.
        low_memory (bool, optional): Reduz o uso de memória ao ler o arquivo em pedaços. Defaults to False.

    Returns:
        pd.DataFrame: DataFrame contendo os dados carregados.
    """
    csv_files = list(base_path.glob("*.csv"))
    list_of_dfs = [pd.read_csv(f, sep=";", encoding="latin1", low_memory=False) for f in csv_files]
    df = pd.concat(list_of_dfs, ignore_index=True)
    print("Carregamento de dados realizado!")
    return df


def store_df(df: pd.DataFrame, path: Path) -> None:
    """
    Salva um DataFrame em um arquivo CSV no caminho especificado.

    Args:
        df (pd.DataFrame): DataFrame a ser salvo.
        path (Path): Caminho completo (incluindo o nome do arquivo) para salvar o CSV.

    Returns:
        None
    """
    # Garante que a pasta exista
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def select_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Seleciona colunas específicas de um DataFrame.

    Args:
        df (pd.DataFrame): DataFrame original.
        columns (List[str]): Lista com os nomes das colunas a serem selecionadas.

    Returns:
        pd.DataFrame: Novo DataFrame contendo apenas as colunas selecionadas.
    """
    return df[columns]


if __name__ == "__main__":
    COLUMNS_FORMATS = {
        "DT_SIN_PRI": None,
        "DT_NOTIFIC": None,
        "DT_EVOLUCA": None,
        "DT_ENTUTI": None,
        "DT_SAIDUTI": None,
        "DOSE_1_COV": "%d/%m/%Y",
        "DOSE_2_COV": "%d/%m/%Y",
        "DOSE_REF": "%d/%m/%Y",
        "DOSE_2REF": "%d/%m/%Y",
    }
    COLUMNS_SELECTED = list(COLUMNS_FORMATS.keys()) + [
        "EVOLUCAO",
        "HOSPITAL",
        "UTI",
        "VACINA_COV",
        "CLASSI_FIN",
    ]

    data_dir = Path("data")
    base_path = data_dir / "raw"
    output_path = data_dir / "staging" / "int_srag.csv"

    # Load the raw SRAG data
    df = load_dataframes(base_path=base_path)

    # Convert the datetime columns
    df = convert_to_datetime(df=df, columns_formats=COLUMNS_FORMATS)

    # Select the columns of interesst
    df = select_columns(df=df, columns=COLUMNS_SELECTED)

    # Write the cleaned SRAG data
    store_df(df=df, path=output_path)
    print("Processamento Concluído com Sucesso!")
