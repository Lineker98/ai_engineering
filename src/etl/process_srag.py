import pandas as pd
from typing import List, Dict
from pathlib import Path

def convert_to_datetime(df: pd.DataFrame, columns_formats: Dict, errors='coerce') -> pd.DataFrame:
    """
    Convert especific column into datetime

    Args:
        df (pd.DataFrame): _description_
        columns_formats (Dict): _description_
        errors (str, optional): _description_. Defaults to 'coerce'.

    Returns:
        _type_: _description_
    """
    for col, format in columns_formats.items():
        df[col] = pd.to_datetime(df[col], format=format, errors=errors)
    print('Conversão de dados realizada!')
    return df

def load_df(df_path: str, sep=';', encoding='latin1', low_memory=False) -> pd.DataFrame:
    """
    Loads a CSV file into a pandas DataFrame.

    Args:
        df_path (str): Path to the CSV file.
        sep (str, optional): Delimiter to use. Defaults to ';'.
        encoding (str, optional): File encoding. Defaults to 'latin1'.
        low_memory (bool, optional): Internally process the file in chunks to lower memory usage. 
                                     Defaults to False.

    Returns:
        pd.DataFrame: DataFrame containing the contents of the loaded CSV file.
    """
    df = pd.read_csv(df_path, sep=sep, encoding=encoding, low_memory=low_memory)
    print('Carregamento de dados realizado!')
    return df

def store_df(df: pd.DataFrame, path: Path) -> None:
    """
    Stores a pandas DataFrame as a CSV file at the specified path.

    Args:
        df (pd.DataFrame): The DataFrame to be saved.
        path (Path): Full path (including filename) where the CSV file will be saved.

    Notes:
        - Creates any missing parent directories automatically.
        - The resulting CSV will not include the index column.
    """
    # Garante que a pasta exista
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def select_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Returns a new DataFrame containing only the specified columns.

    Args:
        df (pd.DataFrame): The original DataFrame.
        columns (List[str]): A list of column names to select from the DataFrame.

    Returns:
        pd.DataFrame: A DataFrame with only the selected columns.
    """
    return df[columns]
    

if __name__ == '__main__':
    COLUMNS_FORMATS = {
        'DT_SIN_PRI': None,
        'DT_NOTIFIC': None,
        'DT_EVOLUCA': None,
        'DT_ENTUTI': None,
        'DT_SAIDUTI': None,
        'DOSE_1_COV': "%d/%m/%Y",
        'DOSE_2_COV': "%d/%m/%Y",
        'DOSE_REF': "%d/%m/%Y",
        'DOSE_2REF': "%d/%m/%Y"
    }
    COLUMNS_SELECTED = list(COLUMNS_FORMATS.keys()) + ['EVOLUCAO', 'HOSPITAL', 'UTI', 'VACINA_COV', 'CLASSI_FIN']
    
    # Diretórios
    data_dir = Path("data")
    df_raw_path = data_dir / "raw" / "INFLUD25-04-08-2025.csv"
    output_path = data_dir / "staging" / "int_srag.csv"
    
    
    # Load the raw SRAG data
    df = load_df(df_raw_path)
    
    # Convert the datetime columns
    df = convert_to_datetime(df=df, columns_formats=COLUMNS_FORMATS)
    
    # Select the columns of interesst
    df = select_columns(df=df, columns=COLUMNS_SELECTED)
    
    # Write the cleaned SRAG data
    store_df(df=df, path=output_path)
    print('Processamento Concluído com Sucesso!')
