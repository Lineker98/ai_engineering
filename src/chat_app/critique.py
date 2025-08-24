from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

CRITIQUE_PROMPT = ChatPromptTemplate.from_template(
    "Avalie a qualidade desta consulta SQL:\n\n{sql}\n\nJustificativa: {rationale}\n\nDê uma nota de 0 a 10 e comente brevemente."
)

def auto_critique(sql: str, rationale: str, model="gpt-4o-mini") -> str:
    """_summary_

    Args:
        sql (str): _description_
        rationale (str): _description_
        model (str, optional): _description_. Defaults to "gpt-4o-mini".

    Returns:
        str: _description_
    """
    llm = ChatOpenAI(model=model, temperature=0)
    prompt = CRITIQUE_PROMPT.format(sql=sql, rationale=rationale)
    response = llm.invoke(prompt)
    return response.content