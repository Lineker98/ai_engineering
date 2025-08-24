
import logging

logging.basicConfig(
    filename="logs/srag_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

def log_audit(user_input: str, sql: str, answer: str):
    logging.info(f"USER: {user_input}")
    logging.info(f"SQL: {sql}")
    logging.info(f"ANSWER: {answer}")
