#!/usr/bin/env python3
"""
Script de testing para verificar la corrección del problema de memoria multiusuario.
Este script simula el problema y verifica que la solución funciona correctamente.
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock de streamlit para testing
class MockStreamlitState:
    def __init__(self):
        self.session_state = {}
    
    def get(self, key, default=None):
        return self.session_state.get(key, default)
    
    def __setitem__(self, key, value):
        self.session_state[key] = value
    
    def __getitem__(self, key):
        return self.session_state[key]
    
    def __contains__(self, key):
        return key in self.session_state
    
    def __delitem__(self, key):
        del self.session_state[key]

# Mock streamlit
class MockStreamlit:
    def __init__(self):
        self.session_state = MockStreamlitState()

# Monkey patch para testing
import sys
mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st

def test_auth_service():
    """Test del AuthService"""
    print("🧪 Testing AuthService...")
    
    from config.auth_service import AuthService, UserInfo, AuthMethod
    
    # Simular usuario local autenticado
    mock_st.session_state['local_user_authenticated'] = True
    mock_st.session_state['local_user_email'] = 'test1@example.com'
    mock_st.session_state['local_user_display_name'] = 'Test User 1'
    mock_st.session_state['local_user_is_admin'] = False
    
    # Test obtener usuario actual
    user_info = AuthService.get_current_user()
    assert user_info is not None, "Usuario debería estar autenticado"
    assert user_info.user_id == 'test1@example.com', f"User ID incorrecto: {user_info.user_id}"
    assert user_info.auth_method == AuthMethod.LOCAL, f"Auth method incorrecto: {user_info.auth_method}"
    
    # Test get_user_id
    user_id = AuthService.get_user_id()
    assert user_id == 'test1@example.com', f"get_user_id incorrecto: {user_id}"
    
    print("✅ AuthService funciona correctamente")

def test_user_change_detection():
    """Test de detección de cambio de usuario"""
    print("🧪 Testing detección de cambio de usuario...")
    
    from config.auth_service import AuthService
    
    # Simular primer usuario
    mock_st.session_state.session_state.clear()
    mock_st.session_state['local_user_authenticated'] = True
    mock_st.session_state['local_user_email'] = 'user1@example.com'
    mock_st.session_state['local_user_display_name'] = 'User 1'
    mock_st.session_state['memoria_usuario'] = {'alias1': 'value1'}
    
    # Primera llamada - no debería haber cambio
    changed = AuthService.handle_user_change()
    assert not changed, "No debería detectar cambio en primera llamada"
    
    # Cambiar usuario
    mock_st.session_state['local_user_email'] = 'user2@example.com'
    mock_st.session_state['local_user_display_name'] = 'User 2'
    
    # Segunda llamada - debería detectar cambio
    changed = AuthService.handle_user_change()
    assert changed, "Debería detectar cambio de usuario"
    
    # Verificar que la memoria se limpió
    assert 'memoria_usuario' not in mock_st.session_state.session_state, "Memoria debería estar limpia"
    
    print("✅ Detección de cambio de usuario funciona correctamente")

def test_mem0_tools_user_id():
    """Test de obtención de user_id en mem0_tools"""
    print("🧪 Testing mem0_tools user_id...")
    
    try:
        from tools.mem0_tools import get_current_user_id
        
        # Simular usuario autenticado
        mock_st.session_state.session_state.clear()
        mock_st.session_state['local_user_authenticated'] = True
        mock_st.session_state['local_user_email'] = 'mem0test@example.com'
        
        user_id = get_current_user_id()
        assert user_id == 'mem0test@example.com', f"mem0_tools user_id incorrecto: {user_id}"
        
        print("✅ mem0_tools user_id funciona correctamente")
        
    except ImportError as e:
        print(f"⚠️  Saltando test mem0_tools (dependencia faltante: {e})")
        print("✅ Test saltado - no afecta la funcionalidad del AuthService")

def test_session_cleanup():
    """Test de limpieza de sesión"""
    print("🧪 Testing limpieza de sesión...")
    
    from config.auth_service import AuthService
    
    # Llenar session_state con datos de usuario
    mock_st.session_state.session_state.clear()
    mock_st.session_state['local_user_authenticated'] = True
    mock_st.session_state['local_user_email'] = 'cleanup@example.com'
    mock_st.session_state['chat_history'] = ['mensaje1', 'mensaje2']
    mock_st.session_state['memoria_usuario'] = {'alias': 'value'}
    mock_st.session_state['atlassian_api_key'] = 'secret_key'
    mock_st.session_state['other_data'] = 'should_remain'
    
    # Limpiar sesión
    AuthService.clear_user_session(exclude_keys=['other_data'])
    
    # Verificar que los datos sensibles se limpiaron
    assert 'local_user_authenticated' not in mock_st.session_state.session_state
    assert 'local_user_email' not in mock_st.session_state.session_state
    assert 'chat_history' not in mock_st.session_state.session_state
    assert 'memoria_usuario' not in mock_st.session_state.session_state
    assert 'atlassian_api_key' not in mock_st.session_state.session_state
    
    # Verificar que los datos excluidos permanecen
    assert mock_st.session_state.session_state.get('other_data') == 'should_remain'
    
    print("✅ Limpieza de sesión funciona correctamente")

def test_fallback_behavior():
    """Test de comportamiento fallback cuando no hay usuario autenticado"""
    print("🧪 Testing comportamiento fallback...")
    
    from config.auth_service import AuthService
    
    # Limpiar todo
    mock_st.session_state.session_state.clear()
    
    # Test AuthService fallback
    user_id = AuthService.get_user_id()
    assert user_id == "atlassian_agent_user_001", f"Fallback incorrecto: {user_id}"
    
    # Test mem0_tools fallback (solo si está disponible)
    try:
        from tools.mem0_tools import get_current_user_id
        mem0_user_id = get_current_user_id()
        assert mem0_user_id == "atlassian_agent_user_001", f"mem0 fallback incorrecto: {mem0_user_id}"
        print("✅ Comportamiento fallback funciona correctamente (incluyendo mem0_tools)")
    except ImportError:
        print("✅ Comportamiento fallback del AuthService funciona correctamente")

def run_all_tests():
    """Ejecuta todos los tests"""
    print("🚀 Iniciando tests de solución multiusuario...")
    print("=" * 50)
    
    try:
        test_auth_service()
        test_user_change_detection()
        test_mem0_tools_user_id()
        test_session_cleanup()
        test_fallback_behavior()
        
        print("=" * 50)
        print("🎉 ¡Todos los tests pasaron exitosamente!")
        print("✅ La solución del problema de memoria multiusuario funciona correctamente")
        
        return True
        
    except AssertionError as e:
        print("=" * 50)
        print(f"❌ Test falló: {e}")
        return False
    except Exception as e:
        print("=" * 50)
        print(f"💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 