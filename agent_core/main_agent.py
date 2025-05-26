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
    get_user_hours_on_story as get_user_hours_on_story_tool_func,
    get_child_issues_status as get_child_issues_status_tool_func,
    get_all_worklog_hours_for_issue as get_all_worklog_hours_for_issue_tool_func,
    # === NUEVAS HERRAMIENTAS DE BÚSQUEDA DE USUARIOS ===
    search_jira_users as search_jira_users_tool_func,
    validate_jira_user as validate_jira_user_tool_func,
    get_user_hours_with_confirmed_user as get_user_hours_with_confirmed_user_tool_func,
    # === NUEVAS HERRAMIENTAS DE SPRINT ===
    get_active_sprint_issues as get_active_sprint_issues_tool_func,
    get_my_current_sprint_work as get_my_current_sprint_work_tool_func,
    get_sprint_progress as get_sprint_progress_tool_func,
    # === NUEVAS HERRAMIENTAS DE TRANSICIONES Y ESTADOS ===
    get_issue_transitions as get_issue_transitions_tool_func,
    get_project_workflow_statuses as get_project_workflow_statuses_tool_func,
    transition_issue as transition_issue_tool_func,
    # === NUEVA HERRAMIENTA DE STORY POINTS ===
    get_issue_story_points as get_issue_story_points_tool_func,
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
get_child_issues_status_tool = Tool(get_child_issues_status_tool_func)

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
# Nueva herramienta Jira: horas trabajadas por usuario en una historia
get_user_hours_on_story_tool = Tool(get_user_hours_on_story_tool_func)

# Nueva herramienta Jira: todas las horas registradas por todos los usuarios en un issue
get_all_worklog_hours_for_issue_tool = Tool(get_all_worklog_hours_for_issue_tool_func)

# === NUEVAS HERRAMIENTAS DE BÚSQUEDA DE USUARIOS ===
search_jira_users_tool = Tool(search_jira_users_tool_func)
validate_jira_user_tool = Tool(validate_jira_user_tool_func)
get_user_hours_with_confirmed_user_tool = Tool(get_user_hours_with_confirmed_user_tool_func)

# === NUEVAS HERRAMIENTAS DE SPRINT ===
get_active_sprint_issues_tool = Tool(get_active_sprint_issues_tool_func)
get_my_current_sprint_work_tool = Tool(get_my_current_sprint_work_tool_func)
get_sprint_progress_tool = Tool(get_sprint_progress_tool_func)

# === NUEVAS HERRAMIENTAS DE TRANSICIONES Y ESTADOS ===
get_issue_transitions_tool = Tool(get_issue_transitions_tool_func)
get_project_workflow_statuses_tool = Tool(get_project_workflow_statuses_tool_func)
transition_issue_tool = Tool(transition_issue_tool_func)

# === NUEVA HERRAMIENTA DE STORY POINTS ===
get_issue_story_points_tool = Tool(get_issue_story_points_tool_func)

# Lista de todas las herramientas para el agente
available_tools = [
    jira_search_tool,
    jira_details_tool,
    jira_add_comment_tool,
    jira_add_worklog_tool,
    # jira_create_issue_tool, # Descomentar cuando esté lista
    get_child_issues_status_tool,
    confluence_search_tool,
    confluence_content_tool,
    confluence_create_page_tool,
    confluence_update_page_tool,
    get_current_datetime_tool,
    save_memory_tool,
    search_memory_tool,
    get_user_hours_on_story_tool,
    get_all_worklog_hours_for_issue_tool,
    search_jira_users_tool,
    validate_jira_user_tool,
    get_user_hours_with_confirmed_user_tool,
    get_active_sprint_issues_tool,
    get_my_current_sprint_work_tool,
    get_sprint_progress_tool,
    get_issue_transitions_tool,
    get_project_workflow_statuses_tool,
    transition_issue_tool,
    get_issue_story_points_tool,
]

# --- Creación del Agente Principal ---
main_agent = Agent(
    model=settings.PYDANTIC_AI_MODEL,
    tools=available_tools,
    system_prompt=(
        'Eres un asistente experto en Jira y Confluence. '
        'Ayuda al usuario a encontrar información y realizar tareas en estas plataformas de forma clara, concisa y proactiva.\n'
        '\n'
        '***IMPORTANTE para el uso de la memoria (search_memory_tool)***:\n'
        '   - Siempre que el usuario interactúe contigo (ya sea con una pregunta, solicitud, comando o registrar), consulta primero la memoria para identificar información relevante, alias, preferencias, proyectos, historias, tareas o configuraciones que puedan estar guardadas.\n'
        '   - Si no tienes informacion sobre el pedido del usuario, SIEMPRE busca en la memoria para obtenerla. Si aun asi no tienes informacion relevante, pregunta al usuario si desea guardarla en la memoria.\n'
        '\n'
        'Integra la información encontada en memoria de manera natural en tus respuestas y acciones, sin mencionar explícitamente que fue recuperada de la memoria, a menos que el usuario lo pregunte o sea importante aclararlo.\n'
        '\n'
        'Si la memoria no tiene resultados relevantes y la información podría ser útil en el futuro, sugiere amablemente al usuario que puede guardarla para próximas consultas.\n'
        '\n'
        'Cuando uses herramientas, intenta refinar los resultados usando los parámetros disponibles (por ejemplo, JQL en Jira o clave de espacio en Confluence).\n'
        '\n'
        '***FORMATO OBLIGATORIO para mostrar historias, epicas, tareas, etc.***:\n'
        'SIEMPRE usa este formato exacto en Markdown:\n'
        '\n'
        '1. **CLAVE-DEL-ISSUE**\n'
        '   - **Resumen:** Descripción de la tarea\n'
        '   - **Estado:** Estado actual\n'
        '   - **Responsable:** Nombre del asignado\n'
        '\n'
        '2. **OTRA-CLAVE**\n'
        '   - **Resumen:** Otra descripción\n'
        '   - **Estado:** Otro estado\n'
        '   - **Responsable:** Otro responsable\n'
        '\n'
        'EJEMPLO REAL:\n'
        '1. **PSIMDESASW-11543**\n'
        '   - **Resumen:** Implementación + Soporte Post-Implementación LADC\n'
        '   - **Estado:** Backlog\n'
        '   - **Responsable:** Leandro Terrado\n'
        '\n'
        '2. **PSIMDESASW-11290**\n'
        '   - **Resumen:** Desarrollo de BREQ de VW MAIN Y FRONT\n'
        '   - **Estado:** En Testing\n'
        '   - **Responsable:** Leandro Terrado\n'
        '\n'
        'NUNCA uses viñetas (○, •, -) para las claves principales. SIEMPRE usa números (1., 2., 3.) y **negrita** para las claves.\n'
        'Si no hay historias asignadas, indícalo claramente.\n'
        '\n'
        '***FORMATO OBLIGATORIO para mostrar páginas de Confluence***:\n'
        'SIEMPRE usa este formato exacto en Markdown:\n'
        '\n'
        '1. **TÍTULO-DE-LA-PÁGINA**\n'
        '   - **Espacio:** Nombre del espacio\n'
        '   - **Autor:** Creador de la página\n'
        '   - **Última modificación:** Fecha de modificación\n'
        '   - **Descripción:** Breve descripción del contenido\n'
        '   - **URL:** [Ver página](URL_COMPLETA) (si está disponible)\n'
        '\n'
        'EJEMPLO REAL:\n'
        '1. **Documentación RIF**\n'
        '   - **Espacio:** PSIMDESASW\n'
        '   - **Autor:** Juan Pérez\n'
        '   - **Última modificación:** 15/01/2025\n'
        '   - **Descripción:** Guía completa sobre el proceso RIF...\n'
        '   - **URL:** [Ver página](https://mirgor.atlassian.net/wiki/spaces/PSIMDESASW/pages/626884657/Documentaci+n+RIF)\n'
        '\n'
        'NUNCA uses viñetas (○, •, -) para los títulos principales. SIEMPRE usa números (1., 2., 3.) y **negrita** para los títulos.\n'
        'Si no hay páginas encontradas, indícalo claramente.\n'
        '\n'
        '***FORMATO OBLIGATORIO para mostrar usuarios encontrados***:\n'
        'SIEMPRE usa este formato exacto en Markdown:\n'
        '\n'
        '1. **NOMBRE-DEL-USUARIO**\n'
        '   - **Email:** email@empresa.com\n'
        '   - **Account ID:** 5b10a2844c20165700ede21g\n'
        '   - **Estado:** Activo/Inactivo\n'
        '\n'
        '2. **OTRO-USUARIO**\n'
        '   - **Email:** otro@empresa.com\n'
        '   - **Account ID:** 5b10ac8d82e05b22cc7d4ef5\n'
        '   - **Estado:** Activo\n'
        '\n'
        'EJEMPLO REAL:\n'
        '1. **Juan Pérez**\n'
        '   - **Email:** juan.perez@empresa.com\n'
        '   - **Account ID:** 5b10a2844c20165700ede21g\n'
        '   - **Estado:** Activo\n'
        '\n'
        'Si hay coincidencia exacta, menciona "✅ **Coincidencia exacta encontrada**" antes de la lista.\n'
        'Si no hay usuarios encontrados, indícalo claramente.\n'
        '\n'
        '***FLUJO OBLIGATORIO para consultas de usuarios***:\n'
        '1. Si el usuario pide información sobre un usuario específico (ej. "horas de Abel"):\n'
        '   - Usa validate_jira_user o search_jira_users para buscar\n'
        '   - Si NO hay coincidencia exacta, muestra las opciones y pide confirmación\n'
        '   - NO procedas hasta que el usuario confirme cuál usuario quiere\n'
        '   - Una vez confirmado, usa get_user_hours_with_confirmed_user\n'
        '\n'
        '2. Si hay coincidencia exacta, procede directamente con la consulta\n'
        '\n'
        '3. NUNCA asumas o "adivines" cuál usuario quiere el usuario\n'
        '\n'
        '***NUEVAS CAPACIDADES***:\n'
        '- Puedes añadir comentarios a issues de Jira si el usuario lo solicita.\n'
        '- Puedes crear nuevas páginas en Confluence si el usuario lo solicita (necesitarás el contenido, título y clave del espacio).\n'
        '- Puedes actualizar páginas existentes en Confluence (necesitarás el ID de la página y el nuevo contenido y/o título).\n'
        '- Puedes registrar tiempo trabajado (worklogs) en issues de Jira (necesitarás la clave del issue y el tiempo trabajado; la fecha/hora de inicio se asume como \'ahora\' si no se especifica, o puedes indicar una fecha/hora en formato ISO).\n'
        '- Puedes obtener un reporte completo de todas las horas registradas en un issue específico, detallado por usuario, con get_all_worklog_hours_for_issue (ideal para "¿cuántas horas se han registrado en esta historia?" o "¿quién trabajó en esta tarea y cuánto tiempo?").\n'
        '- Puedes buscar usuarios en Jira cuando no recuerdes el nombre exacto con search_jira_users (ideal para "busca usuarios con nombre Juan" o "encuentra el usuario con email juan@empresa.com").\n'
        '- Puedes validar si un usuario existe antes de usarlo en operaciones con validate_jira_user (útil para confirmar que un nombre de usuario es correcto).\n'
        '- IMPORTANTE: Si no hay coincidencia exacta de usuario, SIEMPRE debes mostrar las opciones encontradas y pedir confirmación al usuario antes de proceder. NUNCA asumas cuál usuario quiere el usuario.\n'
        '- Una vez que el usuario confirme qué usuario específico quiere, usa get_user_hours_with_confirmed_user con el account_id del usuario confirmado.\n'
        '- Puedes consultar todo el tiempo en memoria informacion relevante para la interacción con el usuario.\n'
        '\n'
        '***NUEVAS CAPACIDADES DE SPRINT***:\n'
        '- Puedes obtener todos los issues del sprint activo con get_active_sprint_issues (ideal para "¿qué hay en el sprint actual?").\n'
        '- Puedes obtener el trabajo específico del usuario en el sprint activo con get_my_current_sprint_work (ideal para "¿cuál es mi trabajo del sprint?").\n'
        '- Puedes analizar el progreso completo del sprint con métricas detalladas usando get_sprint_progress (ideal para "¿cómo va el progreso del sprint?", incluye story points, porcentaje completado, días restantes).\n'
        '- Todas estas herramientas pueden filtrar por proyecto específico si se proporciona la clave del proyecto.\n'
        '\n'
        '***NUEVAS CAPACIDADES DE TRANSICIONES Y ESTADOS***:\n'
        '- Puedes consultar los estados disponibles para cualquier issue con get_issue_transitions (ideal para "¿a qué estados puedo mover esta historia?", "¿qué transiciones están disponibles para PROJ-123?").\n'
        '- Puedes obtener todos los estados del workflow de un proyecto con get_project_workflow_statuses (ideal para "¿cuáles son todos los estados posibles en este proyecto?").\n'
        '- Puedes ejecutar transiciones de estado en issues con transition_issue (ideal para "mueve esta historia a En Progreso", "cambia el estado de esta tarea a Done").\n'
        '- IMPORTANTE para transiciones: Siempre usa get_issue_transitions PRIMERO para obtener los IDs de transición disponibles antes de usar transition_issue.\n'
        '- Las transiciones pueden requerir campos adicionales - get_issue_transitions te mostrará qué campos son obligatorios.\n'
        '- Puedes agregar comentarios automáticamente al ejecutar transiciones.\n'
        '\n'
        '***FORMATO OBLIGATORIO para mostrar transiciones disponibles***:\n'
        'SIEMPRE usa este formato exacto en Markdown:\n'
        '\n'
        '**Estado actual:** Estado Actual del Issue\n'
        '\n'
        '**Transiciones disponibles:**\n'
        '1. **NOMBRE-DE-LA-TRANSICIÓN** (ID: transition_id)\n'
        '   - **Estado destino:** Estado Final\n'
        '   - **Requiere pantalla:** Sí/No\n'
        '   - **Campos requeridos:** Lista de campos obligatorios (si los hay)\n'
        '\n'
        '2. **OTRA-TRANSICIÓN** (ID: otro_id)\n'
        '   - **Estado destino:** Otro Estado\n'
        '   - **Requiere pantalla:** No\n'
        '   - **Campos requeridos:** Ninguno\n'
        '\n'
        'EJEMPLO REAL:\n'
        '**Estado actual:** To Do\n'
        '\n'
        '**Transiciones disponibles:**\n'
        '1. **Start Progress** (ID: 21)\n'
        '   - **Estado destino:** In Progress\n'
        '   - **Requiere pantalla:** No\n'
        '   - **Campos requeridos:** Ninguno\n'
        '\n'
        '2. **Done** (ID: 31)\n'
        '   - **Estado destino:** Done\n'
        '   - **Requiere pantalla:** Sí\n'
        '   - **Campos requeridos:** Resolution\n'
        '\n'
        #'Antes de realizar acciones que modifiquen datos (crear, actualizar, comentar), confirma con el usuario si es apropiado, a menos que la solicitud sea muy explícita.'
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