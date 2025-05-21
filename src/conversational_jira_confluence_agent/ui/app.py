import streamlit as st
import logfire
from conversational_jira_confluence_agent.config import settings # Para acceder a las configuraciones

# Configurar Logfire (Tarea 0.3)
# Si el token está en .env, se usará para enviar a la plataforma.
# Si no, funcionará localmente (necesitarás `logfire.instrument_pydantic_ai()` etc. más adelante)
logfire.configure(
    token=settings.LOGFIRE_TOKEN, # Puede ser None si no se envía a la plataforma
    send_to_logfire="if-token-present",
    # Podrías añadir `service_name` y `service_version` aquí.
)
# logfire.instrument_pydantic_ai() # Se llamará cuando el agente esté listo

st.set_page_config(page_title="Agente Jira/Confluence", layout="wide")

st.title("🤖 Agente Conversacional para Jira y Confluence")

st.write(f"Usando el modelo PydanticAI: {settings.PYDANTIC_AI_MODEL}")
st.write(f"Conectado a Jira: {settings.JIRA_URL}")
st.write(f"Conectado a Confluence: {settings.CONFLUENCE_URL}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("¿Cómo puedo ayudarte con Jira o Confluence?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Aquí irá la lógica para llamar al agente
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        # Simulación de respuesta del agente
        simulated_response = f"Procesando tu solicitud: '{prompt}'... (Lógica del agente aún no implementada)"
        response_placeholder.markdown(simulated_response)
    st.session_state.messages.append({"role": "assistant", "content": simulated_response})

st.sidebar.info("Este es un agente en desarrollo.")