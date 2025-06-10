#!/usr/bin/env python3
"""
Script de diagnóstico para entender la estructura de las memorias en mem0.
Esto nos ayudará a entender por qué no se encuentran las memorias guardadas.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print("🔍 Diagnóstico de estructura de memorias en mem0")
    print("=" * 60)
    
    try:
        # Importar las herramientas necesarias
        from tools.mem0_tools import mem0_client, get_current_user_id
        import json
        
        if not mem0_client:
            print("❌ mem0_client no está inicializado")
            print("   Verifica que MEM0_API_KEY esté configurado")
            return
        
        print("✅ mem0_client inicializado correctamente")
        
        # Obtener el usuario actual
        user_id = "user@empresa.com"  # Usuario de prueba específico
        print(f"👤 Usuario de prueba: {user_id}")
        
        print("\n📋 Intentando obtener todas las memorias con get_all()...")
        try:
            all_memories_result = mem0_client.get_all(user_id=user_id, limit=50)
            print(f"📄 Resultado de get_all(): {type(all_memories_result)}")
            print(f"📄 Contenido completo:")
            print(json.dumps(all_memories_result, indent=2, default=str))
            
            # Analizar la estructura
            if isinstance(all_memories_result, list):
                print(f"\n📊 Es una lista con {len(all_memories_result)} elementos")
                if all_memories_result:
                    print("🔍 Primer elemento:")
                    print(json.dumps(all_memories_result[0], indent=2, default=str))
            elif isinstance(all_memories_result, dict):
                print(f"\n📊 Es un diccionario con claves: {list(all_memories_result.keys())}")
                
                # Buscar donde están las memorias
                for key in ["results", "memories", "data"]:
                    if key in all_memories_result:
                        memories = all_memories_result[key]
                        print(f"🎯 Memorias encontradas en '{key}': {len(memories) if isinstance(memories, list) else 'no es lista'}")
                        if isinstance(memories, list) and memories:
                            print("🔍 Primera memoria:")
                            print(json.dumps(memories[0], indent=2, default=str))
                        break
            
        except Exception as e:
            print(f"❌ Error con get_all(): {e}")
            print(f"   Tipo de error: {type(e)}")
        
        print("\n🔍 Intentando búsqueda semántica con diferentes queries...")
        search_queries = ["manuel", "nombre", "alias", "user", " "]
        
        for query in search_queries:
            try:
                print(f"\n🔎 Buscando con query: '{query}'")
                search_result = mem0_client.search(
                    query=query,
                    user_id=user_id,
                    limit=10
                )
                print(f"📄 Tipo de resultado: {type(search_result)}")
                
                if isinstance(search_result, dict):
                    if "results" in search_result:
                        results = search_result["results"]
                        print(f"📊 Encontradas {len(results)} memorias")
                        if results:
                            print("🔍 Primera memoria encontrada:")
                            print(json.dumps(results[0], indent=2, default=str))
                    else:
                        print("📄 Estructura del resultado:")
                        print(json.dumps(search_result, indent=2, default=str))
                elif isinstance(search_result, list):
                    print(f"📊 Lista con {len(search_result)} elementos")
                    if search_result:
                        print("🔍 Primer elemento:")
                        print(json.dumps(search_result[0], indent=2, default=str))
                else:
                    print(f"📄 Resultado: {search_result}")
                    
            except Exception as e:
                print(f"❌ Error en búsqueda '{query}': {e}")
        
        print("\n🧪 Intentando guardar una memoria de prueba...")
        try:
            test_memory = f"Test memory for user {user_id} at {os.getpid()}"
            save_result = mem0_client.add(
                test_memory,
                user_id=user_id,
                metadata={"alias": "test_alias", "value": "test_value", "type": "test"}
            )
            print(f"💾 Resultado de guardar: {save_result}")
            
            # Intentar buscar la memoria recién guardada
            print("🔍 Buscando la memoria recién guardada...")
            fresh_search = mem0_client.search(
                query="test memory",
                user_id=user_id,
                limit=5
            )
            print(f"📄 Resultado de búsqueda fresca: {fresh_search}")
            
        except Exception as e:
            print(f"❌ Error guardando memoria de prueba: {e}")
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 