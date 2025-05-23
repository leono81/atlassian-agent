# ui/app.py
import streamlit as st
import asyncio
import logfire
from config import settings
from agent_core.main_agent import main_agent # Importamos nuestro agente
from pydantic_ai.messages import UserPromptPart, TextPart, ModelMessage # Para el historial
from typing import List, Dict
from tools.mem0_tools import search_memory, save_memory, precargar_memoria_completa_usuario

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

# --- Precarga de memoria del usuario al iniciar la app ---
def precargar_memoria_usuario():
    if "memoria_usuario" not in st.session_state:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Usar la función específica para precarga que maneja errores robustamente
            result = loop.run_until_complete(precargar_memoria_completa_usuario(limit=100))
            loop.close()
            
            memoria = {}
            if result and hasattr(result, "results") and result.status == "ok":
                for mem in result.results:
                    if mem.alias and mem.value:  # Solo agregar alias válidos
                        memoria[mem.alias] = mem.value
                logfire.info(f"Memoria precargada exitosamente: {len(memoria)} alias cargados.")
            else:
                logfire.warn(f"No se pudo precargar la memoria: {result.status if result else 'resultado nulo'}")
            
            st.session_state["memoria_usuario"] = memoria
            
        except Exception as e:
            logfire.error(f"Error durante la precarga de memoria: {e}", exc_info=True)
            # Inicializar memoria vacía en caso de error
            st.session_state["memoria_usuario"] = {}

precargar_memoria_usuario()

# --- Funciones utilitarias para consultar y actualizar alias ---
def resolver_alias(alias):
    memoria = st.session_state.get("memoria_usuario", {})
    return memoria.get(alias)

def guardar_nuevo_alias(alias, value):
    # Actualiza en sesión
    if "memoria_usuario" not in st.session_state:
        st.session_state["memoria_usuario"] = {}
    st.session_state["memoria_usuario"][alias] = value
    # Actualiza en Mem0 (persistente)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(save_memory(alias=alias, value=value))
    loop.close()

# --- Ejemplo de uso en el flujo conversacional ---
# Para resolver un alias antes de registrar tiempo:
# issue_key = resolver_alias("la daily")
# if issue_key:
#     # Usar issue_key directamente
#     pass
# else:
#     # Pedir al usuario o buscar en Mem0 si no está en la memoria precargada
#     pass

# Para guardar un nuevo alias:
# guardar_nuevo_alias("la daily", "PSIMDESASW-9999")

# --- Función para generar contexto de memoria ---
def generar_contexto_memoria():
    """Genera un string con la memoria precargada para pasarla como contexto al agente."""
    # Verificar si el usuario quiere usar contexto de memoria
    if not st.session_state.get("usar_contexto_memoria", True):
        return ""
    
    memoria = st.session_state.get("memoria_usuario", {})
    if not memoria:
        return ""
    
    # Limitar la cantidad de alias para evitar contexto muy largo
    max_alias = 10  # Máximo 10 alias en el contexto
    memoria_items = list(memoria.items())[:max_alias]
    
    # Generar contexto más compacto
    alias_lines = [f"'{alias}' → {value}" for alias, value in memoria_items]
    
    # Si hay más alias, indicarlo
    total_alias = len(memoria)
    if total_alias > max_alias:
        alias_lines.append(f"... y {total_alias - max_alias} alias más en memoria")
    
    contexto = f"MEMORIA: {', '.join(alias_lines)}"
    return contexto

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
            # Generar contexto de memoria para el agente
            contexto_memoria = generar_contexto_memoria()
            
            # Construir prompt con contexto de memoria si existe
            prompt_con_contexto = prompt
            if contexto_memoria:
                prompt_con_contexto = f"{contexto_memoria}\n\n{prompt}"
            
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
                    prompt_con_contexto,  # Usar el prompt con contexto
                    message_history=history_for_agent
                ))
                loop.close() # Importante cerrar el bucle

                response_content = result.output if result.output else "No se produjo una respuesta textual directa."
                new_agent_messages = result.new_messages() # Capturar nuevos mensajes

            thinking_message_placeholder.markdown(response_content) 

            st.session_state.streamlit_display_messages.append({"role": "assistant", "content": response_content})
            st.session_state.pydantic_ai_messages.extend(new_agent_messages)

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            # Detectar tipos específicos de errores para dar mejor feedback
            if "500" in error_message or "server_error" in error_message:
                user_error_msg = f"🚨 Error del servidor de OpenAI (500). Esto puede ser temporal.\n\n**Sugerencias:**\n- Inténtalo de nuevo en unos segundos\n- Si persiste, puede ser un problema con el modelo `{settings.PYDANTIC_AI_MODEL}`\n\n*Error técnico: {error_type}*"
            elif "model" in error_message.lower() and ("not found" in error_message.lower() or "invalid" in error_message.lower()):
                user_error_msg = f"❌ Modelo inválido: `{settings.PYDANTIC_AI_MODEL}`\n\n**Modelos válidos de OpenAI:**\n- `openai:gpt-4o-mini` (recomendado)\n- `openai:gpt-4o`\n- `openai:gpt-3.5-turbo`\n\n*Error técnico: {error_type}*"
            elif "token" in error_message.lower() or "context" in error_message.lower():
                user_error_msg = f"📏 Contexto muy largo para el modelo.\n\n**Prueba:**\n- Desactivar el contexto de memoria temporalmente\n- Usar un mensaje más corto\n\n*Error técnico: {error_type}*"
            else:
                user_error_msg = f"💥 Error inesperado: {error_message}\n\n*Tipo: {error_type}*"
            
            thinking_message_placeholder.error(user_error_msg)
            st.session_state.streamlit_display_messages.append({"role": "assistant", "content": user_error_msg})
            logfire.error("Error en la interacción con el agente desde Streamlit: {error_message}", error_message=str(e), exc_info=True)
        
        # Forzar rerun para actualizar la UI inmediatamente después de la respuesta del agente
        # st.experimental_rerun() # Usar st.rerun() en versiones > 1.19.0
        st.rerun()


st.sidebar.info(
    f"🤖 **Agente Atlassian**\n\n"
    f"**Modelo:** `{settings.PYDANTIC_AI_MODEL}`\n\n"
    f"*Versión de desarrollo*"
    # f"Jira: {settings.JIRA_URL}. " # Comentado para evitar error si settings no se carga a tiempo
    # f"Confluence: {settings.CONFLUENCE_URL}."
)

# --- Controles modernos de memoria en el sidebar ---
st.sidebar.markdown("---")

# Estado de memoria (inicializar si no existe)
if "usar_contexto_memoria" not in st.session_state:
    st.session_state.usar_contexto_memoria = True

memoria_usuario = st.session_state.get("memoria_usuario", {})
cantidad_alias = len(memoria_usuario)

# Toggle para activar/desactivar contexto de memoria
contexto_activo = st.sidebar.toggle(
    "🧠 Usar contexto de memoria", 
    value=st.session_state.usar_contexto_memoria,
    help="Cuando está activo, el agente conoce automáticamente tus alias sin buscar en memoria."
)
st.session_state.usar_contexto_memoria = contexto_activo

# Indicador visual del estado
if contexto_activo and cantidad_alias > 0:
    st.sidebar.success(f"✅ Contexto activo ({cantidad_alias} alias cargados)")
elif contexto_activo and cantidad_alias == 0:
    st.sidebar.warning("⚠️ Contexto activo pero sin alias")
else:
    st.sidebar.info("ℹ️ Contexto desactivado - el agente usará search_memory")

# Popover para ver la memoria
with st.sidebar.popover(f"👁️ Ver memoria ({cantidad_alias} alias)", use_container_width=True):
    if memoria_usuario:
        st.markdown("**🎯 Alias disponibles:**")
        for alias, value in memoria_usuario.items():
            st.markdown(f"• **{alias}** → `{value}`")
        
        st.markdown("---")
        st.caption(f"Total: {cantidad_alias} alias precargados")
        
        # Botón para refrescar memoria
        if st.button("🔄 Recargar memoria", use_container_width=True):
            # Limpiar memoria actual y recargar
            if "memoria_usuario" in st.session_state:
                del st.session_state["memoria_usuario"]
            st.rerun()
    else:
        st.warning("No hay alias cargados")
        st.markdown("Los alias se crean cuando:")
        st.markdown("- El agente guarda información por ti")
        st.markdown("- Usas la herramienta `save_memory`")

if st.sidebar.button("Limpiar historial de chat"):
    st.session_state.pydantic_ai_messages = []
    st.session_state.streamlit_display_messages = []
    # st.experimental_rerun()
    st.rerun()