# ui/app.py
import streamlit as st
import asyncio
import logfire
from config import settings
from agent_core.main_agent import main_agent # Importamos nuestro agente
from pydantic_ai.messages import UserPromptPart, TextPart, ModelMessage # Para el historial
from typing import List, Dict

# Configurar Logfire
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent_ui", 
    service_version="0.1.0"
)
# No hay logfire.instrument_streamlit() directo.
# La instrumentación de PydanticAI se hace donde se define el agente.
# Y las herramientas/clientes se instrumentarían con logfire.instrument_httpx() si fuera necesario.

st.set_page_config(page_title="Agente Atlassian", layout="wide")

st.title("🤖 Agente Atlassian")

# Inicializar el historial de chat en st.session_state
if "pydantic_ai_messages" not in st.session_state:
    st.session_state.pydantic_ai_messages: List[ModelMessage] = []

if "streamlit_display_messages" not in st.session_state:
    st.session_state.streamlit_display_messages: List[Dict[str, str]] = [] # Corregido tipo aquí también

# Mostrar mensajes del historial
for message in st.session_state.streamlit_display_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del usuario
if prompt := st.chat_input("¿Cómo puedo ayudarte?"):
    st.session_state.streamlit_display_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history_for_agent = list(st.session_state.pydantic_ai_messages) 

    with st.chat_message("assistant"):
        thinking_message_placeholder = st.empty()
        thinking_message_placeholder.markdown("Pensando...")
        
        try:
            # En Streamlit, para ejecutar una corrutina, es común usar asyncio.run
            # en un nuevo bucle si el contexto principal de Streamlit es síncrono.
            # Si tu Streamlit ya está en un loop async (menos común para scripts simples),
            # podrías `await` directamente.
            
            # Este enfoque es más robusto para Streamlit estándar
            response_content = ""
            new_agent_messages: List[ModelMessage] = []

            with logfire.span("agent_interaction_streamlit", user_prompt=prompt, framework="streamlit"):
                # No se puede usar asyncio.run() directamente dentro de un loop ya existente
                # si streamlit mismo usa uno. Para apps de streamlit simples, esto suele funcionar.
                # Si streamlit ejecuta esto en un hilo, new_event_loop es correcto.
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(main_agent.run(
                    prompt,
                    message_history=history_for_agent
                ))
                loop.close() # Importante cerrar el bucle

                response_content = result.output if result.output else "No se produjo una respuesta textual directa."
                new_agent_messages = result.new_messages() # Capturar nuevos mensajes

            thinking_message_placeholder.markdown(response_content) 

            st.session_state.streamlit_display_messages.append({"role": "assistant", "content": response_content})
            st.session_state.pydantic_ai_messages.extend(new_agent_messages)

        except Exception as e:
            error_message = f"Ocurrió un error: {str(e)}"
            thinking_message_placeholder.error(error_message)
            st.session_state.streamlit_display_messages.append({"role": "assistant", "content": error_message})
            logfire.error("Error en la interacción con el agente desde Streamlit: {error_message}", error_message=str(e), exc_info=True)
        
        # Forzar rerun para actualizar la UI inmediatamente después de la respuesta del agente
        # st.experimental_rerun() # Usar st.rerun() en versiones > 1.19.0
        st.rerun()


st.sidebar.info(
    "Este es un agente en desarrollo. "
    f"Modelo: {settings.PYDANTIC_AI_MODEL}. "
    # f"Jira: {settings.JIRA_URL}. " # Comentado para evitar error si settings no se carga a tiempo
    # f"Confluence: {settings.CONFLUENCE_URL}."
)
if st.sidebar.button("Limpiar historial de chat"):
    st.session_state.pydantic_ai_messages = []
    st.session_state.streamlit_display_messages = []
    # st.experimental_rerun()
    st.rerun()