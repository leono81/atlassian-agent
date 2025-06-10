"""
Servicio centralizado de autenticación para la aplicación.
Maneja la identidad del usuario, sesiones y limpieza de estado de forma consistente.
"""

import streamlit as st
from typing import Optional, Tuple, Dict, Any
import logfire
from dataclasses import dataclass
from enum import Enum

class AuthMethod(Enum):
    """Métodos de autenticación soportados"""
    LOCAL = "local_auth"
    GOOGLE_OAUTH = "google_oauth"
    ADMIN_PANEL = "admin_panel"
    DEMO = "demo"

@dataclass
class UserInfo:
    """Información del usuario autenticado"""
    user_id: str  # Email o identificador único
    display_name: str
    auth_method: AuthMethod
    is_admin: bool = False
    session_id: Optional[str] = None
    
class AuthService:
    """
    Servicio centralizado de autenticación que proporciona una interfaz
    consistente para la gestión de usuarios independientemente del método de auth.
    """
    
    @staticmethod
    def get_current_user() -> Optional[UserInfo]:
        """
        Obtiene información del usuario actual autenticado.
        Retorna None si no hay usuario autenticado.
        """
        try:
            # Prioridad 1: Usuario local autenticado
            if st.session_state.get('local_user_authenticated', False):
                user_id = st.session_state.get('local_user_email', '')
                display_name = st.session_state.get('local_user_display_name', user_id)
                is_admin = st.session_state.get('local_user_is_admin', False)
                session_id = st.session_state.get('local_user_session_id')
                
                if user_id:
                    return UserInfo(
                        user_id=user_id,
                        display_name=display_name,
                        auth_method=AuthMethod.LOCAL,
                        is_admin=is_admin,
                        session_id=session_id
                    )
            
            # Prioridad 2: Usuario OAuth2 (Google)
            try:
                if hasattr(st, 'user') and hasattr(st.user, 'is_logged_in') and st.user.is_logged_in:
                    user_id = getattr(st.user, 'email', '')
                    display_name = getattr(st.user, 'name', user_id)
                    
                    if user_id:
                        return UserInfo(
                            user_id=user_id,
                            display_name=display_name,
                            auth_method=AuthMethod.GOOGLE_OAUTH,
                            is_admin=True  # Por defecto en OAuth2
                        )
            except (AttributeError, KeyError):
                pass
            
            # Prioridad 3: Usuario demo (fallback)
            # Solo para desarrollo/demo, no debería usarse en producción
            auth_method = st.session_state.get('auth_method')
            if auth_method in ['demo', None]:  # Si es demo o no hay método
                return UserInfo(
                    user_id="atlassian_agent_user_001",
                    display_name="Usuario Demo",
                    auth_method=AuthMethod.DEMO,
                    is_admin=False
                )
            
            return None
            
        except Exception as e:
            logfire.error(f"Error obteniendo usuario actual: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_user_id() -> str:
        """
        Obtiene el ID del usuario actual (para usar con mem0 y otros servicios).
        Siempre retorna un string, usando fallback si es necesario.
        """
        user_info = AuthService.get_current_user()
        if user_info:
            return user_info.user_id
        
        # Fallback para compatibilidad
        return "atlassian_agent_user_001"
    
    @staticmethod
    def get_user_display_info() -> Tuple[str, str]:
        """
        Obtiene información de display del usuario (ID, nombre).
        Retorna tupla (user_id, display_name).
        """
        user_info = AuthService.get_current_user()
        if user_info:
            return user_info.user_id, user_info.display_name
        
        # Fallback
        return "atlassian_agent_user_001", "Usuario Demo"
    
    @staticmethod
    def is_user_admin() -> bool:
        """
        Verifica si el usuario actual tiene permisos de administrador.
        """
        user_info = AuthService.get_current_user()
        return user_info.is_admin if user_info else False
    
    @staticmethod
    def is_authenticated() -> bool:
        """
        Verifica si hay un usuario autenticado actualmente.
        """
        user_info = AuthService.get_current_user()
        return user_info is not None and user_info.auth_method != AuthMethod.DEMO
    
    @staticmethod
    def get_auth_method() -> Optional[AuthMethod]:
        """
        Obtiene el método de autenticación actual.
        """
        user_info = AuthService.get_current_user()
        return user_info.auth_method if user_info else None
    
    @staticmethod
    def clear_user_session(exclude_keys: Optional[list] = None):
        """
        Limpia completamente la sesión del usuario actual.
        
        Args:
            exclude_keys: Lista de keys del session_state que NO deben ser limpiados
        """
        exclude_keys = exclude_keys or []
        
        # Keys críticos que siempre se deben limpiar para seguridad
        critical_keys_to_clear = [
            # Autenticación y sesión
            'local_user_authenticated',
            'local_user_email', 
            'local_user_display_name',
            'local_user_is_admin',
            'local_user_session_id',
            'user_authenticated', 
            'user_email', 
            'display_name',
            
            # Datos de la aplicación específicos del usuario
            'chat_history',
            'pydantic_ai_messages',
            'streamlit_display_messages',
            'memoria_usuario',
            
            # Credenciales sensibles
            'atlassian_api_key',
            'atlassian_username',
            
            # Contexto del usuario
            'last_logged_user'
        ]
        
        # Keys adicionales que pueden limpiarse opcionalmente
        optional_keys_to_clear = [
            'auth_method',  # Solo limpiar si no está en exclude_keys
        ]
        
        # Limpiar keys críticos (siempre)
        for key in critical_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                
        # Limpiar keys opcionales (solo si no están excluidos)
        for key in optional_keys_to_clear:
            if key not in exclude_keys and key in st.session_state:
                del st.session_state[key]
        
        logfire.info("user_session_cleared", 
                    critical_keys_cleared=len([k for k in critical_keys_to_clear if k in st.session_state]),
                    optional_keys_cleared=len([k for k in optional_keys_to_clear if k not in exclude_keys and k in st.session_state]))
    
    @staticmethod
    def handle_user_change():
        """
        Detecta y maneja cambios de usuario automáticamente.
        Debe ser llamado al inicio de la aplicación.
        
        Returns:
            bool: True si hubo cambio de usuario, False si no
        """
        current_user_id = AuthService.get_user_id()
        last_user_id = st.session_state.get('last_logged_user')
        
        if last_user_id and last_user_id != current_user_id:
            # Cambio de usuario detectado
            logfire.info("user_change_detected",
                        previous_user=last_user_id,
                        new_user=current_user_id)
            
            # Limpiar estado del usuario anterior
            AuthService.clear_user_session(exclude_keys=['auth_method'])
            
            # Actualizar el último usuario
            st.session_state['last_logged_user'] = current_user_id
            
            # Limpiar cache específico de mem0 (se implementará después)
            AuthService._clear_mem0_cache_for_user_change(last_user_id, current_user_id)
            
            logfire.info("user_change_handled",
                        from_user=last_user_id,
                        to_user=current_user_id)
            
            return True
        else:
            # No hay cambio o es el primer acceso
            st.session_state['last_logged_user'] = current_user_id
            return False
    
    @staticmethod
    def _clear_mem0_cache_for_user_change(old_user: str, new_user: str):
        """
        Limpia cache específico de mem0 cuando cambia el usuario.
        Esto es crítico para la seguridad multiusuario.
        """
        try:
            # Usar la función especializada de mem0_tools
            from tools.mem0_tools import invalidate_user_memory_cache
            invalidate_user_memory_cache(old_user, new_user)
            
            logfire.info("mem0_cache_cleared_for_user_change",
                        old_user=old_user,
                        new_user=new_user)
                        
        except ImportError as e:
            logfire.error("Error importando invalidate_user_memory_cache", 
                         old_user=old_user, new_user=new_user, error=e)
            # Fallback: limpiar directamente
            if 'memoria_usuario' in st.session_state:
                del st.session_state['memoria_usuario']
                
        except Exception as e:
            logfire.error("Error limpiando cache mem0 para cambio de usuario", 
                         old_user=old_user, new_user=new_user, error=e)
    
    @staticmethod
    def get_debug_info() -> Dict[str, Any]:
        """
        Obtiene información de debug sobre el estado de autenticación.
        Útil para troubleshooting.
        """
        user_info = AuthService.get_current_user()
        
        return {
            'current_user': user_info.__dict__ if user_info else None,
            'session_state_keys': list(st.session_state.keys()),
            'auth_related_keys': {
                k: st.session_state.get(k, 'NOT_FOUND') 
                for k in ['local_user_authenticated', 'local_user_email', 'auth_method', 'last_logged_user']
            },
            'is_authenticated': AuthService.is_authenticated(),
            'user_id': AuthService.get_user_id(),
        } 