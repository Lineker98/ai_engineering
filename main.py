from src.agents.srag_sql_agent import SRAGSQLAgentApp
from src.agents.srag_report_agent import SRAGMetricsReport
from src.agents.srag_summary_agent import SummaryAgent
from src.etl.news_ingest import ingest_srag_news
from dotenv import load_dotenv
import os
import json

load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
df_path = 'data/marts/srag.sqlite'
metrics_output = 'src/report/metrics/static_metrics.json'
plot_dir_metrics = 'src/report/imgs'

#agent = SRAGSQLAgentApp(sqlite_uri=df_path)
#question = "Qual a taxa de mortalidade para os pacientes com covid-19 no ano de 2025?"

#result = agent.run(question)

#print(result)
#print(result.model_dump())

agent_metrics_report = SRAGMetricsReport(sqlite_path=df_path)
bundle = agent_metrics_report.run(save_path=metrics_output, plot_dir=plot_dir_metrics)


# query = '("Síndrome Respiratória Aguda Grave" OR SRAG) (Brasil OR estados) (Covid OR Influenza OR VSR)'
# output_path = "data/marts/srag_news.json"

# articles = ingest_srag_news(query=query, output_path=output_path, top_k=10)

# agent = SummaryAgent(model="gpt-4o-mini")
# out = agent.run(
#     news_json_path=output_path,
#     save_dir="src/report/summaries",
#     meta={"query": "SRAG Brasil"}
# )