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


PER_ARTICLE_SYSTEM = """\
Você é um assistente que resume notícias de saúde pública (SRAG - Síndrome Respiratória Aguda Grave).
Resuma APENAS com base nos campos fornecidos (title, source, published_at, text/snippet).
- Seja factual, objetivo e conciso (6–10 linhas).
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
Você é um analista sênior. Dado um conjunto de resumos de notícias sobre SRAG (Síndrome Respiratória Aguda Grave),
produza um sumário executivo que:
- integre os achados (sem repetir muito),
- destaque números/tendências se aparecerem em mais de uma fonte,
- aponte convergências e divergências,
- seja útil a gestores públicos.
Saída estritamente no esquema alvo (Pydantic).
"""

AGG_USER = """\
Aqui estão os resumos individuais (JSON):
{summaries_json}
"""