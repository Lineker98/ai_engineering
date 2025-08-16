from src.agents.orchestrator_agent import OrchestratorAgent
from dotenv import load_dotenv
import os
import logging
from src.utils.logs_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
df_path = 'data/marts/srag.sqlite'
srag_news = "data/marts/srag_news.json"
output_dir = "src/report"

if __name__ == '__main__':
    logger.info("--- START SRAG REPORT ---")
    orchestrator = OrchestratorAgent()
    orchestrator.run()
    logger.info("--- FINISH SRAG REPORT ---")