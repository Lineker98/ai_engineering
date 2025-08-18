from src.agents.orchestrator_agent import OrchestratorAgent
from dotenv import load_dotenv
import logging
from src.utils.logs_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
load_dotenv()

if __name__ == '__main__':
    logger.info("--- START SRAG REPORT ---")
    orchestrator = OrchestratorAgent()
    orchestrator.run()
    logger.info("--- FINISH SRAG REPORT ---")