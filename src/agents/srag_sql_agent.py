from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.llms import OpenAI
from langchain.agents.agent import AgentExecutor
from langchain_openai import OpenAI
from langchain.output_parsers import PydanticOutputParser
from dotenv import load_dotenv
from pathlib import Path

from .prompt import SYSTEM_MESSAGE

import os

def create_openai_model(model='gpt-4o-mini', **kwargs) -> OpenAI:
    """_summary_

    Args:
        model (str, optional): _description_. Defaults to 'gpt-4o-mini'.

    Returns:
        OpenAI: _description_
    """
    return OpenAI(model=model, **kwargs)


def create_db_toolkit(df_path: str, llm: OpenAI) -> SQLDatabaseToolkit:
    """_summary_

    Args:
        df_path (str): _description_
        llm (OpenAI): _description_

    Returns:
        SQLDatabaseToolkit: _description_
    """
    path = Path(df_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"[ERRO] Arquivo SQLite não encontrado: {path}")
    
    db = SQLDatabase.from_uri(f'sqlite:///{df_path}')
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit


def create_agent_srag(df_path: str, model='gpt-4o-mini') -> AgentExecutor:
    llm = create_openai_model(model=model)
    toolkit = create_db_toolkit(df_path=df_path, llm=llm)
    
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit, 
        verbose=True,
        agent_kwargs={"system_message": SYSTEM_MESSAGE}
    )
    return agent