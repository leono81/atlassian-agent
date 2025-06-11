#!/usr/bin/env python3
"""
Script de diagnóstico para el agente Atlassian
"""

import sys
sys.path.append('.')

def test_imports():
    """Prueba las importaciones básicas"""
    print("🔍 Probando importaciones...")
    
    try:
        from config import settings
        print("✅ Settings importado correctamente")
    except Exception as e:
        print(f"❌ Error importando settings: {e}")
        return False
    
    try:
        import logfire
        print("✅ Logfire importado correctamente")
    except Exception as e:
        print(f"❌ Error importando logfire: {e}")
        return False
    
    try:
        from config.logging_context import logger, log_user_action
        print("✅ Logging context importado correctamente")
    except Exception as e:
        print(f"❌ Error importando logging_context: {e}")
        return False
        
    try:
        from ui.agent_wrapper import simple_agent
        print("✅ Agent wrapper importado correctamente")
    except Exception as e:
        print(f"❌ Error importando agent_wrapper: {e}")
        return False
    
    return True

def test_basic_functions():
    """Prueba las funciones básicas"""
    print("\n🔍 Probando funciones básicas...")
    
    try:
        from config.logging_context import logger
        logger.info("Test básico de logging")
        print("✅ Logger funciona correctamente")
    except Exception as e:
        print(f"❌ Error en logger: {e}")
        return False
    
    try:
        import uuid
        operation_id = str(uuid.uuid4())[:8]
        print(f"✅ UUID generado: {operation_id}")
    except Exception as e:
        print(f"❌ Error generando UUID: {e}")
        return False
    
    return True

def test_agent_basic():
    """Prueba básica del agente"""
    print("\n🔍 Probando agente básico...")
    
    try:
        from ui.agent_wrapper import simple_agent
        print("✅ Agente importado correctamente")
        
        # Test muy básico sin llamada real
        print("✅ Agente disponible para pruebas")
        return True
    except Exception as e:
        print(f"❌ Error con el agente: {e}")
        return False

def main():
    """Función principal de diagnóstico"""
    print("🚀 DIAGNÓSTICO DEL AGENTE ATLASSIAN")
    print("=" * 50)
    
    # Test 1: Importaciones
    if not test_imports():
        print("\n❌ FALLO: Problema con importaciones")
        return 1
    
    # Test 2: Funciones básicas
    if not test_basic_functions():
        print("\n❌ FALLO: Problema con funciones básicas")
        return 1
    
    # Test 3: Agente básico
    if not test_agent_basic():
        print("\n❌ FALLO: Problema con el agente")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ DIAGNÓSTICO COMPLETO: Todo funciona correctamente")
    print("El problema puede estar en Streamlit o en la configuración específica")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 