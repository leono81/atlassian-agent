#!/usr/bin/env python3
"""
Script de prueba para verificar que la corrección de search_issues funciona
"""
import asyncio
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, '/home/leono/Projects/ai_agents/atlassian agent')

from tools.jira_tools import search_issues
from config.logging_context import logger

async def test_search_issues():
    """
    Prueba básica de la función search_issues corregida
    """
    try:
        logger.info("🧪 Iniciando prueba de search_issues corregida")
        
        # Consulta JQL simple para probar
        test_jql = 'project = "PSIMDESASW" ORDER BY created DESC'
        
        logger.info("🔍 Ejecutando búsqueda con JQL: {jql}", jql=test_jql)
        
        # Usar credenciales de las variables de entorno si están disponibles
        # (en producción se obtendrían de st.session_state)
        result = await search_issues(
            jql_query=test_jql,
            max_results=5,
            atlassian_username=os.getenv("ATLASSIAN_USERNAME"),
            atlassian_api_key=os.getenv("ATLASSIAN_API_KEY")
        )
        
        logger.info("✅ Búsqueda completada. Encontrados {count} issues", count=len(result))
        
        # Mostrar algunos detalles de los resultados
        for i, issue in enumerate(result[:3]):  # Solo primeros 3
            logger.info("📋 Issue {index}: {key} - {summary}", 
                       index=i+1, key=issue.key, summary=issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary)
        
        return True
        
    except Exception as e:
        logger.error("❌ Error en la prueba: {error}", error=str(e))
        return False

if __name__ == "__main__":
    success = asyncio.run(test_search_issues())
    
    if success:
        print("\n🎉 ¡Corrección exitosa! La función search_issues ahora usa jira.jql() correctamente.")
    else:
        print("\n💥 La prueba falló. Revisa los logs para más detalles.") 