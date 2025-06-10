#!/usr/bin/env python3
"""
Script de prueba simple para verificar que la corrección de search_issues funciona
"""
import asyncio
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, '/home/leono/Projects/ai_agents/atlassian agent')

async def test_jira_connection():
    """
    Prueba básica de conexión y corrección de search_issues
    """
    try:
        print("🧪 Iniciando prueba de corrección de Jira...")
        
        # Importar directamente el cliente para probar la corrección
        from agent_core.jira_instances import get_jira_client
        
        print("🔗 Obteniendo cliente Jira...")
        jira = get_jira_client()
        
        print("🔍 Probando el método jql() (método correcto)...")
        
        # Probar directamente el método que corregimos
        loop = asyncio.get_running_loop()
        jql_response = await loop.run_in_executor(None, 
            lambda: jira.jql('project = "PSIMDESASW" ORDER BY created DESC', limit=3))
        
        print(f"📊 Tipo de respuesta: {type(jql_response)}")
        
        if isinstance(jql_response, dict) and "issues" in jql_response:
            issues = jql_response["issues"]
            print(f"✅ Respuesta correcta! Encontrados {len(issues)} issues")
            
            for i, issue in enumerate(issues):
                print(f"  📋 {i+1}. {issue.get('key')} - {issue.get('fields', {}).get('summary', 'Sin summary')[:50]}...")
            
            return True
        else:
            print(f"❌ Respuesta inesperada: {jql_response}")
            return False
            
    except Exception as e:
        print(f"❌ Error en la prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Ejecutando prueba de corrección Jira...")
    success = asyncio.run(test_jira_connection())
    
    if success:
        print("\n🎉 ¡Corrección verificada! El método jira.jql() funciona correctamente.")
        print("   La función search_issues debería funcionar ahora en el agente.")
    else:
        print("\n💥 La prueba falló. Verifica la configuración o credenciales.") 