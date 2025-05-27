# tools/formatting_tools.py
import json
from typing import List
from pydantic_ai.direct import model_request_sync
from agent_core.output_models import JiraIssueItem # Asegúrate que la ruta sea correcta
from config import settings # Para usar el mismo modelo LLM

def format_jira_issues_for_markdown(issues_data: List[JiraIssueItem]) -> str:
    """
    Formatea una lista de datos de issues de Jira en una cadena Markdown.
    Esta herramienta llama internamente a un LLM con instrucciones de formato específicas.
    """
    if not issues_data:
        return "No se encontraron issues con los criterios especificados."

    # Convertir los datos de los issues a una representación de cadena (JSON es una buena opción)
    # para incluirla en el prompt del LLM formateador.
    try:
        # Pydantic v2 usa model_dump, v1 usa dict()
        if hasattr(issues_data[0], 'model_dump'):
            issues_json_list = [issue.model_dump(exclude_none=True) for issue in issues_data]
        else: # Fallback para Pydantic v1
            issues_json_list = [issue.dict(exclude_none=True) for issue in issues_data]
        issues_data_str = json.dumps(issues_json_list, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error al serializar datos de issues: {e}"

    # Este es nuestro "output prompt" específico para formatear issues de Jira
    formatting_system_prompt_content = (
        "Eres un asistente experto en formatear datos de issues de Jira a Markdown. "
        "Tu única tarea es tomar la lista de datos de issues proporcionada y devolver una cadena Markdown formateada."
        "Debes seguir el formato EXACTO especificado."
    )
    
    formatting_user_prompt_content = f'''
Formatea la siguiente lista de datos de issues de Jira en Markdown. Sigue este formato exacto:

1.  **CLAVE-DEL-ISSUE**
    *   **Resumen:** El resumen del issue
    *   **Estado:** El estado actual del issue
    *   **Responsable:** El nombre del asignado (o 'No asignado' si es null o ausente)
2.  **OTRA-CLAVE-ISSUE** (si hay más issues)
    *   **Resumen:** ...
    *   **Estado:** ...
    *   **Responsable:** ...

Si la lista de datos de issues está vacía (aunque este caso se maneja antes), o si por alguna razón no puedes formatear, devuelve "No se pudieron formatear los issues."

Aquí están los datos de los issues (en formato JSON):
```json
{issues_data_str}
```

Por favor, proporciona solo el string Markdown formateado como respuesta, sin ningún texto introductorio o explicaciones adicionales.
'''

    try:
        messages_for_llm = [
            {"role": "system", "content": formatting_system_prompt_content},
            {"role": "user", "content": formatting_user_prompt_content}
        ]
        response = model_request_sync(
            settings.PYDANTIC_AI_MODEL,
            messages_for_llm
            # Podríamos añadir parámetros de modelo si es necesario, ej. temperature=0
        )
        
        if response and response.parts:
            # Asumimos que la respuesta del LLM es directamente el Markdown
            formatted_markdown = response.parts[0].content 
            if isinstance(formatted_markdown, str):
                return formatted_markdown.strip()
            else:
                # Si por alguna razón .content no es str, intentar convertirlo
                return str(formatted_markdown).strip()

        return "Error: El LLM formateador no devolvió una respuesta válida."
    except Exception as e:
        # Considera loguear el error real 'e' para depuración
        # import logfire
        # logfire.error(f"Error en LLM formateador: {e}")
        return f"Error al contactar al LLM formateador: {e}"

# Para pruebas locales (descomentar y ejecutar python tools/formatting_tools.py)
# if __name__ == '__main__':
#     test_issues = [
#         JiraIssueItem(key="TEST-1", summary="Primer issue de prueba", status="To Do", assignee="Usuario A"),
#         JiraIssueItem(key="TEST-2", summary="Segundo issue con detalles", status="In Progress", assignee=None),
#         JiraIssueItem(key="TEST-3", summary="Tercer issue muy importante", status="Done", assignee="Usuario B")
#     ]
#     
#     empty_issues = []
# 
#     print("--- Formateando issues de prueba ---")
#     formatted_output = format_jira_issues_for_markdown(test_issues)
#     print(formatted_output)
# 
#     print("\\n--- Formateando lista vacía ---")
#     formatted_empty_output = format_jira_issues_for_markdown(empty_issues)
#     print(formatted_empty_output)
#
#     # Prueba con un solo issue
#     print("\\n--- Formateando un solo issue ---")
#     single_issue = [JiraIssueItem(key="SINGLE-1", summary="Un único issue", status="Backlog", assignee="Asignado Único")]
#     formatted_single_output = format_jira_issues_for_markdown(single_issue)
#     print(formatted_single_output) 