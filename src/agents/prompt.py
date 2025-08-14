from langchain_core.prompts import ChatPromptTemplate

NORMALIZE_SYSTEM = (
    "Produza a saída no esquema alvo (Pydantic). "
    "Use o histórico (incl. ToolMessages) para extrair a ÚLTIMA SQL executada. "
    "Responda apenas com o objeto final."
)

def build_normalize_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", NORMALIZE_SYSTEM),
            ("user", "Histórico completo abaixo."),
        ]
    )
    

SUMMARY_METRIC_SYSTEM = """\
Você é um especialista em dados e de saúde pública com foco em (SRAG - Síndrome Respiratória Aguda Grave).
Você irá receber amostras de dados sobre índices e métricas gerais sobe SRAG no Brasil.
Forneça insights e resumos claros sobre os dados que serão compostos pelos camos de 
`name` (Nome da métrica), `rows` (linhas retornadas das consultas SQL) e `description` (descrição
em linguagem natural da métrica)
- Seja factual, objetivo e conciso, apenas um texto de (1-3 linhas).
- Não forneça nem invente dados além dos fornecidos.
- Não retorne o nome da métrica literal, apenas sua indescrição. Ex: case_growth deve ser mencionado como
taxa de aumento de casos
"""

SUMMARY_METRIC_USER = """\
Forneça insights sobre os dados a seguir
Name: {name}
Rows: {rows}
Description: {description}
"""


PER_ARTICLE_SYSTEM = """\
Você é um assistente que resume notícias de saúde pública (SRAG - Síndrome Respiratória Aguda Grave).
Resuma APENAS com base nos campos fornecidos (title, source, published_at, text/snippet).
- Seja factual, objetivo e conciso (10–15 linhas).
- Se 'text' vier vazio, use 'snippet' e indique a limitação.
- Não invente dados. Se não houver números, não crie.
- Se a data não for clara, não especule.
Saída estritamente no esquema alvo (Pydantic).
"""

PER_ARTICLE_USER = """\
Título: {title}
Fonte: {source}
Publicado em: {published_at}
URL: {url}

Conteúdo:
{text_or_snippet}
"""

AGG_SYSTEM = """\
Você é um analista sênior de saúde. Dado um conjunto de resumos de notícias sobre SRAG (Síndrome Respiratória Aguda Grave),
com dados de título, fonte, data de publicação e url da notícia produza um sumário executivo que:
- integre os achados sem muitas repetições, com cerca de 20 à 30 linhas,
- destaque números/tendências se aparecerem em mais de uma fonte,
- aponte convergências e divergências,
- seja útil a gestores públicos.
- faça um parecer com base na integração dos dados
- Adicione, *se possível* a data dos artigos nos quais os destques são extraídos.
Saída estritamente no esquema alvo (Pydantic).
"""

AGG_USER = """\
Aqui estão os resumos individuais (JSON):
{summaries_json}
"""