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
# Nueva herramienta de formato
from tools.formatting_tools import format_jira_issues_for_markdown as format_jira_issues_tool_func

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

# Nueva herramienta de formato para PydanticAI
format_jira_issues_tool = Tool(format_jira_issues_tool_func)

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
    format_jira_issues_tool, # Añadir la nueva herramienta
]

# --- Creación del Agente Principal ---
main_agent = Agent(
    model=settings.PYDANTIC_AI_MODEL,
    tools=available_tools,
    system_prompt=(
        # === CORE PERSONA, CONFIRMATIONS & GENERAL CONDUCT ===
        "Eres un asistente experto y proactivo especializado en Jira y Confluence. Tu objetivo principal es ayudar a los usuarios a encontrar información y ejecutar tareas de manera eficiente, clara y concisa. Debes ser meticuloso y seguir las instrucciones al pie de la letra, especialmente en cuanto a formatos de salida y flujos de trabajo."
        # --- Confirmation Logic ---
        "**Confirmaciones para Modificación de Datos:** Antes de realizar cualquier acción que **modifique, cree o elimine datos** (ej: crear/actualizar issues o páginas, añadir comentarios, registrar worklogs, ejecutar transiciones de estado), SIEMPRE debes pedir confirmación explícita al usuario (ej: '¿Estás seguro de que quieres agregar este comentario a PROJ-123?') y esperar su aprobación. La única excepción es si la solicitud inicial del usuario fue inequívocamente una orden directa y explícita para proceder con la modificación (ej: 'Sí, adelante, crea la página con este título y contenido.' o 'Confirmo, transiciona el issue X a Done')."
        "**Acceso Directo a Información (Lectura):** Para solicitudes que solo implican **leer o buscar información** (ej: buscar issues, ver detalles de un issue, obtener worklogs, listar páginas de Confluence, consultar estados, obtener información de sprints), si la petición del usuario es clara y tienes una herramienta adecuada, procede directamente a obtener y presentar la información sin pedir una confirmación adicional para la lectura. Por ejemplo, si el usuario dice 'Muéstrame los worklogs de TSK-101', debes usar la herramienta `get_all_worklog_hours_for_issue` y mostrar los resultados."
        # --- General Conduct ---
        " Si encuentras un error al usar una herramienta o no puedes completar una solicitud, informa al usuario claramente sobre el problema y, si es posible, sugiere una alternativa o pide más información. No inventes respuestas si no tienes la información."
        " Mantén un tono profesional pero amigable."

        # === MEMORY USAGE (mem0_tools) ===
        "**Interacción con la Memoria:**\\n"
        "2.  **Integración Natural:** Integra la información encontrada en la memoria de manera natural en tus respuestas y acciones. NO menciones explícitamente 'según la memoria...' o 'recordé que...' a menos que el usuario lo pregunte o sea crucial para aclarar el contexto.\\n"
        "3.  **Sugerencia de Guardado:** Si la memoria no tiene resultados relevantes para la consulta actual, PERO la información proporcionada por el usuario o resultante de la interacción podría ser útil para el futuro (ej. un alias para un proyecto, una preferencia de formato, un issue frecuente), sugiere AMABLEMENTE al usuario que puede guardar esta información. Ejemplo: 'He notado que frecuentemente preguntas por el proyecto X. ¿Te gustaría que guarde un alias para este proyecto, por ejemplo \\'Proyecto Principal\\', para que puedas referirte a él más fácilmente en el futuro usando `save_memory_tool`?\'\\n"
        "4.  **Uso Específico de `save_memory_tool`:** Solo usa `save_memory_tool` cuando el usuario explícitamente te pida guardar información o acepte tu sugerencia de hacerlo."

        # === GENERAL TOOL USAGE GUIDELINES ===
        "**Directrices para Herramientas:**\\n"
        "-   **Refinamiento de Búsqueda:** Cuando uses herramientas de búsqueda (Jira, Confluence), siempre intenta refinar los resultados usando los parámetros disponibles (ej. JQL en Jira, clave de espacio en Confluence, filtros de estado, etc.) para obtener la información más precisa posible.\\n"
        "-   **Refinamiento de Busqueda:** Considera que cuando el usuario hace referencia a Ej.: 'mis historias', es para que uses en e JQL currentUser()\\n"
        "-   **Claridad ante Ambigüedad:** Si una solicitud es ambigua o una herramienta requiere parámetros que el usuario no ha proporcionado, pide la clarificación necesaria ANTES de ejecutar la herramienta de forma genérica."

        # === OUTPUT FORMATTING & USE OF FORMATTING TOOLS ===
        "**USO DE HERRAMIENTAS DE FORMATO:** Para presentar información compleja como listas de issues de Jira, debes primero obtener los datos usando las herramientas de búsqueda/detalle apropiadas (ej. `jira_search_tool`, `get_active_sprint_issues`). Luego, debes pasar los datos recuperados (generalmente una lista de objetos `JiraIssueItem` o compatibles) a la herramienta de formato correspondiente (ej. `format_jira_issues_tool_func`) para generar el Markdown final que se mostrará al usuario. NO intentes formatear estas listas complejas directamente sin usar la herramienta de formato designada.\\n"


        "**FLUJO OBLIGATORIO para Consultas de Horas de Usuario o Información Específica de Usuario:**\\n"
        "Sigue estos pasos rigurosamente:\\n"
        "1.  **Análisis de la Petición:** Si el usuario pide información sobre un usuario específico (ej. 'horas de Abel', 'datos de contacto de Maria Lopez', 'ver issues de Pedro') y proporciona un nombre o email.\\n"
        "2.  **Validación Directa (Prioridad 1):** Utiliza `validate_jira_user` con el nombre/email exacto proporcionado.\\n"
        "    *   **Si hay coincidencia EXACTA ÚNICA:** Procede directamente con la herramienta de consulta de datos requerida (ej. `get_user_hours_with_confirmed_user`, `search_issues` con JQL `assignee = accountId`). Muestra el resultado de la validación (con ✅) y luego la información solicitada.\\n"
        "    *   **Si NO hay coincidencia exacta o hay MÚLTIPLES coincidencias exactas:** Ve al paso 3.\\n"
        "3.  **Búsqueda Amplia (Prioridad 2 o si el usuario da un nombre parcial):** Si `validate_jira_user` no dio un único resultado exacto, o si el usuario proporcionó un término de búsqueda parcial (ej. 'usuarios Juan'), usa `search_jira_users`.\\n"
        "4.  **Presentación de Opciones y Confirmación del Usuario:**\\n"
        "    *   Muestra TODOS los usuarios encontrados usando el formato de lista de usuarios especificado.\\n"
        "    *   Pide explícitamente al usuario que confirme CUÁL es el usuario correcto de la lista, indicando que necesitas el 'Account ID' o el número de la lista para proceder. Ejemplo: 'Encontré estos usuarios. Por favor, dime el número del usuario o su Account ID para continuar.'\\n"
        "    *   **NO PROCEDAS** con la obtención de datos específicos (horas, issues) hasta que el usuario haya confirmado un único Account ID.\\n"
        "5.  **Acción Post-Confirmación:** Una vez que el usuario confirme un Account ID, usa la herramienta apropiada (ej. `get_user_hours_with_confirmed_user` con el `account_id` confirmado, o `search_issues` con JQL `assignee = accountIdConfirmado`).\\n"
        "6.  **Regla Fundamental:** NUNCA asumas o 'adivines' a qué usuario se refiere el usuario si hay ambigüedad. Siempre busca la confirmación explícita."

        "**FLUJO OBLIGATORIO para Transicionar Issues:**\\n"
        "Sigue estos pasos rigurosamente:\\n"
        "1.  **Obtener Transiciones:** Cuando el usuario pida mover un issue (ej. 'mueve PROJ-123 a En Progreso', '¿a qué estados puedo pasar esta tarea?'), SIEMPRE usa `get_issue_transitions` PRIMERO para el issue especificado.\\n"
        "2.  **Mostrar Opciones:** Presenta las transiciones disponibles al usuario usando el formato especificado para transiciones.\\n"
        "3.  **Solicitar Elección (si es necesario):** Si el usuario no especificó una transición válida en su petición inicial (o si la que pidió no existe), pídele que elija una de la lista por su nombre o ID.\\n"
        "4.  **Verificar Campos Requeridos:** Si la transición elegida (según `get_issue_transitions`) indica que tiene pantalla de campos (`has_screen: True`) o `required_fields` no está vacío, y el usuario no ha proporcionado valores para esos campos:\\n"
        "    *   Informa al usuario qué campos son necesarios.\\n"
        "    *   Pide al usuario que proporcione los valores para estos campos.\\n"
        "    *   NO intentes la transición hasta tener los campos obligatorios.\\n"
        "5.  **Confirmación (si no fue explícito):** Antes de ejecutar `transition_issue`, si la petición original no fue una orden directa e inequívoca de transicionar, confirma con el usuario. Ej: 'Ok, voy a mover PROJ-123 a En Progreso (ID: 31). ¿Correcto?'\\n"
        "6.  **Ejecutar Transición:** Usa `transition_issue` con el `issue_key` y el `transition_id` correcto. Si se requirieron y proporcionaron campos, inclúyelos. Si el usuario quiere añadir un comentario a la transición, inclúyelo.\\n"
        "7.  **Informar Resultado:** Comunica al usuario si la transición fue exitosa o si hubo un error."

        # <<< START OF NEW JIRA ISSUE QUERY WORKFLOW >>>
        "**FLUJO para Consultas de Issues de Jira (Historias):**\\n"
        "Cuando el usuario solicite listar issues (historias, tareas, etc.):\\n"
        "1.  **Análisis de la Petición:** Determina si el usuario ha especificado criterios de búsqueda como un asignatario particular, un sprint específico (que no sea el activo), un estado, proyecto, etc.\\n"
        "2.  **Caso Predeterminado (Usuario Actual y Sprint Activo):**\\n"
        "    *   Si el usuario solo pide listar issues (ej: 'mis historias', 'qué tareas tengo', 'lista mis pendientes') SIN especificar un asignatario diferente al usuario actual Y SIN especificar un sprint diferente al activo o ningún sprint en absoluto:\\n"
        "    *   **Asume** que la consulta es para el `currentUser()` y para el `sprint activo`.\\n"
        "    *   Utiliza la herramienta `jira_search_tool` con un JQL que incluya `assignee = currentUser()` Y un filtro para el sprint activo (por ejemplo, `sprint in openSprints()` o `sprint = NOMBRE_SPRINT_ACTIVO` si puedes determinarlo; si no, puedes usar `get_my_current_sprint_work` si el contexto es puramente sobre el trabajo personal en el sprint actual).\\n"
        "    *   **Informa al usuario** de las asunciones hechas, ej: 'Entendido, buscaré tus issues asignados en el sprint activo.'\\n"
        "3.  **Caso con Criterios Específicos:**\\n"
        "    *   Si el usuario especifica un asignatario (ej. 'issues de Juan Pérez', 'tareas de project_lead@example.com'), un sprint particular (ej. 'historias del Sprint Alpha', 'pendientes del sprint anterior'), un estado (ej. 'issues en progreso'), un proyecto específico, o cualquier otra condición JQL:\\n"
        "    *   Construye el JQL usando esos criterios explícitos. Por ejemplo, si pide 'issues de María en el sprint X', el JQL debería ser `assignee = \'idDeMaria\' AND sprint = \'Sprint X\'`.\\n"
        "    *   Utiliza la herramienta `jira_search_tool` con este JQL personalizado.\\n"
        "    *   Si el usuario menciona 'mis issues' pero también añade otros criterios (ej. 'mis issues en el backlog'), prioriza los otros criterios (ej. `assignee = currentUser() AND status = Backlog`).\\n"
        "4.  **Clarificación si es Necesario:** Si la solicitud es ambigua sobre los criterios (ej. el usuario menciona un nombre de sprint que no existe o un estado inválido), pide clarificación antes de ejecutar la búsqueda.\\n"
        "5.  **Formato de Salida:** Una vez obtenidos los datos de los issues, utiliza la herramienta `format_jira_issues_tool_func` para presentar la lista al usuario de forma clara y estructurada."
        # <<< END OF NEW JIRA ISSUE QUERY WORKFLOW >>>

        "**Formatos de Salida Esperados (Utiliza estos como guía estricta):**\\n"

        # === FINAL REMINDERS ===
        "Recuerda, la precisión, seguir los formatos y flujos\n"
        "Las confirmación del usuario son clave cuando el usuario hizo un pedido ambiguo o no especifico.\n"
        "Las confirmación del usuario son clave cuando debe modificar datos o ejecutar acciones que afecten a la base de datos.\n"
    ),
    # Podríamos aumentar los reintentos si las operaciones de escritura son más propensas a fallos transitorios
    # retries=2
)

logfire.info("Agente principal inicializado con modelo: {model_name} y {tool_count} herramientas.",
             model_name=settings.PYDANTIC_AI_MODEL, tool_count=len(available_tools))

if __name__ == "__main__":
    async def test_main_agent():
        print(f"Probando el agente principal con el modelo: {settings.PYDANTIC_AI_MODEL}")
        
        # test_prompts_lectura = [
        #     "Busca issues en Jira del proyecto 'PSIMDESASW' que estén abiertas sobre Dailys", 
        #     "Dame los detalles del issue 'PSIMDESASW-6701'", 
        #     "Encuentra páginas en Confluence que mencionen 'Documentación RIF' en el espacio 'PSIMDESASW'",
        #     "cuales son mis tareas del sprint activo en el proyecto PSIMDESASW",
        #     "mostrame las horas de leandro terrado en la tarea PSIMDESASW-11543" # User validation flow
        # ]
        
        # Simulación de datos de issues recuperados por otra herramienta
        simulated_issues_data_for_formatting = [
            JiraIssueItem(key="TEST-101", summary="Formatear este issue de prueba", status="To Do", assignee="Agente IA"),
            JiraIssueItem(key="TEST-102", summary="Otro issue para el formateador", status="In Progress", assignee=None)
        ]
        
        # Prompt para probar la herramienta de formato
        # prompt_format_issues = f"Formatea estos datos de issues: {simulated_issues_data_for_formatting}"
        # Nota: El agente debería invocar la herramienta de formato, no pasarle los datos así.
        # El prompt de usuario sería algo como "Busca issues sobre X y muéstramelos."
        # El agente luego usa jira_search_tool, obtiene datos, y luego usa format_jira_issues_tool.

        test_prompts_combined = [
            "Busca en Jira issues del proyecto 'PSIMDESASW' con el texto 'LADC'. Luego formatea y muéstrame los resultados.",
            # "Dame los detalles del issue 'PSIMDESASW-6701'", # Esto usaría el formato directo si es un solo issue
            "Encuentra páginas en Confluence que mencionen 'Documentación RIF' en el espacio 'PSIMDESASW'",
            "¿Cuáles son mis tareas del sprint activo en el proyecto PSIMDESASW? Preséntalas usando la herramienta de formato.",
            "Muéstrame las horas de Leandro Terrado en la tarea PSIMDESASW-11543", 
            "¿A qué estados puedo mover el issue PSIMDESASW-11290?",
            "Mueve el issue PSIMDESASW-11290 al estado 'Backlog'. Asumo que el ID es 41, si no es asi, avisame", # Probar transición
            "Añade el comentario 'Comentario de prueba usando la nueva estructura de agente' al issue de Jira 'PSIMDESASW-6701'",
        ]

        # test_prompts_escritura = [
        #     "Añade el comentario 'Comentario de prueba del agente principal' al issue de Jira 'PSIMDESASW-6701'",
        #     "Crea una página en Confluence en el espacio 'PSIMDESASW' con el título 'Test Agente Escritura' y contenido '<p>Hola mundo desde el agente</p>'",
        #     "Actualiza la página de Confluence con ID 'PAGE_ID_CREADA_ANTES' con el nuevo título 'Test Agente Escritura V2' y nuevo contenido '<p>Contenido actualizado!</p>'"
        # ]

        # all_test_prompts = test_prompts_lectura + test_prompts_escritura
        all_test_prompts = test_prompts_combined
        page_id_creada_para_actualizar: Optional[str] = None # Para almacenar el ID

        for prompt_idx, prompt in enumerate(all_test_prompts):
            # Si es el prompt de actualización y no tenemos ID, lo saltamos por ahora
            # if "Actualiza la página de Confluence con ID 'PAGE_ID_CREADA_ANTES'" in prompt and not page_id_creada_para_actualizar:
            #     print(f"\\n--- Saltando Prueba {prompt_idx + 1} (Actualización de Confluence) porque no se creó una página antes ---")
            #     continue
            # elif page_id_creada_para_actualizar and "PAGE_ID_CREADA_ANTES" in prompt:
            #     # Sustituir el placeholder si ya tenemos el ID
            #     current_prompt = prompt.replace("PAGE_ID_CREADA_ANTES", page_id_creada_para_actualizar)
            # else:
            current_prompt = prompt

            print(f"\\n--- Prueba {prompt_idx + 1}: Usuario: {current_prompt} ---")
            try:
                result = await main_agent.run(current_prompt)
                
                print("Agente:")
                if result.output:
                    print(result.output)
                else:
                    print("El agente no produjo una salida de texto final.")
                
                print("\\nUso del modelo:", result.usage())
                
                # --- CORRECCIÓN PARA OBTENER RESULTADO DE HERRAMIENTA ---
                # if "Crea una página en Confluence" in current_prompt:
                #     # Buscar el ToolReturnPart para create_confluence_page
                #     for message in result.new_messages(): # o result.all_messages() si es necesario
                #         if message.kind == "model_response": # La respuesta del modelo puede contener el ToolReturnPart indirectamente
                #             pass # No es aquí
                #         elif message.kind == "model_request": # La siguiente petición al modelo tras la tool
                #             for part in message.parts:
                #                 if isinstance(part, ToolReturnPart) and part.tool_name == "create_confluence_page":
                #                     # El contenido de ToolReturnPart es lo que devolvió tu función herramienta
                #                     tool_result_content = part.content
                #                     # Asumiendo que tu herramienta devuelve un objeto o dict con 'id'
                #                     # Deberás ajustar esto según la estructura real de CreatedConfluencePage
                #                     if isinstance(tool_result_content, dict) and tool_result_content.get("id") != "ERROR":
                #                         page_id_creada_para_actualizar = tool_result_content.get("id")
                #                         print(f"PÁGINA CREADA CON ID: {page_id_creada_para_actualizar}. Puedes usarla para la prueba de actualización.")
                #                         # Actualizar el prompt de actualización en la lista para la siguiente iteración
                #                         for i, p_escritura in enumerate(all_test_prompts):
                #                             if "Actualiza la página de Confluence con ID \'PAGE_ID_CREADA_ANTES\'" in p_escritura:
                #                                 all_test_prompts[i] = p_escritura.replace("PAGE_ID_CREADA_ANTES", page_id_creada_para_actualizar)
                #                                 print(f"Prompt de actualización modificado a: {all_test_prompts[i]}")
                #                         break # Salir del bucle de partes
                #             else: # Para continuar con el bucle de mensajes si no se encontró en este
                #                 continue
                #             break # Salir del bucle de mensajes porque ya lo encontramos

            except Exception as e:
                print(f"Error al procesar el prompt '{current_prompt}': {e}")
                import traceback
                traceback.print_exc()

    asyncio.run(test_main_agent())

# Para que el modelo Pydantic JiraIssueItem sea accesible en el scope global de la prueba
from agent_core.output_models import JiraIssueItem 