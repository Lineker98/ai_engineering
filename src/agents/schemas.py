from pydantic import BaseModel, Field

class AgentSRAGResposta(BaseModel):
    pensamento: str = Field(..., description="Explicação do raciocíneo")
    sql: str = Field(..., description="Query SQL gerada")
    resposta: str = Field(..., description="Resultado final")