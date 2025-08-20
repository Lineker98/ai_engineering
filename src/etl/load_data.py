import pandas as pd
import asyncio
import aiohttp
from sqlalchemy import create_engine
import io
import os
import logging
from ..utils.logs_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# URLs for the datasets
URLS = [
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-18-08-2025.csv",
    "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2024/INFLUD24-26-06-2025.csv"
]

COLUMNS_TO_KEEP = [
    "DT_SIN_PRI",
    "EVOLUCAO",
    "UTI",
    "VACINA_COV",
    "CLASSI_FIN",
]

DATE_COLUMNS = ['DT_SIN_PRI']

# SQLite Database configuration
DB_NAME = "data/marts/srag.sqlite"
TABLE_NAME = "srag_data"

async def fetch_csv(session, url):
    """
    Asynchronously fetches a CSV file from a URL and returns a pandas DataFrame.
    
    Args:
        session (aiohttp.ClientSession): The client session for making HTTP requests.
        url (str): The URL of the CSV file.
        
    Returns:
        pd.DataFrame: A DataFrame containing the data from the CSV file, 
                      or an empty DataFrame if an error occurs.
    """
    logging.info(f"Starting download from: {url}")
    try:
        async with session.get(url) as response:
            response.raise_for_status()  # Raise an exception for bad status codes
            content = await response.read()
            # Use io.BytesIO to read the content in memory
            df = pd.read_csv(
                io.BytesIO(content), 
                sep=';', 
                encoding='ISO-8859-1',
                usecols=lambda c: c in COLUMNS_TO_KEEP,
                low_memory=False
            )
            logging.info(f"Finished download from: {url}")
            return df
    except aiohttp.ClientError as e:
        logging.error(f"Error downloading {url}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"An error occurred while processing {url}: {e}")
        return pd.DataFrame()
    

async def ingest_srag_data():
    """
    Main function to orchestrate the data fetching, processing, and storing.
    """
    # Checar se a base de dados existe
    if os.path.exists(DB_NAME):
        logging.info(f"Database '{DB_NAME}' already exists. Skipping download and processing.")
        return

    async with aiohttp.ClientSession() as session:
        # Obtenção concorrente de dados
        tasks = [fetch_csv(session, url) for url in URLS]
        dataframes = await asyncio.gather(*tasks)
    
    valid_dataframes = [df for df in dataframes if not df.empty]
    if not valid_dataframes:
        logging.warning("No data was downloaded. Exiting.")
        return
        
    combined_df = pd.concat(valid_dataframes, ignore_index=True)

    for col in DATE_COLUMNS:
        if col in combined_df.columns:
            combined_df[col] = pd.to_datetime(combined_df[col], errors='coerce')
        else:
            logging.warning(f"Date column '{col}' not found in the combined dataframe.")

    # --- Database Storage ---
    logging.info(f"Storing data into SQLite database: {DB_NAME}")
    try:
        engine = create_engine(f'sqlite:///{DB_NAME}')
        combined_df.to_sql(TABLE_NAME, engine, if_exists='replace', index=False)
        logging.info("Data successfully stored in the database.")
        logging.info(f"Total rows processed: {len(combined_df)}")
    except Exception as e:
        logging.error(f"Error storing data in the database: {e}")