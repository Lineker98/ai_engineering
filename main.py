from src.agents.orchestrator_agent import OrchestratorAgent
from dotenv import load_dotenv
import logging
import os
from src.utils.logs_config import setup_logging
from src.chat_app.app import run_app

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

news_query = (
    '("Síndrome Respiratória Aguda Grave" OR SRAG) (Brasil OR estados) (Covid OR Influenza OR VSR)',
)
fecther_api_key = os.getenv("SERPER_API_KEY")

if __name__ == "__main__":
    run_app()
    #logger.info("--- START SRAG REPORT ---")
    #orchestrator = OrchestratorAgent()
    #orchestrator.run(news_query=news_query, fetcher_api_key=fecther_api_key)
    #logger.info("--- FINISH SRAG REPORT ---")
