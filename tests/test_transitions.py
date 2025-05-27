#!/usr/bin/env python3
"""
Script de prueba para las nuevas funcionalidades de transiciones y estados de Jira.
Prueba las funciones: get_issue_transitions, get_project_workflow_statuses, y transition_issue.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
import logfire
from tools.jira_tools import (
    get_issue_transitions,
    get_project_workflow_statuses,
    transition_issue
)

# Configurar logfire
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="test_transitions",
    service_version="1.0.0"
)

async def test_get_issue_transitions():
    """Prueba la función get_issue_transitions"""
    print("\n=== PRUEBA: get_issue_transitions ===")
    
    # Usar un issue existente - CAMBIA ESTO por un issue real de tu proyecto
    test_issue_key = "PSIMDESASW-6701"  # CAMBIA ESTO
    
    try:
        result = await get_issue_transitions(test_issue_key)
        
        print(f"Issue: {result.issue_key}")
        print(f"Resumen: {result.issue_summary}")
        print(f"Estado actual: {result.current_status.name} (ID: {result.current_status.id})")
        print(f"Categoría: {result.current_status.category_name}")
        print(f"Total de transiciones disponibles: {result.total_transitions}")
        
        if result.available_transitions:
            print("\nTransiciones disponibles:")
            for i, transition in enumerate(result.available_transitions, 1):
                print(f"{i}. {transition.name} (ID: {transition.id})")
                print(f"   → Estado destino: {transition.to_status.name}")
                print(f"   → Requiere pantalla: {'Sí' if transition.has_screen else 'No'}")
                
                if transition.required_fields:
                    print(f"   → Campos requeridos:")
                    for field in transition.required_fields:
                        print(f"     - {field.field_name} ({field.field_id}) - Requerido: {field.required}")
                        if field.allowed_values:
                            print(f"       Valores permitidos: {', '.join(field.allowed_values)}")
                else:
                    print(f"   → Campos requeridos: Ninguno")
                print()
        else:
            print("No hay transiciones disponibles para este issue.")
            
        return result
        
    except Exception as e:
        print(f"Error en test_get_issue_transitions: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_get_project_workflow_statuses():
    """Prueba la función get_project_workflow_statuses"""
    print("\n=== PRUEBA: get_project_workflow_statuses ===")
    
    # Usar un proyecto existente - CAMBIA ESTO por tu proyecto
    test_project_key = "PSIMDESASW"  # CAMBIA ESTO
    
    try:
        result = await get_project_workflow_statuses(test_project_key)
        
        print(f"Proyecto: {result.project_key}")
        print(f"Nombre del proyecto: {result.project_name}")
        print(f"Workflow: {result.workflow_name or 'No especificado'}")
        print(f"Total de estados: {result.total_statuses}")
        
        if result.all_statuses:
            print("\nTodos los estados disponibles:")
            for i, status in enumerate(result.all_statuses, 1):
                print(f"{i}. {status.name} (ID: {status.id})")
                if status.description:
                    print(f"   Descripción: {status.description}")
                if status.category:
                    print(f"   Categoría: {status.category}")
                print()
        else:
            print("No se encontraron estados para este proyecto.")
            
        return result
        
    except Exception as e:
        print(f"Error en test_get_project_workflow_statuses: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_transition_issue():
    """Prueba la función transition_issue (SOLO SI HAY TRANSICIONES DISPONIBLES)"""
    print("\n=== PRUEBA: transition_issue ===")
    
    # ADVERTENCIA: Esta función modifica datos reales en Jira
    # Solo ejecutar si estás seguro y tienes un issue de prueba
    
    print("ADVERTENCIA: Esta prueba modificará datos reales en Jira.")
    print("Solo debe ejecutarse con issues de prueba.")
    
    # Obtener transiciones primero
    test_issue_key = "PSIMDESASW-6701"  # CAMBIA ESTO
    
    try:
        transitions_result = await get_issue_transitions(test_issue_key)
        
        if not transitions_result.available_transitions:
            print(f"No hay transiciones disponibles para {test_issue_key}. Saltando prueba de transición.")
            return None
        
        print(f"\nTransiciones disponibles para {test_issue_key}:")
        for i, transition in enumerate(transitions_result.available_transitions, 1):
            print(f"{i}. {transition.name} (ID: {transition.id}) → {transition.to_status.name}")
        
        # Para la prueba, NO ejecutaremos la transición automáticamente
        # Solo mostraremos cómo se haría
        print("\n--- SIMULACIÓN DE TRANSICIÓN ---")
        print("Para ejecutar una transición, usarías:")
        
        if transitions_result.available_transitions:
            first_transition = transitions_result.available_transitions[0]
            print(f"await transition_issue(")
            print(f"    issue_key='{test_issue_key}',")
            print(f"    transition_id='{first_transition.id}',")
            print(f"    comment='Transición ejecutada por script de prueba'")
            print(f")")
            print(f"# Esto movería el issue a: {first_transition.to_status.name}")
        
        # Si quieres ejecutar la transición real, descomenta las siguientes líneas:
        # CUIDADO: Esto modificará el issue real
        """
        if transitions_result.available_transitions:
            first_transition = transitions_result.available_transitions[0]
            result = await transition_issue(
                issue_key=test_issue_key,
                transition_id=first_transition.id,
                comment="Transición ejecutada por script de prueba"
            )
            
            print(f"\nResultado de la transición:")
            print(f"Éxito: {result['success']}")
            print(f"Nuevo estado: {result.get('new_status', 'Unknown')}")
            print(f"Mensaje: {result.get('message', 'Sin mensaje')}")
            
            return result
        """
        
        return {"simulated": True, "message": "Transición simulada, no ejecutada"}
        
    except Exception as e:
        print(f"Error en test_transition_issue: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Función principal que ejecuta todas las pruebas"""
    print("🚀 Iniciando pruebas de funcionalidades de transiciones y estados de Jira")
    print("=" * 70)
    
    # Prueba 1: Obtener transiciones de un issue
    transitions_result = await test_get_issue_transitions()
    
    # Prueba 2: Obtener estados del workflow del proyecto
    workflow_result = await test_get_project_workflow_statuses()
    
    # Prueba 3: Simular transición de issue (sin ejecutar)
    transition_result = await test_transition_issue()
    
    print("\n" + "=" * 70)
    print("✅ Pruebas completadas")
    
    # Resumen
    print("\n📊 RESUMEN:")
    if transitions_result:
        print(f"✓ Transiciones obtenidas para {transitions_result.issue_key}: {transitions_result.total_transitions} disponibles")
    else:
        print("✗ Error al obtener transiciones")
    
    if workflow_result:
        print(f"✓ Estados del workflow obtenidos para {workflow_result.project_key}: {workflow_result.total_statuses} estados")
    else:
        print("✗ Error al obtener estados del workflow")
    
    if transition_result:
        if transition_result.get("simulated"):
            print("✓ Transición simulada correctamente (no ejecutada)")
        else:
            print("✓ Transición ejecutada correctamente")
    else:
        print("✗ Error en la prueba de transición")

if __name__ == "__main__":
    print("IMPORTANTE: Antes de ejecutar, asegúrate de cambiar los valores de prueba:")
    print("- test_issue_key: Cambia 'PSIMDESASW-6701' por un issue real de tu proyecto")
    print("- test_project_key: Cambia 'PSIMDESASW' por tu proyecto real")
    print()
    
    # Ejecutar las pruebas
    asyncio.run(main()) 