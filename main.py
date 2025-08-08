from src.agents.srag_sql_agent import SRAGSQLAgentApp
from dotenv import load_dotenv
import os

load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
df_path = 'data/marts/srag.sqlite'

agent = SRAGSQLAgentApp(sqlite_uri=df_path)
question = "Qual a taxa de mortalidade para os pacientes com covid-19 no ano de 2025?"

result = agent.run(question)

print(result)
print(result.model_dump())