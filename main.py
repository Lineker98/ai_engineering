from src.agents.srag_sql_agent import create_agent_srag
from dotenv import load_dotenv
import os

load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
df_path = 'data/marts/srag.sqlite'

agent = create_agent_srag(df_path=df_path)
response = agent.run("Qual a taxa de mortalidade para os pacientes com covid-19 no ano de 2025?")

print(response)