# ui/app.py
import streamlit as st
import asyncio
import logfire
from config import settings
# Nuevas importaciones para BD y cifrado
from config.user_credentials_db import user_credentials_db
from config.encryption import credential_encryption
from ui.agent_wrapper import simple_agent # Importamos nuestro agente simplificado
from pydantic_ai.messages import UserPromptPart, TextPart, ModelMessage # Para el historial
from typing import List, Dict
from tools.mem0_tools import search_memory, save_memory, precargar_memoria_completa_usuario
from datetime import datetime
from ui.custom_styles import apply_custom_title_styles, render_custom_title
from ui.agent_status_tracker import start_agent_process, render_current_status, track_context_building, track_llm_thinking, track_response_generation, finish_agent_process, status_display
import json
from pathlib import Path

# Configurar Logfire
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent_ui", 
    service_version="0.1.0"
)
# Marcar como configurado para evitar duplicados
setattr(logfire, '_configured', True)

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

# Meta viewport para responsividad móvil
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
""", unsafe_allow_html=True)

# --- CONSTANTES PARA API KEYS DE ATLASSIAN POR USUARIO ---
USER_KEYS_DIR = Path(".streamlit")
USER_KEYS_FILE = USER_KEYS_DIR / "user_atlassian_keys.json"

# --- FUNCIONES DE CIFRADO (AHORA USANDO MÓDULO REAL) ---
def _encrypt_key(api_key: str) -> str:
    """Cifra la API key usando el módulo de cifrado real"""
    return credential_encryption.encrypt(api_key)

def _decrypt_key(encrypted_key: str) -> str:
    """Descifra la API key usando el módulo de cifrado real"""
    return credential_encryption.decrypt(encrypted_key)

# --- GESTIÓN DE CREDENCIALES DE ATLASSIAN POR USUARIO (AHORA CON BD) ---
def get_atlassian_credentials_for_user(user_email: str) -> tuple[str, str]:
    """Obtiene las credenciales de Atlassian para un usuario específico desde la BD."""
    if not user_email:
        return "", ""
    
    api_key, atlassian_username = user_credentials_db.get_credentials(user_email)
    return api_key, atlassian_username

def save_atlassian_credentials_for_user(user_email: str, api_key: str, atlassian_username: str):
    """Guarda las credenciales de Atlassian para un usuario específico en la BD."""
    if not user_email:
        st.error("No se pueden guardar credenciales sin un email de usuario válido.")
        return

    if api_key and atlassian_username:
        success = user_credentials_db.save_credentials(user_email, api_key, atlassian_username)
        if success:
            logfire.info(f"Credenciales de Atlassian guardadas/actualizadas para {user_email}")
        else:
            st.error("Error al guardar las credenciales en la base de datos.")
    elif user_credentials_db.get_credentials(user_email)[0]:  # Si había credenciales previas
        success = user_credentials_db.delete_credentials(user_email)
        if success:
            logfire.info(f"Credenciales de Atlassian eliminadas para {user_email}")
        else:
            st.error("Error al eliminar las credenciales de la base de datos.")

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
    
    /* Tamaño de letra consistente en mensajes de chat - 14px */
    .stChatMessage .stMarkdown {
        font-size: 14px !important;
    }
    
    .stChatMessage .stMarkdown p {
        font-size: 14px !important;
    }
    
    .stChatMessage .stMarkdown li {
        font-size: 14px !important;
    }
    
    .stChatMessage .stMarkdown h1,
    .stChatMessage .stMarkdown h2,
    .stChatMessage .stMarkdown h3,
    .stChatMessage .stMarkdown h4,
    .stChatMessage .stMarkdown h5,
    .stChatMessage .stMarkdown h6 {
        font-size: 16px !important;
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
    
    /* ========================================
       RESPONSIVE DESIGN - MEDIA QUERIES
       ======================================== */
    
    /* Mobile First - Base styles para móvil */
    @media (max-width: 767px) {
        /* Sidebar más compacto en móvil */
        div[data-testid="stSidebar"] {
            width: 280px !important;
        }
        
                 /* Chat container altura adaptativa - más espacio */
         .stContainer[data-testid="stVerticalBlock"] {
             height: calc(100vh - 160px) !important;
             min-height: 450px !important;
             max-height: 550px !important;
         }
         
         /* Chat input responsive */
         div[data-testid="stChatInput"] {
             position: sticky !important;
             bottom: 0 !important;
             background: var(--background-color) !important;
             padding: 10px 0 !important;
             border-top: 1px solid rgba(255,255,255,0.1) !important;
         }
        
                 /* Títulos más compactos en móvil */
         .titulo-app {
             font-size: 1.5rem !important;
         }
         
         /* Títulos compactos responsive */
         div[style*="text-align: center"] h1 {
             font-size: 1.5rem !important;
             margin: 0 0 3px 0 !important;
         }
         
         div[style*="text-align: center"] p {
             font-size: 1rem !important;
             margin: 0 !important;
         }
        
        /* Mensajes de chat más compactos */
        .stChatMessage {
            margin-bottom: 0.5rem !important;
        }
        
        .stChatMessage .stMarkdown {
            font-size: 13px !important;
        }
        
        /* Usuario info más compacto */
        .user-info-flex {
            padding: 4px 6px !important;
            gap: 8px !important;
        }
        
        .user-avatar {
            width: 28px !important;
            height: 28px !important;
            font-size: 12px !important;
        }
        
        .user-name {
            font-size: 13px !important;
            max-width: 90px !important;
        }
        
        .logout-btn {
            width: 28px !important;
            height: 28px !important;
            font-size: 14px !important;
        }
        
        /* Tooltip responsive */
        .user-tooltip {
            min-width: 150px !important;
            font-size: 11px !important;
            left: -20px !important;
        }
        
        /* Fecha sidebar más compacta */
        .fecha-sidebar {
            font-size: 0.75rem !important;
            padding: 6px !important;
        }
        
        /* Botones más grandes para touch */
        div[data-testid="stSidebar"] button {
            min-height: 44px !important;
            font-size: 13px !important;
        }
        
        /* Popover más ancho en móvil */
        .stPopover {
            min-width: 250px !important;
        }
    }
    
    /* Tablet - Pantallas medianas */
    @media (min-width: 768px) and (max-width: 1024px) {
        div[data-testid="stSidebar"] {
            width: 320px !important;
        }
        
        .titulo-app {
            font-size: 2.2rem !important;
        }
        
        .stChatMessage .stMarkdown {
            font-size: 14px !important;
        }
        
        .user-name {
            max-width: 100px !important;
        }
    }
    
    /* Desktop - Pantallas grandes */
    @media (min-width: 1025px) {
        div[data-testid="stSidebar"] {
            width: 350px !important;
        }
        
        .user-name {
            max-width: 120px !important;
        }
    }
    
         /* Pantallas muy pequeñas (móviles en landscape) */
     @media (max-width: 480px) {
         .titulo-app {
             font-size: 1.3rem !important;
         }
         
         /* Títulos ultra-compactos */
         div[style*="text-align: center"] h1 {
             font-size: 1.3rem !important;
             margin: 0 0 2px 0 !important;
         }
         
         div[style*="text-align: center"] p {
             font-size: 0.9rem !important;
         }
        
        .user-info-flex {
            padding: 3px 5px !important;
            gap: 6px !important;
        }
        
        .user-avatar {
            width: 24px !important;
            height: 24px !important;
            font-size: 10px !important;
        }
        
        .user-name {
            font-size: 12px !important;
            max-width: 70px !important;
        }
        
        .logout-btn {
            width: 24px !important;
            height: 24px !important;
            font-size: 12px !important;
        }
        
        /* Chat input más grande para móvil */
        div[data-testid="stChatInput"] textarea {
            font-size: 16px !important; /* Evita zoom en iOS */
        }
    }
    
         /* Orientación landscape en móvil */
     @media (max-width: 767px) and (orientation: landscape) {
         .stContainer[data-testid="stVerticalBlock"] {
             height: calc(100vh - 100px) !important;
             max-height: 400px !important;
         }
         
         /* Sidebar se colapsa automáticamente en landscape */
         div[data-testid="stSidebar"] {
             width: 250px !important;
         }
         
         /* Títulos más compactos en landscape */
         .titulo-app {
             font-size: 1.3rem !important;
             margin: 0.5rem 0 !important;
         }
     }
     
     /* Mejoras para accesibilidad y UX */
     @media (prefers-reduced-motion: reduce) {
         * {
             animation-duration: 0.01ms !important;
             animation-iteration-count: 1 !important;
             transition-duration: 0.01ms !important;
         }
     }
     
     /* Dark mode improvements */
     @media (prefers-color-scheme: dark) {
         .user-tooltip {
             background: rgba(0,0,0,0.98) !important;
             border: 1px solid rgba(255,255,255,0.1) !important;
         }
     }
    
    /* Touch-friendly improvements */
    @media (hover: none) and (pointer: coarse) {
        /* Dispositivos touch */
        .logout-btn:hover {
            background: rgba(255, 107, 107, 0.2) !important;
        }
        
        /* Tooltip se muestra al tap en touch */
        .user-name:active + .user-tooltip {
            display: block !important;
        }
        
        /* Botones más grandes en touch */
        div[data-testid="stSidebar"] button {
            min-height: 48px !important;
            padding: 12px !important;
        }
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

# --- INICIALIZACIÓN DE CREDENCIALES DE ATLASSIAN EN SESSION STATE ---
if "atlassian_api_key" not in st.session_state or "atlassian_username" not in st.session_state:
    api_key, atl_username = get_atlassian_credentials_for_user(current_user)
    st.session_state.atlassian_api_key = api_key
    st.session_state.atlassian_username = atl_username
    
    if api_key and atl_username:
        logfire.info(f"Credenciales de Atlassian (key y username) cargadas en sesión para {current_user}")
        
        # Health check silencioso con las credenciales cargadas (opcional)
        try:
            from agent_core.main_agent import perform_health_checks
            jira_status, jira_msg, conf_status, conf_msg = perform_health_checks(atl_username, api_key)
            
            if jira_status:
                logfire.info(f"✅ Conexión Jira verificada: {jira_msg}")
            else:
                logfire.warn(f"⚠️ Conexión Jira: {jira_msg}")
                
            if conf_status:
                logfire.info(f"✅ Conexión Confluence verificada: {conf_msg}")
            else:
                logfire.warn(f"⚠️ Conexión Confluence: {conf_msg}")
                
        except Exception as e:
            # Si falla el health check, no es crítico, solo loggeamos
            logfire.warn(f"Health check opcional falló: {e}")
    else:
        logfire.info(f"No se encontraron credenciales de Atlassian persistentes completas para {current_user}.")

# --- INTERFAZ PRINCIPAL DEL CHAT ---
# Títulos compactos en la parte superior
st.markdown(f"""
<div style="text-align: center; margin: 0 0 10px 0;">
    <h1 style="
        font-family: 'Poppins', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a8a;
        margin: 0 0 5px 0;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    ">🤖 Agente Atlassian</h1>
</div>
""", unsafe_allow_html=True)

# Container para mensajes con altura maximizada
# Altura dinámica optimizada para aprovechar más espacio
chat_height = 650  # Aumentado para aprovechar el espacio ganado
chat_container = st.container(height=chat_height, border=True)
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
    
    # --- VERIFICACIÓN DE CREDENCIALES ATLASSIAN ANTES DE LLAMAR AL AGENTE ---
    is_atlassian_related_query = any(kw in prompt.lower() for kw in ["atlassian", "jira", "confluence", "issue", "ticket", "página", "espacio"])
    
    if is_atlassian_related_query and not (st.session_state.get("atlassian_api_key") and st.session_state.get("atlassian_username")):
        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(message["content"])
                # No debería haber mensajes de assistant aquí aún si el historial se maneja correctamente
            with st.chat_message("assistant", avatar="🤖"):
                st.warning("⚠️ Para consultas sobre Atlassian (Jira/Confluence), por favor configura tu API Key Y tu Nombre de Usuario de Atlassian en la barra lateral.")
                st.stop()

    # Mostrar inmediatamente la pregunta del usuario en el chat
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])
        
        # Mostrar el estado del agente dentro del chat
        with st.chat_message("assistant", avatar="🤖"):
            status_placeholder = st.empty()
    
    # Generar contexto completo (usuario + memoria)
    contexto_completo = generar_contexto_completo()
    prompt_con_contexto = f"{contexto_completo}\n\n{prompt}" if contexto_completo else prompt
    
    # Procesar respuesta del agente
    try:
        # Paso 1: Iniciar
        start_agent_process("Procesando tu consulta...")
        with status_placeholder:
            render_current_status(status_display)
        
        # Paso 2: Construir contexto
        track_context_building()
        with status_placeholder:
            render_current_status(status_display)
        
        with logfire.span("agent_interaction_streamlit", user_prompt=prompt, framework="streamlit"):
            # Paso 3: Analizar consulta
            track_llm_thinking()
            with status_placeholder:
                render_current_status(status_display)
            
            # Paso 4: Generar respuesta
            track_response_generation()
            with status_placeholder:
                render_current_status(status_display)
            
            # Ejecutar el agente
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(simple_agent.run(
                prompt_con_contexto,
                message_history=st.session_state.pydantic_ai_messages
            ))
            loop.close()
            
            # Actualizar historial con los nuevos mensajes del agente
            st.session_state.pydantic_ai_messages.extend(result.new_messages())
        
        # Reemplazar el estado con la respuesta final
        if result.output:
            with status_placeholder:
                st.markdown(result.output)
            st.session_state.chat_history.append({"role": "assistant", "content": result.output})
        else:
            error_msg = "⚠️ El agente no produjo una respuesta. Intenta reformular tu pregunta."
            with status_placeholder:
                st.markdown(error_msg)
            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
    except Exception as e:
        error_message = f"❌ **Error:** {str(e)}\n\n💡 **Sugerencias:**\n- Verifica que el modelo esté funcionando correctamente\n- Intenta simplificar tu consulta\n- Revisa la configuración del contexto de memoria"
        with status_placeholder:
            st.markdown(error_message)
        st.session_state.chat_history.append({"role": "assistant", "content": error_message})
    
    st.rerun()

# --- SIDEBAR ---
# Información del usuario minimalista y elegante
with st.sidebar:
    st.markdown(f"""
    <style>
        .user-info-flex {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 5px 8px;
            border-radius: 8px;
            background-color: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 12px;
            position: relative;
            transition: background 0.2s;
        }}
        .user-avatar {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 600;
            color: white;
            flex-shrink: 0;
        }}
        .user-name {{
            font-size: 14px;
            font-weight: 500;
            color: #fff;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 110px;
            position: relative;
            cursor: pointer;
        }}
        .user-name:hover + .user-tooltip {{
            display: block;
        }}

        .user-tooltip {{
            display: none;
            position: absolute;
            left: 0;
            top: 110%;
            background: rgba(0,0,0,0.95);
            color: #fff;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 12px;
            z-index: 10;
            min-width: 180px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }}
        
        
        /* Estilos para la sección de memoria - 14px */
        div[data-testid="stSidebar"] .stToggle label {{
            font-size: 14px !important;
        }}
        div[data-testid="stSidebar"] .stPopover button {{
            font-size: 14px !important;
        }}
        div[data-testid="stSidebar"] .stPopover .stMarkdown {{
            font-size: 14px !important;
        }}
        div[data-testid="stSidebar"] .stPopover .stMarkdown p {{
            font-size: 14px !important;
        }}
        div[data-testid="stSidebar"] .stPopover .stMarkdown li {{
            font-size: 14px !important;
        }}
    </style>
    """, unsafe_allow_html=True)
    # Mostrar fecha actual
    fecha_actual = datetime.now().strftime("%d de %B, %Y")
    st.sidebar.markdown(f'<div class="fecha-sidebar">📅 {fecha_actual}</div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    # Obtener iniciales del usuario para el avatar
    user_initials = ''.join([name[0].upper() for name in user_name.split()[:2]])
    
    # Verificar si la autenticación está disponible
    auth_available = False
    try:
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            auth_available = True
    except (AttributeError, KeyError):
        pass
    
    if auth_available:
        # Usuario autenticado con hover tooltip y botón integrado
        user_display_name = user_name if len(user_name) <= 20 else user_name[:17] + "..."
        
                # Crear un contenedor único con flexbox para alineación perfecta
        st.markdown(f"""
        <div class="user-info-flex">
            <div class="user-avatar">{user_initials}</div>
            <div style="display: flex; flex-direction: column; flex: 1;">
                <div class="user-name" title="{user_name}">{user_display_name}</div>
                <div class="user-tooltip">{current_user}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de logout alineado usando CSS absoluto
        st.markdown("""
        <style>
            .user-info-flex {
                position: relative;
                padding-right: 40px; /* Espacio para el botón */
            }
            
            /* Estilar el botón de Streamlit para que se vea como nuestro diseño */
            div[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
                position: absolute !important;
                top: 50% !important;
                right: 8px !important;
                transform: translateY(-50%) !important;
                width: 32px !important;
                height: 32px !important;
                min-height: 32px !important;
                background: transparent !important;
                border: none !important;
                border-radius: 50% !important;
                color: #ff6b6b !important;
                font-size: 16px !important;
                padding: 0 !important;
                transition: all 0.2s !important;
                z-index: 10 !important;
            }
            
            div[data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover {
                background: rgba(255, 107, 107, 0.1) !important;
                color: #ee5a24 !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("🚪", key="logout_btn", help="Cerrar sesión"):
            st.logout()
        


    else:
        # Modo sin autenticación
        st.markdown(f"""
        <div class="user-info-flex">
            <div class="user-avatar">{user_initials}</div>
            <div style="display: flex; flex-direction: column; flex: 1;">
                <div class="user-name">{user_name}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="auth-info">
            Modo demo - Para autenticación multi-usuario configura OAuth2
        </div>
        """, unsafe_allow_html=True)

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

# El estado se muestra en el toggle, no necesitamos indicador adicional

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

# Sección de acciones - separada del área de memoria
st.sidebar.markdown("---")
col1, col2, col3 = st.sidebar.columns([1, 2, 1])
with col2:
    if st.button("Limpiar historial", use_container_width=True  ):
        st.session_state.pydantic_ai_messages = []
        st.session_state.streamlit_display_messages = []
        st.session_state.chat_history = []
        st.rerun()

# El logout se maneja automáticamente a través del formulario HTML en la sección de usuario


# --- CONFIGURACIÓN DE ATLASSIAN API KEY ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 Configuración Atlassian") # Título generalizado

# Este estado refleja si las credenciales están en la SESIÓN ACTUAL
if st.session_state.get("atlassian_api_key") and st.session_state.get("atlassian_username"):
    st.sidebar.success("Credenciales de Atlassian ✅")
elif st.session_state.get("atlassian_api_key"):
    st.sidebar.warning("Falta el nombre de usuario de Atlassian.")
elif st.session_state.get("atlassian_username"):
    st.sidebar.warning("Falta la API Key de Atlassian.")
else:
    st.sidebar.error("Credenciales de Atlassian NO configuradas.")

with st.sidebar.popover("Gestionar Credenciales de Atlassian", use_container_width=True):
    st.markdown("#### Tus Credenciales de Atlassian")
    st.markdown(
        """
        Ingresa tu API key personal y tu nombre de usuario de Atlassian.
        Se guardarán de forma persistente para futuras sesiones.
        
        **Importante:** El cifrado de la API Key es un *placeholder*. Implementa cifrado robusto.
        El nombre de usuario se guarda como texto plano.
        """
    )

    key_for_input = st.session_state.get("atlassian_api_key", "")
    username_for_input = st.session_state.get("atlassian_username", "")
    
    new_api_key_input = st.text_input(
        "Tu Atlassian API Key:",
        type="password",
        value=key_for_input,
        placeholder="Pega tu API key aquí"
    )
    
    new_username_input = st.text_input(
        "Tu Nombre de Usuario Atlassian (email):",
        value=username_for_input,
        placeholder="ej: tu.email@dominio.com"
    )

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Guardar Credenciales", use_container_width=True, type="primary"):
            if new_api_key_input and new_username_input:
                save_atlassian_credentials_for_user(current_user, new_api_key_input, new_username_input)
                st.session_state.atlassian_api_key = new_api_key_input
                st.session_state.atlassian_username = new_username_input
                st.success("¡Credenciales guardadas!")
                logfire.info(f"Credenciales de Atlassian guardadas/actualizadas por {current_user}")
                st.rerun()
            else:
                st.warning("Ingresa API Key y Nombre de Usuario.")
    
    with col_clear:
        if st.button("🗑️ Borrar Guardadas", use_container_width=True):
            save_atlassian_credentials_for_user(current_user, "", "") # Guardar vacío borra
            st.session_state.atlassian_api_key = ""
            st.session_state.atlassian_username = ""
            st.info("Credenciales eliminadas de persistencia.")
            logfire.info(f"Credenciales de Atlassian eliminadas por {current_user}")
            st.rerun()

    st.markdown("---")
    # Verifica directamente de persistencia para el mensaje
    _, stored_username = get_atlassian_credentials_for_user(current_user) 
    if stored_username: # Si hay username, asumimos que hay (o hubo) key
        st.caption("ℹ️ Ya tienes credenciales guardadas. Ingresar nuevas las reemplazará.")
    else:
        st.caption("ℹ️ Aún no has guardado credenciales.")


# Información del sistema al final absoluto del sidebar
with st.sidebar:
    st.markdown("---")
    st.markdown(f"""
    <div style="
        font-size: 10px !important; 
        color: #666; 
        text-align: center; 
        padding: 8px 4px; 
        line-height: 1.3;
        opacity: 0.7;
        font-family: inherit;
    ">
        {settings.PYDANTIC_AI_MODEL}<br>
        <span style="font-size: 10px !important;">v0.1.0 beta</span>
    </div>
    """, unsafe_allow_html=True)


st.sidebar.markdown("---")