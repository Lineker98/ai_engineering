# prompt.py
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
