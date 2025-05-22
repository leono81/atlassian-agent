# agent_core/main_agent.py
from pydantic_ai import Agent, Tool
from config import settings 
import logfire
import asyncio
from pydantic_ai.messages import ToolReturnPart

# Importar las funciones de herramientas
from tools.jira_tools import (
    search_issues as jira_search_issues_tool_func,
    get_issue_details as jira_get_issue_details_tool_func,
    add_comment_to_jira_issue as jira_add_comment_tool_func,
    add_worklog_to_jira_issue as jira_add_worklog_tool_func,
    # create_jira_issue as jira_create_issue_tool_func # Descomentar cuando esté lista
)
from tools.confluence_tools import (
    search_confluence_pages as conf_search_pages_tool_func,
    get_confluence_page_content as conf_get_page_content_tool_func,
    create_confluence_page as conf_create_page_tool_func,
    update_confluence_page_content as conf_update_page_tool_func,
)
from tools.time_tools import get_current_datetime as get_current_datetime_tool_func
from tools.mem0_tools import save_memory as save_memory_tool_func, search_memory as search_memory_tool_func

# Configuración de Logfire
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent",
    service_version="0.1.0"
)
logfire.instrument_pydantic_ai()
logfire.instrument_pydantic()

# --- Definición de Herramientas para PydanticAI ---
# Jira Tools
jira_search_tool = Tool(jira_search_issues_tool_func)
jira_details_tool = Tool(jira_get_issue_details_tool_func)
jira_add_comment_tool = Tool(jira_add_comment_tool_func)
jira_add_worklog_tool = Tool(jira_add_worklog_tool_func)
# jira_create_issue_tool = Tool(jira_create_issue_tool_func) # Descomentar cuando esté lista

# Confluence Tools
confluence_search_tool = Tool(conf_search_pages_tool_func)
confluence_content_tool = Tool(conf_get_page_content_tool_func)
confluence_create_page_tool = Tool(conf_create_page_tool_func)
confluence_update_page_tool = Tool(conf_update_page_tool_func)

# Time Tools
get_current_datetime_tool = Tool(get_current_datetime_tool_func)

# Mem0 Tools
save_memory_tool = Tool(save_memory_tool_func)
search_memory_tool = Tool(search_memory_tool_func)

# Lista de todas las herramientas para el agente
available_tools = [
    jira_search_tool,
    jira_details_tool,
    jira_add_comment_tool,
    jira_add_worklog_tool,
    # jira_create_issue_tool, # Descomentar cuando esté lista
    confluence_search_tool,
    confluence_content_tool,
    confluence_create_page_tool,
    confluence_update_page_tool,
    get_current_datetime_tool,
    save_memory_tool,
    search_memory_tool,
]

# --- Creación del Agente Principal ---
main_agent = Agent(
    model=settings.PYDANTIC_AI_MODEL,
    tools=available_tools,
    system_prompt=(
        "Eres un asistente experto en Jira y Confluence. "
        "Ayuda al usuario a encontrar información y realizar tareas en estas plataformas. "
        "Sé claro y conciso en tus respuestas. "
        "Antes de usar las herramientas, consulta la memoria para ver si ya hay información relevante guardada. "
        "Cuando busques, intenta usar los parámetros de las herramientas para refinar los resultados si es posible. "
        "Por ejemplo, para Jira, usa JQL específico y para Confluence, puedes usar la clave del espacio si se proporciona.\n"
        "NUEVAS CAPACIDADES:\n"
        "- Ahora puedes AÑADIR COMENTARIOS a issues de Jira si el usuario lo solicita.\n"
        "- Ahora puedes CREAR NUEVAS PÁGINAS en Confluence si el usuario lo solicita. Necesitarás el contenido (en formato de almacenamiento XHTML), el título y la clave del espacio.\n"
        "- Ahora puedes ACTUALIZAR PÁGINAS existentes en Confluence si el usuario lo solicita. Necesitarás el ID de la página y el nuevo contenido (XHTML) y/o el nuevo título.\n"
        "- Ahora puedes REGISTRAR TIEMPO (worklogs) en issues de Jira. Necesitarás la clave del issue y el tiempo trabajado (ej. '2h', '30m', o preferiblemente en segundos). La fecha y hora de inicio se asumirá como 'ahora' si no se especifica, o puedes indicar una fecha/hora en formato ISO.\n"
        "Antes de realizar una acción de escritura (crear, actualizar, comentar), confirma con el usuario si es apropiado, a menos que la solicitud sea muy explícita.\n"
        "\n"
        "IMPORTANTE: Antes de responder preguntas sobre preferencias, configuraciones, datos personales del usuario o información que podría estar guardada, consulta primero la memoria usando la herramienta correspondiente.\n"
        "Si la memoria no tiene resultados relevantes, sugiere al usuario guardar esa información para futuras consultas.\n"
    ),
     # Podríamos aumentar los reintentos si las operaciones de escritura son más propensas a fallos transitorios
    # retries=2 
)

logfire.info("Agente principal inicializado con modelo: {model_name} y {tool_count} herramientas.",
             model_name=settings.PYDANTIC_AI_MODEL, tool_count=len(available_tools))

if __name__ == "__main__":
    async def test_main_agent():
        print(f"Probando el agente principal con el modelo: {settings.PYDANTIC_AI_MODEL}")
        
        test_prompts_lectura = [
            "Busca issues en Jira del proyecto 'PSIMDESASW' que estén abiertas sobre Dailys", 
            "Dame los detalles del issue 'PSIMDESASW-6701'", 
            "Encuentra páginas en Confluence que mencionen 'Documentación RIF' en el espacio 'PSIMDESASW'",
        ]
        
        test_prompts_escritura = [
            "Añade el comentario 'Comentario de prueba del agente principal' al issue de Jira 'PSIMDESASW-6701'",
            "Crea una página en Confluence en el espacio 'PSIMDESASW' con el título 'Test Agente Escritura' y contenido '<p>Hola mundo desde el agente</p>'",
            "Actualiza la página de Confluence con ID 'PAGE_ID_CREADA_ANTES' con el nuevo título 'Test Agente Escritura V2' y nuevo contenido '<p>Contenido actualizado!</p>'"
        ]

        all_test_prompts = test_prompts_lectura + test_prompts_escritura
        page_id_creada_para_actualizar: Optional[str] = None # Para almacenar el ID

        for prompt_idx, prompt in enumerate(all_test_prompts):
            # Si es el prompt de actualización y no tenemos ID, lo saltamos por ahora
            if "Actualiza la página de Confluence con ID 'PAGE_ID_CREADA_ANTES'" in prompt and not page_id_creada_para_actualizar:
                print(f"\n--- Saltando Prueba {prompt_idx + 1} (Actualización de Confluence) porque no se creó una página antes ---")
                continue
            elif page_id_creada_para_actualizar and "PAGE_ID_CREADA_ANTES" in prompt:
                # Sustituir el placeholder si ya tenemos el ID
                current_prompt = prompt.replace("PAGE_ID_CREADA_ANTES", page_id_creada_para_actualizar)
            else:
                current_prompt = prompt

            print(f"\n--- Prueba {prompt_idx + 1}: Usuario: {current_prompt} ---")
            try:
                result = await main_agent.run(current_prompt)
                
                print("Agente:")
                if result.output:
                    print(result.output)
                else:
                    print("El agente no produjo una salida de texto final.")
                
                print("\nUso del modelo:", result.usage())
                
                # --- CORRECCIÓN PARA OBTENER RESULTADO DE HERRAMIENTA ---
                if "Crea una página en Confluence" in current_prompt:
                    # Buscar el ToolReturnPart para create_confluence_page
                    for message in result.new_messages(): # o result.all_messages() si es necesario
                        if message.kind == "model_response": # La respuesta del modelo puede contener el ToolReturnPart indirectamente
                            pass # No es aquí
                        elif message.kind == "model_request": # La siguiente petición al modelo tras la tool
                            for part in message.parts:
                                if isinstance(part, ToolReturnPart) and part.tool_name == "create_confluence_page":
                                    # El contenido de ToolReturnPart es lo que devolvió tu función herramienta
                                    tool_result_content = part.content
                                    if isinstance(tool_result_content, CreatedConfluencePage) and tool_result_content.id != "ERROR":
                                        page_id_creada_para_actualizar = tool_result_content.id
                                        print(f"PÁGINA CREADA CON ID: {page_id_creada_para_actualizar}. Puedes usarla para la prueba de actualización.")
                                        # Actualizar el prompt de actualización en la lista para la siguiente iteración
                                        for i, p_escritura in enumerate(all_test_prompts):
                                            if "Actualiza la página de Confluence con ID 'PAGE_ID_CREADA_ANTES'" in p_escritura:
                                                all_test_prompts[i] = p_escritura.replace("PAGE_ID_CREADA_ANTES", page_id_creada_para_actualizar)
                                                print(f"Prompt de actualización modificado a: {all_test_prompts[i]}")
                                        break # Salir del bucle de partes
                            else: # Para continuar con el bucle de mensajes si no se encontró en este
                                continue
                            break # Salir del bucle de mensajes porque ya lo encontramos

            except Exception as e:
                print(f"Error al procesar el prompt '{current_prompt}': {e}")
                import traceback
                traceback.print_exc()

    asyncio.run(test_main_agent())