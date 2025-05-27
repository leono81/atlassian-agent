import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
from mem0 import MemoryClient
import logfire

# User ID fijo para todas las interacciones con Mem0
USER_ID_FIJO = "atlassian_agent_user_001" # Puedes cambiar este valor si lo deseas

# Configuración: obtener la API key de Mem0 desde el entorno
MEM0_API_KEY = os.getenv("MEM0_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Corrected client initialization
mem0_client = None
if MEM0_API_KEY:
    try:
        mem0_client = MemoryClient(api_key=MEM0_API_KEY)
        logfire.info(f"Mem0 Client initialized with MEM0_API_KEY for user {USER_ID_FIJO}.")
    except Exception as e:
        logfire.error(f"Error initializing Mem0 Client with MEM0_API_KEY: {e}", exc_info=True)
        mem0_client = None
elif OPENAI_API_KEY: # If MEM0_API_KEY is not present, but OPENAI_API_KEY is, try initializing with that for local/dev usage
    try:
        logfire.info("MEM0_API_KEY not found. Attempting to initialize Mem0 Client (e.g. with OpenAI API key for local/dev)...")
        mem0_client = MemoryClient() # Assuming it can pick up OPENAI_API_KEY from env or has other fallbacks
        logfire.info(f"Mem0 Client initialized (fallback) for user {USER_ID_FIJO}. Note: Full functionality may depend on Mem0 service connection.")
    except Exception as e:
        logfire.error(f"Error initializing Mem0 Client with fallback: {e}", exc_info=True)
        mem0_client = None

class SaveMemoryRequest(BaseModel):
    alias: str = Field(..., description="Nombre corto, apodo o alias que el usuario quiere recordar.")
    value: str = Field(..., description="Valor asociado al alias. Puede ser un ID, texto, número, etc.")
    type: Optional[str] = Field(default=None, description="Tipo de memoria (ej: 'jira_alias', 'soporte', 'cliente', etc.).")
    context: Optional[str] = Field(default=None, description="Contexto adicional o descripción.")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales opcionales.")

class SaveMemoryResponse(BaseModel):
    memory_id: str = Field(..., description="ID de la memoria guardada.")
    status: str = Field(..., description="Estado de la operación.")

class SearchMemoryRequest(BaseModel):
    alias: Optional[str] = Field(default=None, description="Alias o apodo a buscar.")
    type: Optional[str] = Field(default=None, description="Tipo de memoria a buscar.")
    value: Optional[str] = Field(default=None, description="Valor asociado a buscar.")
    query: Optional[str] = Field(default=None, description="Búsqueda semántica libre.")
    limit: int = Field(default=3, description="Máximo de resultados a devolver.")

class MemoryResult(BaseModel):
    memory_id: str
    alias: str
    value: str
    type: Optional[str] = None
    context: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

class SearchMemoryResponse(BaseModel):
    results: List[MemoryResult]
    status: str

async def save_memory(
    alias: str = Field(..., description="Nombre corto, apodo o alias que el usuario quiere recordar."),
    value: str = Field(..., description="Valor asociado al alias. Puede ser un ID, texto, número, etc."),
    type: Optional[str] = Field(default=None, description="Tipo de memoria (ej: 'jira_alias', 'soporte', 'cliente', etc.)."),
    context: Optional[str] = Field(default=None, description="Contexto adicional o descripción."),
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Metadatos adicionales opcionales.")
) -> SaveMemoryResponse:
    """
    Guarda una memoria personalizada para el usuario, asociando un alias a un valor y metadatos.
    """
    if not mem0_client:
        logfire.warn("save_memory called but mem0_client is not initialized.")
        return SaveMemoryResponse(memory_id="ERROR", status="Mem0 client not initialized. Set MEM0_API_KEY or ensure OPENAI_API_KEY is configured for fallback.")

    _type_val = type.default if isinstance(type, FieldInfo) else type
    _context_val = context.default if isinstance(context, FieldInfo) else context
    _extra_val = extra.default if isinstance(extra, FieldInfo) else extra
    
    metadata = {"alias": alias, "value": value}
    if _type_val is not None:
        metadata["type"] = _type_val
    if _context_val is not None:
        metadata["context"] = _context_val
    if _extra_val and isinstance(_extra_val, dict):
        metadata.update(_extra_val)
    
    content_str = f"{alias} => {value}" if _context_val is None else f"{alias} => {value} ({_context_val})"
    
    try:
        result = mem0_client.add(
            [{"role": "user", "content": content_str}],
            user_id=USER_ID_FIJO,
            metadata=metadata
        )
        logfire.debug(f"Mem0 client.add() raw result: {result}")
        
        memory_id = "ERROR"
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and result[0].get("id"):
            memory_id = result[0]["id"]
        elif isinstance(result, dict) and result.get("id"):
            memory_id = result["id"]
        elif isinstance(result, dict) and "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0 and result["results"][0].get("id"):
            memory_id = result["results"][0]["id"]

        if memory_id == "ERROR":
             logfire.error(f"Failed to extract memory_id from mem0 result. Raw result: {result}")
        return SaveMemoryResponse(memory_id=memory_id, status="ok" if memory_id != "ERROR" else "error saving memory")
    except Exception as e:
        logfire.error(f"Error during mem0_client.add or processing its result: {e}", exc_info=True)
        return SaveMemoryResponse(memory_id="ERROR", status=f"Error saving memory: {str(e)}")

async def search_memory(
    alias: Optional[str] = Field(default=None, description="Alias o apodo a buscar."),
    type: Optional[str] = Field(default=None, description="Tipo de memoria a buscar."),
    value: Optional[str] = Field(default=None, description="Valor asociado a buscar."),
    query: Optional[str] = Field(default=None, description="Búsqueda semántica libre."),
    limit: int = Field(default=3, description="Máximo de resultados a devolver.")
) -> SearchMemoryResponse:
    """
    Busca memorias del usuario por alias, tipo, valor o búsqueda semántica.
    """
    if not mem0_client:
        logfire.warn("search_memory called but mem0_client is not initialized.")
        return SearchMemoryResponse(results=[], status="Mem0 client not initialized. Set MEM0_API_KEY or ensure OPENAI_API_KEY is configured for fallback.")

    _alias_val = alias.default if isinstance(alias, FieldInfo) else alias
    _type_val = type.default if isinstance(type, FieldInfo) else type
    _value_val = value.default if isinstance(value, FieldInfo) else value
    _query_val = query.default if isinstance(query, FieldInfo) else query
    _limit_val = limit.default if isinstance(limit, FieldInfo) else limit

    filters = {}
    if _alias_val is not None:
        filters["alias"] = _alias_val
    if _type_val is not None:
        filters["type"] = _type_val
    if _value_val is not None:
        filters["value"] = _value_val
    
    # --- Lógica para query obligatorio ---
    search_query_text = _query_val if _query_val is not None else ""
    if not search_query_text:
        if _alias_val:
            search_query_text = str(_alias_val)
        else:
            logfire.error("search_memory: No se proporcionó ni query ni alias. La API de Mem0 requiere al menos uno.")
            return SearchMemoryResponse(results=[], status="Debes proporcionar al menos un alias o un query para buscar en memoria.")

    resolved_limit = 3
    if isinstance(_limit_val, int):
        resolved_limit = _limit_val if _limit_val > 0 else 3
    elif _limit_val is not None:
        try:
            resolved_limit = int(_limit_val)
            if resolved_limit <= 0: resolved_limit = 3
        except (ValueError, TypeError):
            logfire.warn(f"Limit parameter '{_limit_val}' could not be cast to int. Defaulting to 3.")
            resolved_limit = 3
            
    try:
        result = mem0_client.search(query=search_query_text, user_id=USER_ID_FIJO, filters=filters, limit=resolved_limit)
        logfire.debug(f"Mem0 client.search() raw result: {result}")
        
        parsed_results_list = []
        actual_mem_list = []
        if isinstance(result, list):
            actual_mem_list = result
        elif isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
            actual_mem_list = result["results"]
        elif isinstance(result, dict) and "hits" in result and isinstance(result["hits"], list):
            actual_mem_list = result["hits"]

        for mem_item in actual_mem_list:
            if not isinstance(mem_item, dict): 
                logfire.warn(f"Skipping non-dict item in search results: {mem_item}")
                continue
            meta = mem_item.get("metadata", {})
            if not isinstance(meta, dict): 
                logfire.warn(f"Metadata for memory {mem_item.get('id')} is not a dict, skipping. Meta: {meta}")
                meta = {}
            
            alias_val = meta.get("alias")
            value_val = meta.get("value")

            # Only proceed if both alias and value are present and not empty
            if alias_val and value_val:
                parsed_results_list.append(MemoryResult(
                    memory_id=str(mem_item.get("id", "")),
                    alias=str(alias_val),
                    value=str(value_val),
                    type=str(meta.get("type")) if meta.get("type") is not None else None,
                    context=str(meta.get("context")) if meta.get("context") is not None else None,
                    extra={k: v for k, v in meta.items() if k not in {"alias", "value", "type", "context"}}
                ))
        return SearchMemoryResponse(results=parsed_results_list, status="ok")
    except Exception as e:
        logfire.error(f"Error during mem0_client.search or processing its results: {e}", exc_info=True)
        return SearchMemoryResponse(results=[], status=f"Error searching memory: {str(e)}")

# --- Pruebas manuales (Enhanced) ---
if __name__ == "__main__":
    import asyncio

    # Setup basic logfire for local testing output if not already configured elsewhere
    # logfire.configure(pydantic_plugin=logfire.PydanticPlugin(include_models=True))
    # logfire.instrument_httpx()

    async def main():
        print(f"--- Mem0 Tools Test Script ---")
        print(f"Using fixed User ID: {USER_ID_FIJO}")
        print(f"MEM0_API_KEY found: {bool(MEM0_API_KEY)}")
        print(f"OPENAI_API_KEY found: {bool(OPENAI_API_KEY)}")
        print(f"mem0_client initialized: {bool(mem0_client)}")

        if not mem0_client:
            print("\nSkipping tests: mem0_client is not initialized. \nPlease set MEM0_API_KEY or ensure OPENAI_API_KEY is set and allows fallback initialization for Mem0.")
            return

        test_alias = "my_jira_space_alias"
        test_value = "PSIMDESASW_TEST"
        test_type = "jira_space_config"
        test_context = "Primary JIRA space for software development testing."
        test_extra = {"priority": "high", "related_ticket": "JIRA-123"}

        print("\n--- Test 1: Save memory (all fields) ---")
        save_resp_full = await save_memory(
            alias=test_alias, 
            value=test_value, 
            type=test_type, 
            context=test_context, 
            extra=test_extra
        )
        print(f"SaveMemoryResponse (full): {save_resp_full}")
        saved_memory_id = save_resp_full.memory_id if save_resp_full.status == "ok" else None

        print("\n--- Test 2: Save memory (only required fields) ---")
        alias_req = "minimal_alias_test"
        value_req = "minimal_value_content"
        save_resp_req = await save_memory(alias=alias_req, value=value_req)
        print(f"SaveMemoryResponse (required only): {save_resp_req}")

        if saved_memory_id and saved_memory_id != "ERROR":
            print(f"\n--- Searching for saved memory (ID: {saved_memory_id}) using various criteria for user {USER_ID_FIJO} ---")

            print("\nTest 3.1: Search by alias...")
            search_alias_resp = await search_memory(alias=test_alias, limit=1)
            print(f"Search by alias response: {search_alias_resp}")
            if search_alias_resp.results: print(f"Found: {search_alias_resp.results[0]}")

            print("\nTest 3.2: Search by type...")
            search_type_resp = await search_memory(type=test_type, limit=1)
            print(f"Search by type response: {search_type_resp}")
            if search_type_resp.results: print(f"Found: {search_type_resp.results[0]}")

            print("\nTest 3.3: Search by semantic query (matching context)...")
            search_query_resp = await search_memory(query="software development testing", limit=1)
            print(f"Search by query response: {search_query_resp}")
            if search_query_resp.results: print(f"Found: {search_query_resp.results[0]}")

            print("\nTest 3.4: Search with query and filter...")
            search_query_filter_resp = await search_memory(query=test_value, type=test_type, limit=1)
            print(f"Search by query+filter response: {search_query_filter_resp}")
            if search_query_filter_resp.results: print(f"Found: {search_query_filter_resp.results[0]}")

            print("\nTest 3.5: Search for non-existent alias...")
            search_no_exist_resp = await search_memory(alias="non_existent_alias_blah")
            print(f"Search non-existent response: {search_no_exist_resp}")
        else:
            print("\nSkipping search tests as initial save_memory failed or did not return a valid ID.")

        print("\n--- Test 4: Search for the minimal memory entry by its alias ---")
        if save_resp_req.status == "ok" and save_resp_req.memory_id != "ERROR":
            search_minimal_resp = await search_memory(alias=alias_req)
            print(f"Search for minimal entry response: {search_minimal_resp}")
            if search_minimal_resp.results: print(f"Found: {search_minimal_resp.results[0]}")
        else:
            print("Skipping search for minimal entry as its save failed.")
            
        print("\n--- All tests completed ---")

    asyncio.run(main())

async def precargar_memoria_completa_usuario(limit: int = 100) -> SearchMemoryResponse:
    """
    Función específica para precargar toda la memoria del usuario al iniciar la app.
    Usa una búsqueda genérica para traer todos los alias guardados.
    """
    if not mem0_client:
        logfire.warn("precargar_memoria_completa_usuario called but mem0_client is not initialized.")
        return SearchMemoryResponse(results=[], status="Mem0 client not initialized.")
    
    try:
        # Usar una búsqueda genérica que probablemente coincida con muchas memorias
        # Intentamos con diferentes queries hasta que uno funcione
        queries_to_try = [
            "alias",  # Buscar por la palabra "alias" que debería estar en muchas memorias
            "proyecto",  # Otra palabra común
            " ",  # Espacio simple
            "",   # String vacío (si Mem0 lo permite)
        ]
        
        for query_attempt in queries_to_try:
            try:
                result = mem0_client.search(
                    query=query_attempt, 
                    user_id=USER_ID_FIJO, 
                    filters={}, 
                    limit=limit
                )
                logfire.debug(f"precargar_memoria_completa_usuario with query '{query_attempt}' - raw result: {result}")
                
                parsed_results_list = []
                actual_mem_list = []
                if isinstance(result, list):
                    actual_mem_list = result
                elif isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
                    actual_mem_list = result["results"]
                elif isinstance(result, dict) and "hits" in result and isinstance(result["hits"], list):
                    actual_mem_list = result["hits"]

                for mem_item in actual_mem_list:
                    if not isinstance(mem_item, dict): 
                        continue
                    meta = mem_item.get("metadata", {})
                    if not isinstance(meta, dict): 
                        meta = {}
                    
                    alias_val = meta.get("alias")
                    value_val = meta.get("value")

                    # Only proceed if both alias and value are present and not empty
                    if alias_val and value_val:
                        parsed_results_list.append(MemoryResult(
                            memory_id=str(mem_item.get("id", "")),
                            alias=str(alias_val),
                            value=str(value_val),
                            type=str(meta.get("type")) if meta.get("type") is not None else None,
                            context=str(meta.get("context")) if meta.get("context") is not None else None,
                            extra={k: v for k, v in meta.items() if k not in {"alias", "value", "type", "context"}}
                        ))
                
                logfire.info(f"precargar_memoria_completa_usuario: Cargados {len(parsed_results_list)} alias válidos para el usuario.")
                return SearchMemoryResponse(results=parsed_results_list, status="ok")
                
            except Exception as query_error:
                logfire.debug(f"Query '{query_attempt}' failed: {query_error}")
                continue
        
        # Si todos los queries fallaron
        logfire.warn("precargar_memoria_completa_usuario: Todos los queries genéricos fallaron. Retornando memoria vacía.")
        return SearchMemoryResponse(results=[], status="No se pudo cargar la memoria - todos los queries fallaron")
        
    except Exception as e:
        logfire.error(f"Error during precargar_memoria_completa_usuario: {e}", exc_info=True)
        return SearchMemoryResponse(results=[], status=f"Error cargando memoria: {str(e)}") 