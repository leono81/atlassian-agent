# ui/app.py
import streamlit as st
import asyncio
import logfire
from config import settings
from agent_core.main_agent import main_agent # Importamos nuestro agente
from pydantic_ai.messages import UserPromptPart, TextPart, ModelMessage # Para el historial
from typing import List, Dict
from tools.mem0_tools import search_memory, save_memory, precargar_memoria_completa_usuario
from datetime import datetime
from ui.custom_styles import apply_custom_title_styles, render_custom_title

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

# Configuración de página y CSS personalizado
st.set_page_config(
    page_title="Agente Atlassian",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE AUTENTICACIÓN ---
def check_authentication():
    """
    Verifica si el usuario está autenticado y maneja el flujo de login.
    Retorna True si está autenticado, False si no.
    """
    # Verificar si la autenticación nativa está disponible y configurada
    try:
        # Intentar acceder a st.user de forma segura
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            return True
    except (AttributeError, KeyError) as e:
        # La autenticación nativa no está configurada o disponible
        # Mostrar mensaje informativo y permitir acceso sin autenticación
        st.info("ℹ️ **Modo sin autenticación**: La autenticación OAuth2 no está configurada. "
                "La aplicación funcionará con un usuario por defecto.")
        
        with st.expander("🔧 ¿Quieres configurar autenticación multi-usuario?"):
            st.markdown("""
            **Para habilitar autenticación con Google:**
            
            1. 📋 Sigue la guía: `SETUP_OAUTH.md`
            2. 🔑 Configura: `.streamlit/secrets.toml`
            3. ✅ Verifica: `python verify_auth_setup.py`
            4. 🚀 Reinicia la aplicación
            
            **Beneficios de la autenticación:**
            - 👥 Múltiples usuarios
            - 🔒 Datos privados por usuario
            - 🧠 Memoria personalizada
            - 🔐 Acceso seguro
            """)
        
        # Permitir continuar sin autenticación
        return True
    
    # Si llegamos aquí, la autenticación está disponible pero el usuario no está logueado
    st.markdown("# 🔐 Acceso al Agente Atlassian")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        ### Bienvenido al Agente Atlassian
        
        Para acceder a la aplicación, necesitas autenticarte con tu cuenta de Google.
        
        **Características:**
        - 🤖 Agente inteligente para Jira y Confluence
        - 🧠 Memoria personalizada con tus alias y configuraciones
        - 🔒 Datos seguros y privados por usuario
        - 📊 Historial de conversaciones persistente
        """)
        
        st.markdown("---")
        
        # Botón de login centrado
        if st.button("🚀 Iniciar Sesión con Google", 
                    use_container_width=True, 
                    type="primary"):
            try:
                st.login()
            except Exception as e:
                st.error(f"Error durante el login: {e}")
                st.info("💡 **Posibles soluciones:**\n"
                       "- Verifica que hayas configurado correctamente Google OAuth2\n"
                       "- Revisa el archivo `.streamlit/secrets.toml`\n"
                       "- Consulta `SETUP_OAUTH.md` para más detalles")
        
        st.markdown("---")
        st.caption("🔒 Tu privacidad es importante. Solo accedemos a tu email para identificarte.")
    
    return False

# Verificar autenticación antes de mostrar la app
if not check_authentication():
    st.stop()  # Detener ejecución si no está autenticado

# Usuario autenticado - continuar con la aplicación
def get_user_info():
    """Obtiene información del usuario de forma segura."""
    try:
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            email = getattr(st.user, 'email', 'usuario_autenticado')
            name = getattr(st.user, 'name', email)
            return email, name
    except (AttributeError, KeyError):
        pass
    
    # Fallback para modo sin autenticación
    return "atlassian_agent_user_001", "Usuario Demo"

current_user, user_name = get_user_info()

# Aplicar estilos personalizados para títulos
apply_custom_title_styles()

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    /* Ocultar el título principal para evitar duplicación */
    .main > div:first-child h1 {
        display: none;
    }
    
    /* Mejorar el aspecto del container de chat */
    .stContainer {
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* Espaciado mejorado para mensajes de chat */
    .stChatMessage {
        margin-bottom: 0.8rem;
    }
    
    /* Estilo minimalista para métricas en el sidebar */
    [data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.05);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 6px 10px;
        border-radius: 6px;
        margin: 2px 0;
    }
    
    /* Mejorar el aspecto del popover */
    .stPopover {
        border-radius: 8px;
    }
    
    /* Estilo para fechas en sidebar */
    .fecha-sidebar {
        font-size: 0.85rem;
        color: #666;
        text-align: center;
        padding: 8px;
        background-color: rgba(0,0,0,0.03);
        border-radius: 6px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES UTILITARIAS ---
def precargar_memoria_usuario():
    """Precarga la memoria del usuario desde Mem0 al iniciar la app."""
    if "memoria_usuario" not in st.session_state:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(precargar_memoria_completa_usuario(limit=100))
            loop.close()
            
            memoria = {}
            if result and hasattr(result, "results") and result.status == "ok":
                for mem in result.results:
                    if mem.alias and mem.value:
                        memoria[mem.alias] = mem.value
                logfire.info(f"Memoria precargada exitosamente: {len(memoria)} alias cargados.")
            else:
                logfire.warn(f"No se pudo precargar la memoria: {result.status if result else 'resultado nulo'}")
            
            st.session_state["memoria_usuario"] = memoria
            
        except Exception as e:
            logfire.error(f"Error durante la precarga de memoria: {e}", exc_info=True)
            st.session_state["memoria_usuario"] = {}

def resolver_alias(alias):
    """Resuelve un alias desde la memoria precargada."""
    memoria = st.session_state.get("memoria_usuario", {})
    return memoria.get(alias)

def guardar_nuevo_alias(alias, value):
    """Guarda un nuevo alias tanto en sesión como en Mem0."""
    if "memoria_usuario" not in st.session_state:
        st.session_state["memoria_usuario"] = {}
    st.session_state["memoria_usuario"][alias] = value
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(save_memory(alias=alias, value=value))
    loop.close()

def generar_contexto_completo():
    """Genera un string con información del usuario y memoria para pasarla como contexto al agente."""
    contexto_partes = []
    
    # 1. Información del usuario
    contexto_partes.append(f"USUARIO: {user_name} (email: {current_user})")
    
    # 2. Memoria del usuario (si está activa)
    if st.session_state.get("usar_contexto_memoria", True):
        memoria = st.session_state.get("memoria_usuario", {})
        if memoria:
            max_alias = 10
            memoria_items = list(memoria.items())[:max_alias]
            alias_lines = [f"'{alias}' → {value}" for alias, value in memoria_items]
            
            total_alias = len(memoria)
            if total_alias > max_alias:
                alias_lines.append(f"... y {total_alias - max_alias} alias más en memoria")
            
            contexto_partes.append(f"MEMORIA: {', '.join(alias_lines)}")
    
    return "\n".join(contexto_partes) if contexto_partes else ""

def generar_contexto_memoria():
    """Función legacy - mantener para compatibilidad."""
    return generar_contexto_completo()

# --- INICIALIZACIÓN DEL ESTADO ---
if "pydantic_ai_messages" not in st.session_state:
    st.session_state.pydantic_ai_messages: List[ModelMessage] = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history: List[Dict[str, str]] = []

if "streamlit_display_messages" not in st.session_state:
    st.session_state.streamlit_display_messages: List[Dict[str, str]] = []

if "usar_contexto_memoria" not in st.session_state:
    st.session_state.usar_contexto_memoria = True

# Ejecutar precarga de memoria una sola vez
precargar_memoria_usuario()

# --- INTERFAZ PRINCIPAL DEL CHAT ---
# Título personalizado con nombre del usuario usando estilos personalizados
render_custom_title(f"Agente Atlassian", "app", "🤖")
st.markdown(f"### Hola {user_name.split()[0]}!")
# Container para mensajes con altura aumentada y scroll
chat_container = st.container(height=600, border=True)
with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(message["content"])
        elif message["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(message["content"])

# Chat input siempre visible en la parte inferior
if prompt := st.chat_input("💬 Escribe tu consulta aquí...", key="main_chat"):
    # Agregar mensaje del usuario al historial
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # Generar contexto completo (usuario + memoria)
    contexto_completo = generar_contexto_completo()
    prompt_con_contexto = f"{contexto_completo}\n\n{prompt}" if contexto_completo else prompt
    
    # Procesar respuesta del agente
    try:
        with st.status("🤖 Procesando tu consulta...", expanded=True) as status:
            st.write("🔍 Consultando memoria...")
            st.write("🔧 Ejecutando herramientas...")
            
            with logfire.span("agent_interaction_streamlit", user_prompt=prompt, framework="streamlit"):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(main_agent.run(
                    prompt_con_contexto,
                    message_history=st.session_state.pydantic_ai_messages
                ))
                loop.close()
                
                # Actualizar historial con los nuevos mensajes del agente
                st.session_state.pydantic_ai_messages.extend(result.new_messages())
            
            status.update(label="✅ Respuesta lista!", state="complete")
        
        # Agregar respuesta al historial para visualización
        if result.output:
            st.session_state.chat_history.append({"role": "assistant", "content": result.output})
        else:
            st.session_state.chat_history.append({"role": "assistant", "content": "⚠️ El agente no produjo una respuesta. Intenta reformular tu pregunta."})
            
    except Exception as e:
        error_message = f"❌ **Error:** {str(e)}\n\n💡 **Sugerencias:**\n- Verifica que el modelo esté funcionando correctamente\n- Intenta simplificar tu consulta\n- Revisa la configuración del contexto de memoria"
        st.session_state.chat_history.append({"role": "assistant", "content": error_message})
    
    st.rerun()

# --- SIDEBAR ---
# Información del usuario autenticado
st.sidebar.markdown("### 👤 Usuario")
st.sidebar.markdown(f"**{user_name}**")
st.sidebar.markdown(f"📧 `{current_user}`")

# Botón de logout (solo si la autenticación está disponible)
try:
    # Verificar si la autenticación está disponible antes de mostrar logout
    if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.logout()
    else:
        # En modo sin autenticación, mostrar información en lugar del botón
        st.sidebar.info("🔓 **Modo sin autenticación**\n\nPara habilitar login/logout, configura OAuth2 siguiendo `SETUP_OAUTH.md`")
except (AttributeError, KeyError):
    # La autenticación no está disponible
    st.sidebar.info("🔓 **Modo sin autenticación**\n\nPara habilitar login/logout, configura OAuth2 siguiendo `SETUP_OAUTH.md`")

st.sidebar.markdown("---")

# Mostrar fecha actual
fecha_actual = datetime.now().strftime("%d de %B, %Y")
st.sidebar.markdown(f'<div class="fecha-sidebar">📅 {fecha_actual}</div>', unsafe_allow_html=True)

st.sidebar.info(
    f"**Modelo:** {settings.PYDANTIC_AI_MODEL}\n\n"
    f"*Versión de desarrollo*"
)

st.sidebar.markdown("---")

# EJEMPLO DE DASHBOARD DE MÉTRICAS (comentado)
# st.sidebar.markdown("### 📊 Métricas del Sistema")
# col1, col2 = st.sidebar.columns(2)
# with col1:
#     total_messages = len(st.session_state.chat_history)
#     st.metric("💬 Mensajes", total_messages, delta=1 if total_messages > 0 else 0)
# with col2:
#     st.metric("🔧 Herramientas", 16, delta="+3")
# st.sidebar.progress(0.85, "Funcionamiento: 85%")

# Controles de memoria
memoria_usuario = st.session_state.get("memoria_usuario", {})
cantidad_alias = len(memoria_usuario)

# Toggle para activar/desactivar contexto completo
contexto_activo = st.sidebar.toggle(
    "🧠 Usar contexto completo", 
    value=st.session_state.usar_contexto_memoria,
    help="Cuando está activo, el agente conoce tu nombre, email y alias automáticamente sin buscar en memoria."
)
st.session_state.usar_contexto_memoria = contexto_activo

# Indicador visual del estado
if contexto_activo and cantidad_alias > 0:
    st.sidebar.success(f"✅ Contexto activo: usuario + {cantidad_alias} alias")
elif contexto_activo and cantidad_alias == 0:
    st.sidebar.success("✅ Contexto activo: usuario (sin alias)")
else:
    st.sidebar.info("ℹ️ Contexto desactivado - el agente usará search_memory")

# Popover para ver la memoria (sin ícono del ojo)
with st.sidebar.popover(f"Ver memoria ({cantidad_alias} alias)", use_container_width=True):
    if memoria_usuario:
        st.markdown("**🎯 Alias disponibles:**")
        for alias, value in memoria_usuario.items():
            st.markdown(f"• **{alias}** → `{value}`")
        
        st.markdown("---")
        st.caption(f"Total: {cantidad_alias} alias precargados")
        
        if st.button("🔄 Recargar memoria", use_container_width=True):
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
    st.session_state.chat_history = []
    st.rerun()