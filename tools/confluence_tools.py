# tools/confluence_tools.py
import asyncio
import functools
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo # <--- IMPORTAR FieldInfo

from agent_core.confluence_instances import get_confluence_client
from config import settings
import logfire

def _build_full_confluence_url(relative_url: Optional[str]) -> Optional[str]:
    """
    Construye una URL completa de Confluence usando la URL base del settings.
    Maneja tanto URLs relativas como absolutas y asegura que incluya /wiki/ cuando sea necesario.
    """
    if not relative_url or not settings.CONFLUENCE_URL:
        return relative_url
    
    # Si ya es una URL completa, devolverla tal como está
    if relative_url.startswith('http'):
        return relative_url
    
    # Construir la URL base
    base_url = settings.CONFLUENCE_URL.rstrip('/')
    
    # Limpiar la URL relativa
    clean_relative = relative_url.lstrip('/')
    
    # Si la URL relativa no empieza con 'wiki/', agregarla
    if not clean_relative.startswith('wiki/'):
        # Si empieza con 'spaces/' o 'pages/', agregar 'wiki/' antes
        if clean_relative.startswith(('spaces/', 'pages/')):
            clean_relative = f"wiki/{clean_relative}"
        # Si no tiene ningún prefijo reconocido, asumir que necesita 'wiki/'
        elif clean_relative and not clean_relative.startswith(('api/', 'rest/')):
            clean_relative = f"wiki/{clean_relative}"
    
    final_url = f"{base_url}/{clean_relative}"
    
    # Log para debugging
    logfire.debug("URL construction: {original} -> {final}", original=relative_url, final=final_url)
    
    return final_url

class ConfluencePage(BaseModel):
    id: str
    title: str
    space_key: Optional[str] = None
    space_name: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    version: Optional[int] = None
    excerpt: Optional[str] = None
    web_url: Optional[str] = None

class ConfluencePageDetails(ConfluencePage):
    body_storage: Optional[str] = None

class CreatedConfluencePage(BaseModel):
    id: str
    title: str
    space_key: Optional[str] = None
    link_web_ui: Optional[str] = Field(default=None, alias="_links_webui")

# ... (search_confluence_pages y get_confluence_page_content sin cambios) ...
# (Asegúrate que están aquí como en la versión anterior que funcionaba)
async def search_confluence_pages(
    query: str = Field(..., description="Término de búsqueda o consulta CQL. Ejemplo CQL: 'space = \"DOCS\" AND title ~ \"tutorial\"'"),
    space_key: Optional[str] = Field(default=None, description="Clave del espacio para limitar la búsqueda (opcional)."),
    max_results: int = 5
) -> List[ConfluencePage]:
    actual_max_results = min(max(1, max_results), 50)
    logfire.info("Ejecutando search_confluence_pages con query: {query}, space: {space_key}, limit: {limit}",
                 query=query, space_key=space_key, limit=actual_max_results)
    # ... (resto del código de search_confluence_pages)
    try:
        confluence = get_confluence_client()
        loop = asyncio.get_running_loop()
        
        is_cql = " = " in query or " ~ " in query or " order by " in query.lower() 

        cql_to_execute = query
        if is_cql:
            if space_key:
                if not (f"space = \"{space_key}\"" in cql_to_execute or f"space = '{space_key}'" in cql_to_execute):
                    cql_to_execute = f"(space = \"{space_key}\") AND ({cql_to_execute})"
        else: 
            cql_to_execute = f"text ~ \"{query}\""
            if space_key:
                cql_to_execute = f"(space = \"{space_key}\") AND ({cql_to_execute})"
        
        search_endpoint = f"rest/api/content/search?cql={cql_to_execute}&limit={actual_max_results}&expand=space,history.lastUpdated,history.createdBy,version,excerpt,_links.webui"

        with logfire.span("confluence.cql_search", cql=cql_to_execute, limit=actual_max_results):
            results_raw = await loop.run_in_executor(None, lambda: confluence.get(search_endpoint))

        pages_found: List[ConfluencePage] = []
        if results_raw and results_raw.get("results"):
            for page_data in results_raw["results"]:
                space_info = page_data.get("space", {})
                history_info = page_data.get("history", {})
                created_by_info = history_info.get("createdBy", {})
                last_updated_info = history_info.get("lastUpdated", {})
                version_info = page_data.get("version", {})
                links_info = page_data.get("_links", {})
                
                # Extraer excerpt y limpiar HTML básico
                raw_excerpt = page_data.get("excerpt", "")
                clean_excerpt = None
                if raw_excerpt:
                    # Remover tags HTML básicos para mostrar texto limpio
                    import re
                    clean_excerpt = re.sub(r'<[^>]+>', '', raw_excerpt).strip()
                    if len(clean_excerpt) > 150:
                        clean_excerpt = clean_excerpt[:150] + "..."
                
                pages_found.append(
                    ConfluencePage(
                        id=page_data.get("id"),
                        title=page_data.get("title"),
                        space_key=space_info.get("key") if space_info else None,
                        space_name=space_info.get("name") if space_info else None,
                        author=created_by_info.get("displayName") if created_by_info else None,
                        created_date=history_info.get("createdDate"),
                        modified_date=last_updated_info.get("when") if last_updated_info else None,
                        version=version_info.get("number") if version_info else None,
                        excerpt=clean_excerpt,
                        web_url=_build_full_confluence_url(links_info.get("webui")) if links_info else None
                    )
                )
        logfire.info("search_confluence_pages encontró {count} páginas.", count=len(pages_found))
        return pages_found
    except Exception as e:
        logfire.error("Error en search_confluence_pages: {error_message}", error_message=str(e), exc_info=True)
        return [ConfluencePage(id="ERROR", title=f"Error al buscar páginas: {str(e)}")]


async def get_confluence_page_content(
    page_id: str = Field(..., description="El ID de la página de Confluence.")
) -> ConfluencePageDetails:
    logfire.info("Ejecutando get_confluence_page_content para page_id: {page_id}", page_id=page_id)
    # ... (resto del código de get_confluence_page_content)
    try:
        confluence = get_confluence_client()
        loop = asyncio.get_running_loop()
        with logfire.span("confluence.page_content", page_id=page_id):
            page_data = await loop.run_in_executor(None, lambda: confluence.get_page_by_id(page_id, expand="body.storage,space,version,history.lastUpdated,history.createdBy,_links.webui"))
        
        if not page_data:
            return ConfluencePageDetails(id=page_id, title=f"No se encontró la página con ID {page_id}")

        space_info = page_data.get("space", {})
        body_info = page_data.get("body", {}).get("storage", {})
        history_info = page_data.get("history", {})
        created_by_info = history_info.get("createdBy", {})
        last_updated_info = history_info.get("lastUpdated", {})
        version_info = page_data.get("version", {})
        links_info = page_data.get("_links", {})
        
        details = ConfluencePageDetails(
            id=page_data.get("id"),
            title=page_data.get("title"),
            space_key=space_info.get("key") if space_info else None,
            space_name=space_info.get("name") if space_info else None,
            author=created_by_info.get("displayName") if created_by_info else None,
            created_date=history_info.get("createdDate"),
            modified_date=last_updated_info.get("when") if last_updated_info else None,
            version=version_info.get("number") if version_info else None,
            excerpt=None,  # No necesitamos excerpt para detalles completos
            web_url=_build_full_confluence_url(links_info.get("webui")) if links_info else None,
            body_storage=body_info.get("value") if body_info else None
        )
        logfire.info("get_confluence_page_content obtuvo contenido para {page_id}", page_id=page_id)
        return details
    except Exception as e:
        logfire.error("Error en get_confluence_page_content para {page_id}: {error_message}", 
                      page_id=page_id, error_message=str(e), exc_info=True)
        return ConfluencePageDetails(id=page_id, title=f"Error al obtener contenido: {str(e)}")


async def create_confluence_page(
    space_key: str = Field(..., description="La clave del espacio donde crear la página (ej. 'DOCS')."),
    title: str = Field(..., description="El título de la nueva página."),
    body_content_storage: str = Field(..., description="El contenido de la página en formato de almacenamiento de Confluence (XHTML)."),
    parent_id: Optional[str] = Field(default=None, description="ID de la página padre bajo la cual crear esta página (opcional).")
) -> CreatedConfluencePage:
    logfire.info("Intentando crear página en espacio {space_key} con título: '{title}'",
                 space_key=space_key, title=title)
    try:
        confluence = get_confluence_client()
        loop = asyncio.get_running_loop()

        # --- CORRECCIÓN para parent_id ---
        actual_parent_id_value: Optional[str]
        if isinstance(parent_id, FieldInfo):
            actual_parent_id_value = parent_id.default # Usar el default del FieldInfo
            logfire.debug("parent_id era FieldInfo, usando default: {default_val}", default_val=actual_parent_id_value)
        else:
            actual_parent_id_value = parent_id # Usar el valor que llegó (que podría ser None o un str)
        
        api_args = {
            "space": str(space_key),
            "title": str(title),
            "body": str(body_content_storage),
            "representation": "storage",
            "type": "page"
        }
        
        if actual_parent_id_value is not None:
            try:
                # La API de Confluence (y por ende la biblioteca) espera el parent_id como un entero para ancestors
                api_args["parent_id"] = int(actual_parent_id_value)
            except ValueError:
                logfire.warning("parent_id '{pid}' no es un entero válido, se omitirá.", pid=actual_parent_id_value)
        
        logfire.debug("Argumentos finales para confluence.create_page: {args}", args=api_args)

        with logfire.span("confluence.create_page_call", **api_args):
            call_func = functools.partial(confluence.create_page, **api_args)
            created_page_data = await loop.run_in_executor(None, call_func)
        
        # ... (resto de la función sin cambios) ...
        if not isinstance(created_page_data, dict) or 'id' not in created_page_data:
            logfire.error("Respuesta inesperada de confluence.create_page: {response_data}", response_data=created_page_data)
            return CreatedConfluencePage(id="ERROR", title="Respuesta inesperada de la API de Confluence al crear página.")

        _links = created_page_data.get('_links', {})
        
        created_page = CreatedConfluencePage(
            id=created_page_data['id'],
            title=created_page_data['title'],
            space_key=space_key, 
            link_web_ui=_build_full_confluence_url(_links.get('webui')) if _links else None
        )

        logfire.info("Página '{title}' (ID: {page_id}) creada exitosamente en espacio {space_key}.",
                     title=created_page.title, page_id=created_page.id, space_key=created_page.space_key)
        return created_page
    except Exception as e:
        logfire.error("Error al crear página en Confluence: {error_message}", error_message=str(e), exc_info=True)
        import traceback
        traceback.print_exc() 
        return CreatedConfluencePage(id="ERROR", title=f"Error al crear página: {str(e)}")


# ... (función update_confluence_page_content y el bloque if __name__ == "__main__": sin cambios)
# Asegúrate de que update_confluence_page_content también tenga este manejo para sus parámetros opcionales
# si se usan con Field(default=...)
async def update_confluence_page_content(
    page_id: str = Field(..., description="El ID de la página de Confluence a actualizar."),
    new_title: Optional[str] = Field(default=None, description="El nuevo título para la página (opcional)."),
    new_body_content_storage: str = Field(..., description="El nuevo contenido completo de la página en formato de almacenamiento (XHTML)."),
    new_version_comment: Optional[str] = Field(default=None, description="Comentario para la nueva versión (opcional).")
) -> CreatedConfluencePage:
    logfire.info("Intentando actualizar contenido de la página ID: {page_id}", page_id=page_id)
    try:
        confluence = get_confluence_client()
        loop = asyncio.get_running_loop()

        # --- CORRECCIÓN para new_title y new_version_comment si son FieldInfo ---
        actual_new_title: Optional[str]
        if isinstance(new_title, FieldInfo):
            actual_new_title = new_title.default
        else:
            actual_new_title = new_title

        actual_new_version_comment: Optional[str]
        if isinstance(new_version_comment, FieldInfo):
            actual_new_version_comment = new_version_comment.default
        else:
            actual_new_version_comment = new_version_comment
        
        # --- Fin Corrección ---

        title_to_update = actual_new_title
        if actual_new_title is None: # Si después de resolver FieldInfo, sigue siendo None, obtener el actual
            with logfire.span("confluence.get_page_title_for_update", page_id=page_id):
                 current_page_data_for_title = await loop.run_in_executor(None, lambda: confluence.get_page_by_id(page_id, expand="title"))
            if not current_page_data_for_title:
                 return CreatedConfluencePage(id=page_id, title=f"Página con ID {page_id} no encontrada para obtener título actual.") # Aquí añadí status antes, lo quito para consistencia
            title_to_update = current_page_data_for_title.get("title")


        update_params = {
            "title": title_to_update,
            "body": str(new_body_content_storage), # Asegurar que body es string
            "representation": "storage",
        }
        if actual_new_version_comment:
            update_params["version_comment"] = actual_new_version_comment
        
        logfire.debug("Argumentos para confluence.update_page (page_id={pid}): {args}", pid=page_id, args=update_params)

        with logfire.span("confluence.update_page_call", page_id=page_id, **update_params):
            call_func = functools.partial(confluence.update_page, page_id, **update_params)
            updated_page_data = await loop.run_in_executor(None, call_func)

        # ... (resto de la función update_confluence_page_content como antes) ...
        if not isinstance(updated_page_data, dict) or 'id' not in updated_page_data:
            logfire.error("Respuesta inesperada de confluence.update_page: {response_data}", response_data=updated_page_data)
            return CreatedConfluencePage(id=page_id, title="Respuesta inesperada de la API de Confluence al actualizar página.")
        
        _links = updated_page_data.get('_links', {})
        
        space_key_from_response = updated_page_data.get("space", {}).get("key")
        if not space_key_from_response: 
            page_info_for_space = await loop.run_in_executor(None, lambda: confluence.get_page_by_id(page_id, expand="space"))
            space_key_from_response = page_info_for_space.get("space", {}).get("key") if page_info_for_space else None


        updated_page = CreatedConfluencePage(
            id=updated_page_data['id'],
            title=updated_page_data['title'],
            space_key=space_key_from_response,
            link_web_ui=_build_full_confluence_url(_links.get('webui')) if _links else None
        )
        logfire.info("Página ID {page_id} actualizada exitosamente a título '{title}'.",
                     page_id=updated_page.id, title=updated_page.title)
        return updated_page
    except Exception as e:
        logfire.error("Error al actualizar página en Confluence (ID: {page_id}): {error_message}",
                      page_id=page_id, error_message=str(e), exc_info=True)
        import traceback
        traceback.print_exc()
        return CreatedConfluencePage(id=page_id, title=f"Error al actualizar página: {str(e)}")


if __name__ == "__main__":
    from config import settings
    import asyncio
    logfire.configure(token=settings.LOGFIRE_TOKEN, send_to_logfire="if-token-present", service_name="confluence_tools_write_test")

    async def test_confluence_write_tools():
        # !! IMPORTANTE: CAMBIA ESTOS VALORES POR DATOS VÁLIDOS EN TU CONFLUENCE DE PRUEBAS !!
        test_space_key = "PSIMDESASW" # Un espacio donde puedas crear páginas
        page_title_for_creation = "Página de Prueba Agente PydanticAI"
        page_content_storage = "<p>Este es el contenido inicial de la página de prueba creada por el agente.</p>"
            
        if test_space_key == "YOUR_TEST_SPACE_KEY":
            print("Por favor, edita 'tools/confluence_tools.py' y cambia 'YOUR_TEST_SPACE_KEY' por una clave de espacio real para probar.")
            return

        created_page: Optional[CreatedConfluencePage] = None
        print(f"\nProbando create_confluence_page en espacio '{test_space_key}'...")
        try:
            created_page_response = await create_confluence_page(
                space_key=test_space_key,
                title=page_title_for_creation,
                body_content_storage=page_content_storage
            )
            if created_page_response.id != "ERROR":
                created_page = created_page_response # Guardar para usar en la actualización
                print(f"Página creada: ID {created_page.id} - Título: '{created_page.title}' - Link: {created_page.link_web_ui}")
            else:
                print(f"Error al crear página: {created_page_response.title}") # title contendrá el mensaje de error

            if created_page and created_page.id != "ERROR":
                print(f"\nProbando update_confluence_page_content para Page ID {created_page.id}...")
                updated_content = "<p>Este es el contenido <strong>actualizado</strong> de la página de prueba.</p>"
                updated_title = f"{page_title_for_creation} (Actualizada)"
                
                updated_page_response = await update_confluence_page_content(
                    page_id=created_page.id,
                    new_title=updated_title,
                    new_body_content_storage=updated_content,
                    new_version_comment="Actualizado por el agente de prueba."
                )
                if updated_page_response.id != "ERROR":
                    print(f"Página actualizada: ID {updated_page_response.id} - Título: '{updated_page_response.title}' - Link: {updated_page_response.link_web_ui}")
                else:
                    print(f"Error al actualizar página: {updated_page_response.title}")
            else:
                print("\nNo se puede probar la actualización sin una página creada exitosamente.")

        except Exception as e:
            print(f"Error durante las pruebas de escritura de Confluence: {e}")
            import traceback
            traceback.print_exc()
            
    asyncio.run(test_confluence_write_tools())
    print("Pruebas de escritura para Confluence comentadas por defecto.")
    print("Descomenta 'asyncio.run(test_confluence_write_tools())' y ajusta los valores de prueba si deseas ejecutar.")