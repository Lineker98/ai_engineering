import streamlit as st
from .srag_sql_agent import SRAGSQLAgentApp
from .srag_chat import SRAGSQLAgentChat
from .critique import auto_critique


def run_app():
    st.set_page_config(page_title="Agente SQL SRAG", layout="wide")
    st.title("🧠 Agente SRAG SQL")

    if "chat" not in st.session_state:
        agent = SRAGSQLAgentApp("data/marts/srag.sqlite")
        st.session_state.chat = SRAGSQLAgentChat(agent)

    user_input = st.text_input("Digite sua pergunta:", key="input")

    if user_input:
        try:
            with st.spinner("Consultando banco de dados..."):
                result = st.session_state.chat.ask(user_input)

            st.success("✅ Resposta encontrada!")
            st.markdown(f"**📢 Resposta:** {result.answer}")
            st.code(result.sql, language="sql")
            st.markdown(f"🧾 *Justificativa:* {result.rationale}")

            critique = auto_critique(result.sql, result.rationale)
            st.markdown(f"🧠 **Avaliação da LLM:** {critique}")

        except Exception as e:
            st.error(f"Erro: {str(e)}")