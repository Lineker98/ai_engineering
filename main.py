from src.agents.srag_sql_agent import SRAGSQLAgentApp
from src.agents.srag_report_agent import SRAGMetricsReport
from src.utils.plots import plot_daily_cases_last_30_days, plot_monthly_cases_last_12_months
from src.etl.news_ingest import ingest_srag_news
from dotenv import load_dotenv
import os
import json

load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
df_path = 'data/marts/srag.sqlite'
metrics_output = 'src/report/metrics/static_metrics.json'

#agent = SRAGSQLAgentApp(sqlite_uri=df_path)
#question = "Qual a taxa de mortalidade para os pacientes com covid-19 no ano de 2025?"

#result = agent.run(question)

#print(result)
#print(result.model_dump())

# agent_metrics_report = SRAGMetricsReport(sqlite_path=df_path)
# bundle = agent_metrics_report.run(save_path=metrics_output)

# plot_daily_cases_last_30_days(
#     df_path, "src/report/imgs/casos_diarios_30d_covid",
#     where_clause="CLASSI_FIN = 5", 
#     rolling_days=7, json_path='src/report/metrics/chart_last_30_daily_cases.json'
# )

# plot_monthly_cases_last_12_months(
#     df_path, "src/report/imgs/casos_mensais_12m_covid",
#     where_clause="CLASSI_FIN = 5", json_path='src/report/metrics/chart_last_12_montly_cases.json'
# )


query = '("Síndrome Respiratória Aguda Grave" OR SRAG) (Brasil OR estados) (Covid OR Influenza OR VSR)'
output_path = "src/report/metrics/srag_news.json"

articles = ingest_srag_news(query=query, output_path=output_path, top_k=5)