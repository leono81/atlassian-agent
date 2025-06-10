# ui/app.py
import streamlit as st
import asyncio
import logfire
from config import settings
# Nuevas importaciones para BD y cifrado
from config.user_credentials_db import user_credentials_db
from config.encryption import credential_encryption
# NUEVO: Sistema de logging robusto con contexto de usuario
from config.logging_context import (
    UserLoggingContext, logger, log_user_action, log_system_event, log_operation
)
from ui.agent_wrapper import simple_agent # Importamos nuestro agente simplificado
from pydantic_ai.messages import UserPromptPart, TextPart, ModelMessage # Para el historial
from typing import List, Dict
from tools.mem0_tools import search_memory, save_memory, precargar_memoria_completa_usuario
from datetime import datetime
from ui.custom_styles import apply_custom_title_styles, render_custom_title
from ui.agent_status_tracker import start_agent_process, render_current_status, track_context_building, track_llm_thinking, track_response_generation, finish_agent_process, status_display
import json
from pathlib import Path
import time
import uuid

# Configurar Logfire SOLO si no está ya configurado
def _configure_logfire_if_needed():
    """Configura Logfire solo si es necesario para evitar logs duplicados"""
    try:
        if hasattr(logfire, '_configured') and getattr(logfire, '_configured', False):
            return
        
        if settings.LOGFIRE_TOKEN:
            logfire.configure(
                token=settings.LOGFIRE_TOKEN,
                send_to_logfire="if-token-present",
                service_name="jira_confluence_agent_ui", 
                service_version="0.1.0"
            )
            # Instrumentación automática avanzada de Logfire
            logfire.instrument_pydantic_ai()
            logfire.instrument_httpx()
            setattr(logfire, '_configured', True)
            
            # Log del sistema: aplicación iniciada
            log_system_event('application_started', 
                           component='streamlit_ui',
                           version='0.1.0')
    except Exception as e:
        # Si hay error configurando logfire, continuar sin él
        log_system_event('logfire_configuration_failed', 
                        severity='warning',
                        error=str(e))

_configure_logfire_if_needed()

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
@log_operation("encrypt_credential")
def _encrypt_key(api_key: str) -> str:
    """Cifra la API key usando el módulo de cifrado real"""
    return credential_encryption.encrypt(api_key)

@log_operation("decrypt_credential")
def _decrypt_key(encrypted_key: str) -> str:
    """Descifra la API key usando el módulo de cifrado real"""
    return credential_encryption.decrypt(encrypted_key)

# --- GESTIÓN DE CREDENCIALES DE ATLASSIAN POR USUARIO (AHORA CON BD) ---
@log_operation("get_user_credentials", log_output=False)  # No loguear credenciales en output
def get_atlassian_credentials_for_user(user_email: str) -> tuple[str, str]:
    """Obtiene las credenciales de Atlassian para un usuario específico desde la BD."""
    if not user_email:
        logger.warning("get_credentials_failed", reason="empty_user_email")
        return "", ""
    
    try:
        api_key, atlassian_username = user_credentials_db.get_credentials(user_email)
        
        # Log del resultado sin exponer credenciales
        if api_key and atlassian_username:
            logger.info("credentials_retrieved_successfully", 
                       has_api_key=bool(api_key),
                       has_username=bool(atlassian_username))
        else:
            logger.info("no_credentials_found", user_email=user_email)
            
        return api_key, atlassian_username
    except Exception as e:
        logger.error("credentials_retrieval_failed", error=e, user_email=user_email)
        return "", ""

@log_operation("save_user_credentials", log_input=False)  # No loguear credenciales en input
def save_atlassian_credentials_for_user(user_email: str, api_key: str, atlassian_username: str):
    """Guarda las credenciales de Atlassian para un usuario específico en la BD."""
    if not user_email:
        logger.error("save_credentials_failed", reason="empty_user_email")
        st.error("No se pueden guardar credenciales sin un email de usuario válido.")
        return

    try:
        if api_key and atlassian_username:
            success = user_credentials_db.save_credentials(user_email, api_key, atlassian_username)
            if success:
                logger.info("credentials_saved_successfully", 
                           operation="save",
                           has_api_key=bool(api_key),
                           has_username=bool(atlassian_username))
                log_user_action("credentials_updated", 
                               credential_type="atlassian")
            else:
                logger.error("credentials_save_failed", reason="database_error")
                st.error("Error al guardar las credenciales en la base de datos.")
        elif user_credentials_db.get_credentials(user_email)[0]:  # Si había credenciales previas
            success = user_credentials_db.delete_credentials(user_email)
            if success:
                logger.info("credentials_deleted_successfully", operation="delete")
                log_user_action("credentials_removed", 
                               credential_type="atlassian")
            else:
                logger.error("credentials_delete_failed", reason="database_error")
                st.error("Error al eliminar las credenciales de la base de datos.")
    except Exception as e:
        logger.error("credentials_operation_failed", error=e, operation="save_or_delete")
        st.error(f"Error al manejar credenciales: {str(e)}")

# --- SISTEMA DE AUTENTICACIÓN ---

def show_auth_selector():
    """
    Muestra la pantalla de selección de método de autenticación.
    Retorna el método seleccionado o None si no se ha seleccionado nada.
    """
    st.markdown("# 🔐 Agente Atlassian")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### Selecciona tu método de autenticación")
        
        st.markdown("---")
        
        # Opción 1: Google OAuth2
        google_button_cols = st.columns([1])
        with google_button_cols[0]:
            if st.button("Inicie sesión con Google", 
                        use_container_width=True, 
                        type="primary",
                        icon=":material/account_circle:",
                        key="auth_google",
                        help="Autenticación con Google OAuth2"):
                return "google_oauth"
        
        st.markdown("")
        
        # Opción 2: Autenticación Local
        if st.button("📧 Inicie sesión con su correo", 
                    use_container_width=True, 
                    type="secondary",
                    key="auth_local"):
            return "local_auth"
        
        st.markdown("---")
        st.caption("🔒 Todos los métodos garantizan la seguridad de tus datos")
    
    return None

def handle_google_oauth_auth():
    """
    Maneja la autenticación con Google OAuth2.
    Retorna True si está autenticado, False si no.
    """
    # Verificar si la autenticación nativa está disponible y configurada
    try:
        # Verificar si el usuario ya está logueado
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            # Usuario autenticado - establecer contexto de logging
            user_email = getattr(st.user, 'email', 'authenticated_user')
            _setup_user_logging_context(user_email)
            log_user_action("authentication_success", 
                           auth_method="google_oauth",
                           user_email=user_email)
            return True
    except (AttributeError, KeyError) as e:
        # La autenticación nativa no está configurada o disponible
        logger.info("oauth_not_configured", 
                   reason="oauth_not_available",
                   error=str(e))
    
    # Mostrar pantalla de login de Google
    st.markdown("# 🌐 Autenticación con Google")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Verificar si OAuth2 está configurado
        try:
            # Intentar verificar si los secrets están disponibles
            if hasattr(st, 'secrets') and 'auth' in st.secrets:
                oauth_configured = True
            else:
                oauth_configured = False
        except:
            oauth_configured = False
        
        if not oauth_configured:
            st.error("❌ **Google OAuth2 no está configurado**")
            st.markdown("""
            **Para configurar Google OAuth2:**
            
            1. 📋 Sigue la guía: `SETUP_OAUTH.md`
            2. 🔑 Configura: `.streamlit/secrets.toml`
            3. ✅ Verifica: `python verify_auth_setup.py`
            4. 🚀 Reinicia la aplicación
            """)
            
            if st.button("⬅️ Volver al selector", key="back_from_google"):
                if 'auth_method' in st.session_state:
                    del st.session_state.auth_method
                st.rerun()
            return False
        
        st.markdown("""
        ### Iniciar Sesión con Google
        
        **Características:**
        - 🤖 Agente inteligente para Jira y Confluence
        - 🧠 Memoria personalizada con tus alias y configuraciones
        - 🔒 Datos seguros y privados por usuario
        - 📊 Historial de conversaciones persistente
        """)
        
        st.markdown("---")
        
        # Botón de login centrado
        col_back, col_login = st.columns([1, 2])
        
        with col_back:
            if st.button("⬅️ Volver", key="back_from_google_login"):
                if 'auth_method' in st.session_state:
                    del st.session_state.auth_method
                st.rerun()
        
        with col_login:
            if st.button("🚀 Iniciar Sesión", 
                        use_container_width=True, 
                        type="primary",
                        key="google_login_btn"):
                try:
                    log_user_action("login_attempt", auth_method="google_oauth")
                    st.login()
                except Exception as e:
                    logger.error("login_failed", error=e, auth_method="google_oauth")
                    st.error(f"Error durante el login: {e}")
                    st.info("💡 **Posibles soluciones:**\n"
                           "- Verifica que hayas configurado correctamente Google OAuth2\n"
                           "- Revisa el archivo `.streamlit/secrets.toml`\n"
                           "- Consulta `SETUP_OAUTH.md` para más detalles")
        
        st.markdown("---")
        st.caption("🔒 Tu privacidad es importante. Solo accedemos a tu email para identificarte.")
    
    return False

def _setup_local_user_session(user_info: dict, session_id: str):
    """Establece la sesión local del usuario en Streamlit."""
    st.session_state.local_user_authenticated = True
    st.session_state.local_user_email = user_info['user_email']
    st.session_state.local_user_display_name = user_info['display_name']
    st.session_state.local_user_is_admin = user_info['is_admin']
    st.session_state.local_user_session_id = session_id
    
    # Establecer contexto de logging
    _setup_user_logging_context(user_info['user_email'])
    
    logger.info("local_user_session_established", 
               user_email=user_info['user_email'],
               display_name=user_info['display_name'],
               is_admin=user_info['is_admin'])

def _clear_local_user_session():
    """Limpia la sesión local del usuario."""
    # Invalidar sesión en la base de datos
    if 'local_user_session_id' in st.session_state:
        from config.user_credentials_db import user_credentials_db
        user_credentials_db.invalidate_user_session(st.session_state.local_user_session_id)
    
    # Limpiar TODO el session_state relacionado con el usuario para evitar fugas de datos entre sesiones.
    # Esto es CRÍTICO para la seguridad.
    keys_to_clear = [
        # Autenticación y sesión
        'auth_method',
        'local_user_authenticated',
        'local_user_email',
        'local_user_display_name',
        'local_user_is_admin',
        'local_user_session_id',
        'user_authenticated', 
        'user_email', 
        'display_name',
        
        # Datos de la aplicación
        'chat_history',
        'pydantic_ai_messages',
        'streamlit_display_messages',
        'memoria_usuario',
        
        # Credenciales sensibles
        'atlassian_api_key',
        'atlassian_username'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    logger.info("local_user_session_cleared_completely")

def _validate_local_user_session() -> bool:
    """Valida la sesión local del usuario."""
    if not st.session_state.get('local_user_authenticated', False):
        return False
    
    session_id = st.session_state.get('local_user_session_id')
    if not session_id:
        return False
    
    from config.user_credentials_db import user_credentials_db
    session_info = user_credentials_db.validate_user_session(session_id)
    
    if session_info:
        # Sesión válida - actualizar información por si cambió
        st.session_state.local_user_email = session_info['user_email']
        st.session_state.local_user_display_name = session_info['display_name']
        st.session_state.local_user_is_admin = session_info['is_admin']
        return True
    else:
        # Sesión inválida - limpiarla
        _clear_local_user_session()
        return False

def handle_local_auth():
    """
    Maneja la autenticación local con base de datos real.
    Retorna True si está autenticado, False si no.
    """
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Verificar si el usuario ya está logueado localmente
        if st.session_state.get('local_user_authenticated', False):
            # Validar que la sesión sigue siendo válida
            if _validate_local_user_session():
                user_email = st.session_state.get('local_user_email', 'usuario_local')
                
                # Log del acceso exitoso y retornar directamente al agente
                log_user_action("authentication_success", 
                               auth_method="local_auth",
                               user_email=user_email)
                return True
            else:
                # Si la sesión no es válida, limpiarla
                _clear_local_user_session()
        
        # Mostrar formulario de login
        st.markdown("### Iniciar Sesión")
        
        # Importar la base de datos
        from config.user_credentials_db import user_credentials_db
        
        # Verificar si hay usuarios locales creados
        local_users = user_credentials_db.list_local_users()
        if not local_users:
            st.warning("⚠️ **No hay usuarios locales configurados**")
            st.info("**Para crear el primer usuario:**\n\n"
                   "1. 🛠️ Ve al **Panel de Administración**\n"
                   "2. 👤 Crea un usuario administrador\n"
                   "3. 🔑 Vuelve aquí para iniciar sesión")
            
            col_back, col_admin = st.columns([1, 1])
            
            with col_back:
                if st.button("⬅️ Volver al selector", key="back_no_users"):
                    if 'auth_method' in st.session_state:
                        del st.session_state.auth_method
                    st.rerun()
            
            with col_admin:
                if st.button("🛠️ Ir a Panel de Admin", key="go_to_admin"):
                    st.session_state.auth_method = "admin_panel"
                    st.rerun()
            
            return False
        
        # Formulario de login local
        with st.form("local_login_form"):
            username = st.text_input("👤 Usuario", placeholder="tu@empresa.com")
            password = st.text_input("🔒 Contraseña", type="password")
            remember_me = st.checkbox("🔄 Recordar sesión por 7 días", value=False)
            
            col_back, col_login = st.columns([1, 2])
            
            with col_back:
                back_clicked = st.form_submit_button("⬅️ Volver")
                
            with col_login:
                login_clicked = st.form_submit_button("🔑 Iniciar Sesión", type="primary")
        
        if back_clicked:
            if 'auth_method' in st.session_state:
                del st.session_state.auth_method
            st.rerun()
        
        if login_clicked:
            if username and password:
                # Intentar autenticar al usuario
                user_info = user_credentials_db.verify_local_user(username, password)
                
                if user_info:
                    # Login exitoso
                    st.success("✅ **Login exitoso**")
                    
                    # Crear sesión
                    session_hours = 168 if remember_me else 24  # 7 días o 24 horas
                    session_id = user_credentials_db.create_user_session(
                        user_email=user_info['user_email'],
                        expires_in_hours=session_hours,
                        ip_address="127.0.0.1",  # En producción usar st.get_ip() si está disponible
                        user_agent="Streamlit App"
                    )
                    
                    if session_id:
                        # Establecer sesión en Streamlit
                        _setup_local_user_session(user_info, session_id)
                        
                        log_user_action("login_success", 
                                       auth_method="local_auth",
                                       user_email=user_info['user_email'],
                                       session_duration_hours=session_hours)
                        
                        st.rerun()  # Recargar para mostrar la pantalla de usuario logueado
                    else:
                        st.error("❌ Error creando sesión. Intenta nuevamente.")
                        log_user_action("session_creation_failed", 
                                       auth_method="local_auth",
                                       user_email=user_info['user_email'])
                else:
                    # Login fallido
                    st.error("❌ **Credenciales incorrectas**")
                    st.warning("⚠️ Verifica tu email y contraseña.\n\n"
                              "Si has olvidado tu contraseña, contacta al administrador.")
                    
                    log_user_action("login_failed", 
                                   auth_method="local_auth",
                                   username=username,
                                   reason="invalid_credentials")
            else:
                st.error("⚠️ Por favor, completa todos los campos")
        
        # Información sobre usuarios disponibles (solo emails, sin mostrar passwords)
        if local_users:
            with st.expander("ℹ️ Usuarios disponibles", expanded=False):
                active_users = [u for u in local_users if u['is_active']]
                if active_users:
                    st.markdown("**Usuarios activos:**")
                    for user in active_users:
                        status = "👑 Admin" if user['is_admin'] else "👤 Usuario"
                        last_login = user['last_login'] or "Nunca"
                        st.markdown(f"- **{user['user_email']}** ({status}) - Último acceso: {last_login}")
                else:
                    st.warning("No hay usuarios activos")
        
        st.markdown("---")
        st.caption("🔒 Las contraseñas se almacenan de forma segura con hash y salt")
    
    return False

def _validate_admin_access():
    """Verifica si el usuario actual tiene permisos de administrador."""
    # Si es usuario local, verificar si es admin
    if st.session_state.get('local_user_authenticated', False):
        return st.session_state.get('local_user_is_admin', False)
    
    # Para usuarios OAuth2, por ahora permitir acceso (se puede restringir después)
    try:
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            return True  # Todos los usuarios OAuth2 son admin por defecto
    except (AttributeError, KeyError):
        pass
    
    # Para usuario demo, no permitir acceso a admin
    return False

def _create_user_tab():
    """Tab para crear nuevos usuarios."""
    st.markdown("### 👤 Crear Nuevo Usuario")
    
    from config.user_credentials_db import user_credentials_db
    
    with st.form("create_user_form"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            new_email = st.text_input("📧 Email del usuario", placeholder="usuario@empresa.com")
            new_password = st.text_input("🔒 Contraseña", type="password", placeholder="Mínimo 8 caracteres")
        
        with col2:
            new_display_name = st.text_input("👤 Nombre completo", placeholder="Juan Pérez")
            is_admin = st.checkbox("⚙️ Permisos de administrador", value=False)
        
        # Columnas para alinear botones: Espaciador, Cancelar, Crear
        st.markdown("---") # Separador visual
        col_spacer, col_cancel, col_create = st.columns([3, 1, 1])
        
        with col_cancel:
            cancel_clicked = st.form_submit_button("❌ Cancelar", use_container_width=True)
        
        with col_create:
            create_clicked = st.form_submit_button("✅ Crear Usuario", type="primary", use_container_width=True)
    
    if cancel_clicked:
        st.rerun()
    
    if create_clicked:
        if new_email and new_password and new_display_name:
            # Validaciones básicas
            if len(new_password) < 8:
                st.error("❌ La contraseña debe tener al menos 8 caracteres")
            elif not "@" in new_email:
                st.error("❌ Email inválido")
            elif user_credentials_db.local_user_exists(new_email):
                st.error("❌ Ya existe un usuario con ese email")
            else:
                # Crear usuario
                result = user_credentials_db.create_local_user(
                    user_email=new_email,
                    display_name=new_display_name,
                    password=new_password,
                    is_admin=is_admin
                )
                
                if result:
                    st.success(f"✅ Usuario creado exitosamente: {new_display_name}")
                    log_user_action("user_created", 
                                   admin_action=True,
                                   target_user=new_email,
                                   is_admin=is_admin)
                    st.rerun()
                else:
                    st.error("❌ Error creando usuario. Verifica los datos.")
        else:
            st.error("⚠️ Por favor completa todos los campos")

def _manage_users_tab():
    """Tab para gestionar usuarios existentes."""
    st.markdown("### 👥 Gestionar Usuarios")
    
    from config.user_credentials_db import user_credentials_db
    
    # Listar usuarios
    users = user_credentials_db.list_local_users()
    
    if not users:
        st.info("ℹ️ No hay usuarios locales creados.")
        return
    
    st.markdown(f"**Total de usuarios:** {len(users)}")
    
    # Tabla de usuarios
    for i, user in enumerate(users):
        with st.expander(f"👤 {user['display_name']} ({user['user_email']})", expanded=False):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**Email:** {user['user_email']}")
                st.markdown(f"**Nombre:** {user['display_name']}")
                st.markdown(f"**Estado:** {'✅ Activo' if user['is_active'] else '❌ Inactivo'}")
                st.markdown(f"**Admin:** {'👑 Sí' if user['is_admin'] else '👤 No'}")
                st.markdown(f"**Creado:** {user['created_at']}")
                st.markdown(f"**Último acceso:** {user['last_login'] or 'Nunca'}")
                if user['failed_login_attempts'] > 0:
                    st.markdown(f"**Intentos fallidos:** {user['failed_login_attempts']}")
            
            with col2:
                # Cambiar estado
                current_status = user['is_active']
                new_status = st.toggle(
                    f"Activo", 
                    value=current_status,
                    key=f"toggle_status_{user['user_email']}"
                )
                
                if new_status != current_status:
                    result = user_credentials_db.toggle_local_user_status(
                        user['user_email'], 
                        new_status
                    )
                    if result:
                        status_text = "activado" if new_status else "desactivado"
                        st.success(f"Usuario {status_text}")
                        log_user_action("user_status_changed", 
                                       admin_action=True,
                                       target_user=user['user_email'],
                                       new_status=status_text)
                        st.rerun()
                    else:
                        st.error("Error cambiando estado")
            
            with col3:
                # Acciones
                if st.button("🔒 Resetear Password", key=f"reset_pwd_{user['user_email']}"):
                    st.session_state[f'reset_password_for'] = user['user_email']
                    st.rerun()
                
                if st.button("🗑️ Eliminar", key=f"delete_{user['user_email']}", type="secondary"):
                    st.session_state[f'delete_user'] = user['user_email']
                    st.rerun()
    
    # Manejar reset de contraseña
    if 'reset_password_for' in st.session_state:
        user_email = st.session_state['reset_password_for']
        st.markdown("---")
        st.markdown(f"### 🔒 Resetear contraseña para: {user_email}")
        
        with st.form(f"reset_password_form"):
            new_password = st.text_input("Nueva contraseña", type="password", placeholder="Mínimo 8 caracteres")
            confirm_password = st.text_input("Confirmar contraseña", type="password")
            
            col_cancel, col_reset = st.columns([1, 1])
            
            with col_cancel:
                if st.form_submit_button("Cancelar"):
                    del st.session_state['reset_password_for']
                    st.rerun()
            
            with col_reset:
                if st.form_submit_button("🔒 Resetear", type="primary"):
                    if new_password and confirm_password:
                        if new_password == confirm_password:
                            if len(new_password) >= 8:
                                result = user_credentials_db.update_local_user_password(
                                    user_email, new_password
                                )
                                if result:
                                    st.success("✅ Contraseña reseteada exitosamente")
                                    log_user_action("password_reset", 
                                                   admin_action=True,
                                                   target_user=user_email)
                                    del st.session_state['reset_password_for']
                                    st.rerun()
                                else:
                                    st.error("❌ Error reseteando contraseña")
                            else:
                                st.error("❌ La contraseña debe tener al menos 8 caracteres")
                        else:
                            st.error("❌ Las contraseñas no coinciden")
                    else:
                        st.error("⚠️ Completa ambos campos")
    
    # Manejar eliminación de usuario
    if 'delete_user' in st.session_state:
        user_email = st.session_state['delete_user']
        st.markdown("---")
        st.error(f"### ⚠️ ¿Eliminar usuario: {user_email}?")
        st.warning("Esta acción no se puede deshacer. Se eliminarán todas las sesiones del usuario.")
        
        col_cancel, col_delete = st.columns([1, 1])
        
        with col_cancel:
            if st.button("Cancelar eliminación", key="cancel_delete"):
                del st.session_state['delete_user']
                st.rerun()
        
        with col_delete:
            if st.button("🗑️ ELIMINAR", key="confirm_delete", type="primary"):
                result = user_credentials_db.delete_local_user(user_email)
                if result:
                    st.success(f"✅ Usuario {user_email} eliminado")
                    log_user_action("user_deleted", 
                                   admin_action=True,
                                   target_user=user_email)
                    del st.session_state['delete_user']
                    st.rerun()
                else:
                    st.error("❌ Error eliminando usuario")

def _statistics_tab():
    """Tab para ver estadísticas del sistema."""
    st.markdown("### 📊 Estadísticas del Sistema")
    
    from config.user_credentials_db import user_credentials_db
    
    # Estadísticas de usuarios
    users = user_credentials_db.list_local_users()
    active_users = [u for u in users if u['is_active']]
    admin_users = [u for u in users if u['is_admin']]
    users_with_login = [u for u in users if u['last_login']]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Total Usuarios", len(users))
    
    with col2:
        st.metric("✅ Usuarios Activos", len(active_users))
    
    with col3:
        st.metric("👑 Administradores", len(admin_users))
    
    with col4:
        st.metric("🔐 Con Login", len(users_with_login))
    
    # Gráfico de usuarios por estado
    if users:
        st.markdown("#### Estados de Usuario")
        active_count = len(active_users)
        inactive_count = len(users) - active_count
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"**Activos:** {active_count}")
            st.markdown(f"**Inactivos:** {inactive_count}")
        
        with col2:
            # Datos para gráfico simple con barras de progreso
            if active_count > 0:
                st.progress(active_count / len(users), text=f"Usuarios Activos: {active_count}")
            if admin_users:
                st.progress(len(admin_users) / len(users), text=f"Administradores: {len(admin_users)}")
    
    # Estadísticas de credenciales Atlassian
    st.markdown("---")
    st.markdown("#### 🔗 Credenciales Atlassian")
    
    atlassian_users = user_credentials_db.list_users()
    st.metric("🔑 Usuarios con credenciales Atlassian", len(atlassian_users))
    
    if atlassian_users:
        st.markdown("**Usuarios con acceso a Atlassian:**")
        for user_email, atlassian_username, updated_at in atlassian_users:
            st.markdown(f"- **{user_email}** → {atlassian_username} (actualizado: {updated_at})")

def _logs_tab():
    """Tab para ver logs del sistema."""
    st.markdown("### 📋 Logs del Sistema")
    
    st.info("ℹ️ Los logs completos están disponibles en el dashboard de **Logfire**")
    st.markdown("🔗 **Dashboard de Logfire**: https://logfire-us.pydantic.dev/")
    
    # Simulación de logs recientes (en producción, esto vendría de Logfire API)
    st.markdown("#### 🕐 Actividad Reciente")
    
    sample_logs = [
        {"timestamp": "2024-01-15 10:30:15", "action": "login_success", "user": "admin@empresa.com", "method": "local_auth"},
        {"timestamp": "2024-01-15 10:25:42", "action": "user_created", "user": "admin@empresa.com", "target": "nuevo@empresa.com"},
        {"timestamp": "2024-01-15 10:20:18", "action": "authentication_success", "user": "usuario@empresa.com", "method": "local_auth"},
        {"timestamp": "2024-01-15 10:15:33", "action": "login_failed", "user": "test@empresa.com", "reason": "invalid_credentials"},
        {"timestamp": "2024-01-15 10:10:07", "action": "admin_panel_access", "user": "admin@empresa.com", "status": "authorized"},
    ]
    
    for log in sample_logs:
        with st.expander(f"📋 {log['timestamp']} - {log['action']}", expanded=False):
            st.json(log)
    
    st.markdown("#### 📊 Métricas de Logging")
    st.markdown("""
    **Eventos monitoreados:**
    - ✅ `login_success` / `login_failed` - Intentos de autenticación
    - 👤 `user_created` / `user_deleted` - Gestión de usuarios
    - 🔒 `password_reset` - Cambios de contraseña
    - 📊 `admin_panel_access` - Accesos al panel de admin
    - 🎫 `session_created` / `session_invalidated` - Gestión de sesiones
    - 📈 `user_action` - Acciones generales del usuario
    """)

def _system_tab():
    """Tab para configuración del sistema."""
    st.markdown("### ⚙️ Configuración del Sistema")
    
    from config.user_credentials_db import user_credentials_db
    from pathlib import Path
    
    # Información del sistema
    st.markdown("#### 💾 Base de Datos")
    
    db_path = Path(".streamlit/user_credentials.db")
    if db_path.exists():
        db_size = db_path.stat().st_size
        st.success(f"✅ Base de datos activa: {db_size} bytes")
    else:
        st.error("❌ Base de datos no encontrada")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Verificar Conexión BD"):
            try:
                # Test simple de conexión
                users = user_credentials_db.list_local_users()
                st.success(f"✅ Conexión exitosa. {len(users)} usuarios encontrados.")
            except Exception as e:
                st.error(f"❌ Error de conexión: {e}")
    
    with col2:
        if st.button("📊 Estadísticas BD"):
            try:
                users = user_credentials_db.list_local_users()
                atlassian_users = user_credentials_db.list_users()
                
                st.info(f"""
                **Estadísticas de la Base de Datos:**
                - 👥 Usuarios locales: {len(users)}
                - 🔗 Credenciales Atlassian: {len(atlassian_users)}
                - 📊 Tablas: 3 (user_credentials, local_users, local_user_sessions)
                """)
            except Exception as e:
                st.error(f"❌ Error obteniendo estadísticas: {e}")
    
    # Políticas de seguridad
    st.markdown("---")
    st.markdown("#### 🛡️ Políticas de Seguridad")
    
    st.markdown("""
    **Configuración actual:**
    - 🔒 **Hashing**: bcrypt con salt único
    - 🎫 **Sesiones**: 24 horas (standard), 7 días (recordar)
    - 🚫 **Bloqueo**: 5 intentos fallidos
    - 🔐 **Contraseñas**: Mínimo 8 caracteres
    - 📊 **Logging**: Todos los eventos registrados
    """)
    
    # Acciones administrativas
    st.markdown("---")
    st.markdown("#### 🚨 Acciones Administrativas")
    
    st.warning("⚠️ **Acciones peligrosas - Usar con precaución**")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🧹 Limpiar Sesiones Expiradas", type="secondary"):
            # En una implementación real, esto limpiaría sesiones expiradas
            st.info("🧹 Funcionalidad de limpieza ejecutada (simulada)")
            log_user_action("cleanup_expired_sessions", admin_action=True)
    
    with col2:
        if st.button("📋 Exportar Logs de Usuario", type="secondary"):
            st.info("📋 Exportación de logs disponible en el dashboard de Logfire")
            log_user_action("export_logs_requested", admin_action=True)

def handle_admin_panel():
    """
    Maneja el panel de administración completo.
    Retorna True si se debe continuar, False si no.
    """
    st.markdown("# ⚙️ Panel de Administración")
    st.markdown("---")
    
    # Verificar permisos de administrador
    if not _validate_admin_access():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.error("🚫 **Acceso Denegado**")
            st.warning("Solo los administradores pueden acceder a este panel.")
            
            if st.button("⬅️ Volver al selector", key="access_denied_back"):
                if 'auth_method' in st.session_state:
                    del st.session_state.auth_method
                st.rerun()
            
            log_user_action("admin_panel_access_denied", 
                           admin_action=False,
                           reason="insufficient_permissions")
        return False
    
    # Panel de administración para usuarios autorizados
    st.success(f"👑 **Bienvenido al Panel de Administración**")
    
    # Tabs del panel de administración
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Crear Usuario", 
        "👥 Gestionar Usuarios", 
        "📊 Estadísticas",
        "📋 Logs",
        "⚙️ Sistema"
    ])
    
    with tab1:
        _create_user_tab()
    
    with tab2:
        _manage_users_tab()
    
    with tab3:
        _statistics_tab()
    
    with tab4:
        _logs_tab()
    
    with tab5:
        _system_tab()
    
    # Botón para volver al selector

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⬅️ Volver", key="admin_back_to_app"):
            # En lugar de borrar el método de auth, lo establecemos a 'local_auth'
            # para que la app principal se renderice.
            st.session_state.auth_method = "local_auth"
            log_user_action("admin_panel_exit", admin_action=True)
            st.rerun()
    
    log_user_action("admin_panel_access", 
                   admin_action=True,
                   status="authorized")
    
    return False  # Nunca continúa a la aplicación principal

def check_authentication():
    """
    Función principal de autenticación que maneja el flujo completo.
    Retorna True si el usuario está autenticado, False si no.
    """
    # Verificar si ya tenemos un método de autenticación seleccionado
    if 'auth_method' not in st.session_state:
        # Mostrar selector de método de autenticación
        selected_method = show_auth_selector()
        
        if selected_method:
            st.session_state.auth_method = selected_method
            st.rerun()  # Recargar para mostrar el método seleccionado
        
        return False  # No autenticado aún
    
    # Manejar el método seleccionado
    auth_method = st.session_state.auth_method
    
    if auth_method == "google_oauth":
        return handle_google_oauth_auth()
    elif auth_method == "local_auth":
        return handle_local_auth()
    elif auth_method == "admin_panel":
        # El panel de admin maneja su propia autenticación
        return handle_admin_panel()
    else:
        # Método desconocido, volver al selector
        del st.session_state.auth_method
        st.rerun()
        return False

def _setup_user_logging_context(user_email: str):
    """Establece el contexto de logging para el usuario actual."""
    # Establecer el contexto de usuario para toda la sesión
    if 'user_logging_context' not in st.session_state:
        st.session_state.user_logging_context = UserLoggingContext(user_email)
        st.session_state.user_logging_context.__enter__()
        
        logger.info("user_session_started", 
                   session_id=st.session_state.user_logging_context.session_id,
                   correlation_id=st.session_state.user_logging_context.correlation_id)

# Verificar autenticación antes de mostrar la app
if not check_authentication():
    st.stop()  # Detener ejecución si no está autenticado

# Usuario autenticado - continuar con la aplicación
def get_user_info():
    """Obtiene información del usuario de forma segura."""
    # Prioridad 1: Usuario local autenticado
    if st.session_state.get('local_user_authenticated', False):
        email = st.session_state.get('local_user_email', 'usuario_local')
        name = st.session_state.get('local_user_display_name', email)
        return email, name
    
    # Prioridad 2: Usuario OAuth2 (Google)
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

# ===== DETECCIÓN DE CAMBIO DE USUARIO - LIMPIAR CHAT =====
# Verificar si cambió el usuario para limpiar el chat
last_user = st.session_state.get('last_logged_user', None)
if last_user and last_user != current_user:
    # Usuario diferente detectado - limpiar chat y contexto
    chat_keys_to_clear = [
        'chat_history', 
        'pydantic_ai_messages', 
        'streamlit_display_messages',
        'memoria_usuario'  # También limpiar memoria para nuevo usuario
    ]
    for key in chat_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Log del cambio de usuario
    log_user_action("user_switched", 
                   previous_user=last_user,
                   new_user=current_user)

# Actualizar el último usuario logueado
st.session_state['last_logged_user'] = current_user

# Log del inicio de sesión de usuario
log_user_action("session_loaded", 
               user_name=user_name,
               user_email=current_user)

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

# Mostrar botón de Panel de Admin si el usuario es administrador
def _check_if_current_user_is_admin():
    """Verifica si el usuario actual tiene permisos de administrador."""
    # Usuario local autenticado
    if st.session_state.get('local_user_authenticated', False):
        return st.session_state.get('local_user_is_admin', False)
    
    # Usuario OAuth2 - por ahora todos son admin por defecto
    try:
        if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
            return True  # Todos los usuarios OAuth2 son admin por defecto
    except (AttributeError, KeyError):
        pass
    
    return False

# ===== ÁREA PRINCIPAL DEL CHAT =====

def create_styled_container(container_id: str, css_styles: str):
    """Crea un contenedor con ID único usando el método robusto de la comunidad Streamlit"""
    plh = st.container()
    html_code = f"""<div id='marker_outer_{container_id}'></div>"""
    st.markdown(html_code, unsafe_allow_html=True)
    
    with plh:
        inner_html_code = f"""<div id='marker_inner_{container_id}'></div>"""
        plh.markdown(inner_html_code, unsafe_allow_html=True)
    
    style = f"""
    <style>
        div[data-testid='stVerticalBlock']:has(div#marker_inner_{container_id}):not(:has(div#marker_outer_{container_id})) {{
            {css_styles}
        }}
    </style>
    """
    st.markdown(style, unsafe_allow_html=True)
    return plh

# ===== CSS ROBUSTO BASADO EN INVESTIGACIÓN =====
st.markdown("""
<style>
    /* ===== ESTILOS PARA ÁREA PRINCIPAL (MÉTODOS ROBUSTOS) ===== */
    
    /* Título principal elegante - MÉTODO DIRECTO SIN VARIABLES CSS */
    .main-title {
        text-align: center;
        background: linear-gradient(135deg, #4a9eff, #00d084);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 2rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Container de chat minimalista - DISEÑO LIMPIO */
    div[data-testid="stChatFloatingInputContainer"] {
        background: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        backdrop-filter: none !important;
    }
    
    /* Input de chat limpio */
    div[data-testid="stChatInput"] input {
        background: transparent !important;
        border: none !important;
        color: #ffffff !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        padding: 14px 16px !important;
    }
    
    div[data-testid="stChatInput"] input::placeholder {
        color: #9ca3af !important;
        font-style: normal !important;
    }
    
    /* Botón de envío empresarial */
    div[data-testid="stChatInput"] button {
        background: #4a9eff !important;
        border: none !important;
        border-radius: 6px !important;
        color: white !important;
        transition: background-color 0.2s ease !important;
    }
    
    div[data-testid="stChatInput"] button:hover {
        background: #3d8bfd !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Mensajes de chat minimalistas */
    div[data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        margin-bottom: 16px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding-bottom: 16px !important;
        backdrop-filter: none !important;
        transition: none !important;
    }
    
    div[data-testid="stChatMessage"]:hover {
        background: transparent !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Avatar de usuario */
    div[data-testid="stChatMessage"] img[alt="👤"] {
        border-radius: 50% !important;
        box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3) !important;
    }
    
    /* Avatar de asistente */
    div[data-testid="stChatMessage"] img[alt="🤖"] {
        border-radius: 50% !important;
        box-shadow: 0 2px 8px rgba(0, 208, 132, 0.3) !important;
    }
    
    /* Container de chat minimalista */
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        backdrop-filter: none !important;
    }
    
    /* Scrollbar para el chat */
    div[data-testid="stVerticalBlock"]::-webkit-scrollbar {
        width: 6px;
    }
    
    div[data-testid="stVerticalBlock"]::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 3px;
    }
    
    div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #4a9eff, #00d084);
        border-radius: 3px;
    }
    
    div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #3d8bfd, #00c077);
    }
</style>
""", unsafe_allow_html=True)

# Título principal con estilo - SOLO UNO, SIN DUPLICADOS
st.markdown('<h1 class="main-title">🤖 Agente Atlassian</h1>', unsafe_allow_html=True)

# Container para mensajes con diseño moderno
chat_height = 650
chat_container = st.container(height=chat_height, border=False)
with chat_container:
    if not st.session_state.chat_history:
        # Placeholder elegante cuando no hay mensajes
        st.markdown("""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; padding: 2rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.7;">🤖</div>
            <h3 style="color: #b3b3b3; font-weight: 500; margin-bottom: 0.5rem;">¡Hola! Soy tu Agente Atlassian</h3>
            <p style="color: #808080; font-size: 14px; max-width: 400px; line-height: 1.5;">
                Puedo ayudarte con Jira, Confluence y cualquier consulta que necesites. 
                ¡Escribe tu pregunta abajo para comenzar!
            </p>
            <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 8px; max-width: 500px;">
                <p style="color: #4a9eff; font-size: 12px; margin: 0;">
                    💡 <strong>Consejo:</strong> Para consultas de Atlassian, asegúrate de configurar tus credenciales en la barra lateral.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(message["content"])
            elif message["role"] == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message["content"])

# Chat input siempre visible en la parte inferior
if prompt := st.chat_input("💬 Escribe tu consulta aquí...", key="main_chat"):
    # Log de la acción del usuario
    log_user_action("user_query_submitted", 
                   query_length=len(prompt),
                   has_context=bool(generar_contexto_completo()),
                   query_preview=prompt[:100])  # Solo primeros 100 chars por privacidad
    
    # Agregar mensaje del usuario al historial
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    
    # --- VERIFICACIÓN DE CREDENCIALES ATLASSIAN ANTES DE LLAMAR AL AGENTE ---
    is_atlassian_related_query = any(kw in prompt.lower() for kw in ["atlassian", "jira", "confluence", "issue", "ticket", "página", "espacio"])
    
    # Log del análisis de la consulta
    logger.info("query_analysis", 
               is_atlassian_related=is_atlassian_related_query,
               has_atlassian_credentials=bool(st.session_state.get("atlassian_api_key") and st.session_state.get("atlassian_username")),
               query_keywords=[kw for kw in ["atlassian", "jira", "confluence", "issue", "ticket", "página", "espacio"] if kw in prompt.lower()])
    
    if is_atlassian_related_query and not (st.session_state.get("atlassian_api_key") and st.session_state.get("atlassian_username")):
        # Log de bloqueo por credenciales faltantes
        logger.warning("query_blocked_missing_credentials", 
                      query_type="atlassian_related",
                      reason="missing_credentials")
        log_user_action("credentials_required_warning", 
                       query_type="atlassian")
        
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
    
    # Log del contexto generado
    logger.info("context_preparation", 
               has_context=bool(contexto_completo),
               context_length=len(contexto_completo) if contexto_completo else 0,
               final_prompt_length=len(prompt_con_contexto))
    
    # Procesar respuesta del agente
    agent_start_time = time.time()
    operation_id = str(uuid.uuid4())[:8]
    
    try:
        # Log del inicio del procesamiento del agente
        logger.info("agent_processing_started", 
                   operation_id=operation_id,
                   agent_type="pydantic_ai",
                   framework="streamlit")
        
        # Paso 1: Iniciar
        start_agent_process("Procesando tu consulta...")
        with status_placeholder:
            render_current_status(status_display)
        
        # Paso 2: Construir contexto
        track_context_building()
        with status_placeholder:
            render_current_status(status_display)
        
        with logfire.span("agent_interaction_streamlit", 
                         user_prompt=prompt, 
                         framework="streamlit",
                         operation_id=operation_id,
                         has_context=bool(contexto_completo)):
            # Paso 3: Analizar consulta
            track_llm_thinking()
            with status_placeholder:
                render_current_status(status_display)
            
            # Paso 4: Generar respuesta
            track_response_generation()
            with status_placeholder:
                render_current_status(status_display)
            
            # Ejecutar el agente
            logger.info("agent_execution_starting", 
                       operation_id=operation_id,
                       execution_method="asyncio")
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(simple_agent.run(
                prompt_con_contexto,
                message_history=st.session_state.pydantic_ai_messages
            ))
            loop.close()
            
            # Actualizar historial con los nuevos mensajes del agente
            st.session_state.pydantic_ai_messages.extend(result.new_messages())
        
        # Calcular duración total
        agent_duration_ms = (time.time() - agent_start_time) * 1000
        
        # Reemplazar el estado con la respuesta final
        if result.output:
            # Log de respuesta exitosa
            logger.info("agent_response_generated", 
                       operation_id=operation_id,
                       response_length=len(result.output),
                       duration_ms=round(agent_duration_ms, 2),
                       has_output=True,
                       model_usage=str(result.usage()) if hasattr(result, 'usage') else None)
            
            log_user_action("response_received", 
                           response_length=len(result.output),
                           duration_ms=round(agent_duration_ms, 2),
                           success=True)
            
            with status_placeholder:
                st.markdown(result.output)
            st.session_state.chat_history.append({"role": "assistant", "content": result.output})
        else:
            # Log de respuesta vacía
            logger.warning("agent_response_empty", 
                          operation_id=operation_id,
                          duration_ms=round(agent_duration_ms, 2),
                          has_output=False)
            
            log_user_action("response_received", 
                           response_length=0,
                           duration_ms=round(agent_duration_ms, 2),
                           success=False,
                           issue="empty_response")
            
            error_msg = "⚠️ El agente no produjo una respuesta. Intenta reformular tu pregunta."
            with status_placeholder:
                st.markdown(error_msg)
            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
    except Exception as e:
        # Calcular duración hasta el fallo
        agent_duration_ms = (time.time() - agent_start_time) * 1000
        
        # Log de error detallado
        logger.error("agent_processing_failed", 
                    error=e,
                    operation_id=operation_id,
                    duration_ms=round(agent_duration_ms, 2),
                    error_type=type(e).__name__,
                    query_preview=prompt[:100])
        
        log_user_action("response_received", 
                       duration_ms=round(agent_duration_ms, 2),
                       success=False,
                       error_type=type(e).__name__,
                       issue="processing_error")
        
        error_message = f"❌ **Error:** {str(e)}\n\n💡 **Sugerencias:**\n- Verifica que el modelo esté funcionando correctamente\n- Intenta simplificar tu consulta\n- Revisa la configuración del contexto de memoria"
        with status_placeholder:
            st.markdown(error_message)
        st.session_state.chat_history.append({"role": "assistant", "content": error_message})
    
    st.rerun()

# --- SIDEBAR ---
# ========== DISEÑO UX/UI PROFESIONAL CON MÉTODOS ROBUSTOS ==========
with st.sidebar:
    st.markdown("""
    <style>
        /* ===== SISTEMA DE DISEÑO ROBUSTO SIN VARIABLES CSS ===== */
        
        /* Reset y base para sidebar - VALORES DIRECTOS */
        div[data-testid="stSidebar"] {
            background: #1e1e1e !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }
        
        /* ===== SECCIÓN USUARIO MINIMALISTA ===== */
        .user-card {
            background: transparent;
            border: none;
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 0;
            padding: 0 0 16px 0;
            margin-bottom: 24px;
            backdrop-filter: none;
            transition: none;
        }
        
        .user-card:hover {
            background: transparent;
            border-color: rgba(255, 255, 255, 0.15);
        }
        
        .user-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 4px;
        }
        
        .user-info {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
        }
        
        .user-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4a9eff, #00d084);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            color: white;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(74, 158, 255, 0.3);
        }
        
        .user-name {
            font-size: 13px;
            font-weight: 500;
            color: #ffffff;
            line-height: 1.2;
        }
        
        .user-date {
            font-size: 12px;
            color: #9ca3af;
            text-align: right;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        /* ===== BOTONES SISTEMA ===== */
        .action-buttons {
            display: flex;
            gap: 4px;
            margin-top: 8px;
        }
        
        /* Botones principales */
        div[data-testid="stSidebar"] button[kind="primary"] {
            background: linear-gradient(135deg, #4a9eff, #3d8bfd) !important;
            border: none !important;
            border-radius: 6px !important;
            color: white !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            height: 32px !important;
            padding: 0 12px !important;
            transition: all 0.15s ease !important;
            box-shadow: 0 2px 4px rgba(74, 158, 255, 0.3) !important;
        }
        
        div[data-testid="stSidebar"] button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 8px rgba(74, 158, 255, 0.4) !important;
        }
        
        /* Botones secundarios */
        div[data-testid="stSidebar"] button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 6px !important;
            color: #b3b3b3 !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            height: 32px !important;
            padding: 0 12px !important;
            transition: all 0.15s ease !important;
        }
        
        div[data-testid="stSidebar"] button[kind="secondary"]:hover {
            background: rgba(255, 255, 255, 0.12) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
        }
        

        

        
        /* ===== SECCIONES SIN TÍTULOS - ULTRA MINIMALISTA ===== */
        .content-section {
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 0;
            margin-bottom: 24px;
        }
        
        /* ===== TOGGLE Y CONTROLES ===== */
        div[data-testid="stSidebar"] .stToggle {
            margin-bottom: 8px !important;
        }
        
        div[data-testid="stSidebar"] .stToggle label {
            font-size: 11px !important;
            color: #b3b3b3 !important;
            font-weight: 500 !important;
        }
        
        /* ===== POPOVER MODERNA ===== */
        div[data-testid="stSidebar"] .stPopover button {
            background: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 6px !important;
            color: #b3b3b3 !important;
            font-size: 10px !important;
            height: 28px !important;
            transition: all 0.15s ease !important;
        }
        
        div[data-testid="stSidebar"] .stPopover button:hover {
            background: rgba(255, 255, 255, 0.12) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
        }
        
        /* ===== ESTADOS Y ALERTAS ===== */
        div[data-testid="stSidebar"] .stSuccess {
            background: rgba(0, 208, 132, 0.1) !important;
            border: 1px solid rgba(0, 208, 132, 0.3) !important;
            border-radius: 6px !important;
            color: #00d084 !important;
            font-size: 10px !important;
            padding: 4px 8px !important;
        }
        
        div[data-testid="stSidebar"] .stError {
            background: rgba(255, 107, 53, 0.1) !important;
            border: 1px solid rgba(255, 107, 53, 0.3) !important;
            border-radius: 6px !important;
            color: #ff6b35 !important;
            font-size: 10px !important;
            padding: 4px 8px !important;
        }
        
        /* ===== INPUTS MODERNOS ===== */
        div[data-testid="stSidebar"] .stTextInput input {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 6px !important;
            color: #ffffff !important;
            font-size: 10px !important;
            height: 32px !important;
            padding: 0 8px !important;
        }
        
        div[data-testid="stSidebar"] .stTextInput input:focus {
            border-color: #4a9eff !important;
            box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2) !important;
        }
        
        div[data-testid="stSidebar"] .stTextInput label {
            font-size: 10px !important;
            color: #b3b3b3 !important;
            font-weight: 500 !important;
        }
        
        /* ===== SEPARADORES ELEGANTES ===== */
        div[data-testid="stSidebar"] hr {
            border: none !important;
            height: 1px !important;
            background: rgba(255, 255, 255, 0.12) !important;
            margin: 12px 0 !important;
        }
        
        /* ===== SCROLLBAR PERSONALIZADA ===== */
        div[data-testid="stSidebar"] ::-webkit-scrollbar {
            width: 4px;
        }
        
        div[data-testid="stSidebar"] ::-webkit-scrollbar-track {
            background: transparent;
        }
        
        div[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 2px;
        }
        
        div[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        /* ===== ANIMACIONES SUTILES ===== */
        div[data-testid="stSidebar"] * {
            transition: all 0.15s ease;
        }
        
        /* ===== RESPONSIVE ===== */
        @media (max-height: 800px) {
            .content-section {
                padding: 8px;
                margin-bottom: 8px;
            }
        }
    </style>
    """, unsafe_allow_html=True)
    
    # ===== TARJETA DE USUARIO SIMPLE =====
    fecha_actual = datetime.now().strftime("%d/%m/%Y") # Formato con año
    user_initials = ''.join([name[0].upper() for name in user_name.split()[:2]])
    user_display_name = user_name if len(user_name) <= 16 else user_name[:13] + "..."
    
    # Verificar si hay sesión activa
    is_logged_in = st.session_state.get('local_user_authenticated', False)
    
    # Usar columnas para alinear el nombre y el botón de logout
    col1, col2 = st.columns([0.85, 0.15])

    with col1:
        st.markdown(f"""
        <div class="user-card">
            <div class="user-header">
                <div class="user-info">
                    <div class="user-avatar">{user_initials}</div>
                    <div class="user-name">{user_display_name}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if is_logged_in:
            if st.button("🚪", key="logout_btn", help="Cerrar sesión"):
                user_email = st.session_state.get('local_user_email', 'usuario_local')
                _clear_local_user_session()
                log_user_action("logout_success", 
                               auth_method="local_auth",
                               user_email=user_email)
                
                # Simplemente recargamos la app, el estado de sesión ya está limpio.
                st.rerun()
    
    # ===== SECCIÓN ADMIN =====
    user_is_admin = _check_if_current_user_is_admin()
    if user_is_admin:
        st.markdown('<div style="height: 1px; background: rgba(255, 255, 255, 0.1); margin: 16px 0;"></div>', unsafe_allow_html=True)
        if st.button("🛠️ Panel de Admin", 
                            use_container_width=True, 
                            type="primary",
                            key="admin_panel_access"):
            st.session_state.auth_method = "admin_panel"
            st.rerun()

    # ===== SECCIÓN MEMORIA & CONTEXTO =====
    st.markdown('<div style="height: 1px; background: rgba(255, 255, 255, 0.1); margin: 16px 0;"></div>', unsafe_allow_html=True)
    memoria_usuario = st.session_state.get("memoria_usuario", {})
    cantidad_alias = len(memoria_usuario)
    
    # Toggle para contexto
    contexto_activo = st.toggle(
        "Usar contexto completo", 
        value=st.session_state.usar_contexto_memoria,
        help="Incluye automáticamente tu información personal y alias en las consultas"
    )
    st.session_state.usar_contexto_memoria = contexto_activo

    # Controles de memoria
    col1, col2 = st.columns([2, 1])
    with col1:
        with st.popover(f"📚 Memoria ({cantidad_alias})", use_container_width=True):
            if memoria_usuario:
                st.markdown("**Alias guardados:**")
                for alias, value in memoria_usuario.items():
                    st.markdown(f"• **{alias}** → `{value}`")
                
                if st.button("🔄 Recargar memoria", use_container_width=True):
                    if "memoria_usuario" in st.session_state:
                        del st.session_state["memoria_usuario"]
                    st.rerun()
            else:
                st.info("No hay alias guardados")
                st.markdown("Los alias se crean automáticamente cuando el agente guarda información")

    with col2:
        if st.button("🗑️", key="clear_chat", help="Limpiar historial de chat"):
            st.session_state.pydantic_ai_messages = []
            st.session_state.streamlit_display_messages = []
            st.session_state.chat_history = []
            st.rerun()

    # ===== SECCIÓN ATLASSIAN =====
    st.markdown('<div style="height: 1px; background: rgba(255, 255, 255, 0.1); margin: 16px 0;"></div>', unsafe_allow_html=True)
    # Estado de credenciales
    if st.session_state.get("atlassian_api_key") and st.session_state.get("atlassian_username"):
        st.success("✅ Configurado")
    elif st.session_state.get("atlassian_api_key"):
        st.error("❌ Falta usuario")
    elif st.session_state.get("atlassian_username"):
        st.error("❌ Falta API Key")
    else:
        st.error("❌ No configurado")

    with st.popover("⚙️ Configurar credenciales", use_container_width=True):
        st.markdown("**Credenciales de Atlassian**")
        st.markdown("Se guardan para futuras sesiones.")

        key_for_input = st.session_state.get("atlassian_api_key", "")
        username_for_input = st.session_state.get("atlassian_username", "")
        
        new_api_key_input = st.text_input(
            "API Key:",
            type="password",
            value=key_for_input,
            placeholder="Tu API key"
        )
        
        new_username_input = st.text_input(
            "Email:",
            value=username_for_input,
            placeholder="tu@dominio.com"
        )

        col_save, col_clear = st.columns(2)
        with col_save:
            if st.button("💾 Guardar", use_container_width=True, type="primary"):
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
            if st.button("🗑️ Limpiar", use_container_width=True):
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

    # Información del sistema al final
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
        <span style="font-size: 10px !important;">v0.1.0 beta</span><br>
        <span style="font-size: 10px !important;">{fecha_actual}</span>
    </div>
    """, unsafe_allow_html=True)