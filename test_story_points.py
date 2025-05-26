#!/usr/bin/env python3
"""
Script de prueba para verificar la función get_issue_story_points
"""

import asyncio
from tools.jira_tools import get_issue_story_points, get_issue_details
from config import settings
import logfire

# Configurar logfire
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="story_points_test"
)

async def test_story_points():
    """Prueba la función de Story Points con un issue existente"""
    
    # Cambia este issue key por uno que exista en tu Jira
    test_issue_key = "PSIMDESASW-6701"  # Cambia por un issue real
    
    print(f"🔍 Probando Story Points para issue: {test_issue_key}")
    print("=" * 60)
    
    # Probar la función específica de Story Points
    print("\n1. Probando get_issue_story_points()...")
    story_points_result = await get_issue_story_points(test_issue_key)
    
    print(f"   Issue: {story_points_result['issue_key']}")
    print(f"   Resumen: {story_points_result.get('issue_summary', 'N/A')}")
    print(f"   Tipo: {story_points_result.get('issue_type', 'N/A')}")
    print(f"   Story Points: {story_points_result['story_points']}")
    print(f"   Encontrado: {story_points_result['found']}")
    print(f"   Mensaje: {story_points_result['message']}")
    
    if story_points_result.get('debug_fields_found'):
        print(f"   Campos debug encontrados: {story_points_result['debug_fields_found']}")
    
    # Probar también get_issue_details para ver si incluye Story Points
    print("\n2. Probando get_issue_details() (ahora incluye Story Points)...")
    issue_details = await get_issue_details(test_issue_key)
    
    print(f"   Issue: {issue_details.key}")
    print(f"   Resumen: {issue_details.summary}")
    print(f"   Estado: {issue_details.status}")
    print(f"   Story Points: {issue_details.story_points}")
    print(f"   Responsable: {issue_details.assignee}")
    
    print("\n" + "=" * 60)
    print("✅ Prueba completada!")
    
    if story_points_result['found']:
        print(f"🎯 Story Points encontrados: {story_points_result['story_points']} SP")
    else:
        print("⚠️  No se encontraron Story Points configurados para este issue")
        print("   Esto puede ser normal si:")
        print("   - El issue no tiene Story Points asignados")
        print("   - El campo de Story Points está en un customfield diferente")
        print("   - Tu instancia de Jira no usa Story Points")

if __name__ == "__main__":
    asyncio.run(test_story_points()) 