# tools/jira_tools.py
import asyncio
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
# from pydantic_ai import tool # Recordar que no usamos el decorador aquí directamente

from agent_core.jira_instances import get_jira_client
import logfire

# ... (Clases JiraIssue y JiraIssueDetails como antes) ...
class JiraIssue(BaseModel):
    key: str
    summary: str
    status: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None

class JiraIssueDetails(JiraIssue):
    description: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    # ... y cualquier otro detalle que quieras

class CreatedJiraIssue(BaseModel):
    key: str
    id: str
    self_link: str = Field(alias="self") # Para el enlace devuelto por la API de Jira

class JiraComment(BaseModel):
    id: str
    body: str
    author: Optional[str] = None
    created: Optional[str] = None


async def search_issues(# ... (como antes) ...
    jql_query: str = Field(..., description="La consulta JQL para buscar issues. Ejemplo: 'project = \"PROJ\" AND status = Open ORDER BY priority DESC'"),
    max_results: int = 10
) -> List[JiraIssue]:
    # ... (código como antes, solo asegúrate de que max_results tiene un default simple)
    logfire.info("Ejecutando search_issues con JQL: {jql_query}, max_results: {max_results}",
                 jql_query=jql_query, max_results=max_results)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        with logfire.span("jira.jql_search", jql=jql_query, limit=max_results):
            issues_raw = await loop.run_in_executor(None, lambda: jira.jql(jql_query, limit=max_results))

        issues_found: List[JiraIssue] = []
        if issues_raw and issues_raw.get("issues"):
            for issue_data in issues_raw["issues"]:
                fields = issue_data.get("fields", {})
                assignee_info = fields.get("assignee")
                reporter_info = fields.get("reporter")
                issues_found.append(
                    JiraIssue(
                        key=issue_data.get("key"),
                        summary=fields.get("summary"),
                        status=fields.get("status", {}).get("name"),
                        assignee=assignee_info.get("displayName") if assignee_info else None,
                        reporter=reporter_info.get("displayName") if reporter_info else None,
                    )
                )
        logfire.info("search_issues encontró {count} issues.", count=len(issues_found))
        return issues_found
    except Exception as e:
        logfire.error("Error en search_issues: {error_message}", error_message=str(e), exc_info=True)
        return [JiraIssue(key="ERROR", summary=f"Error al buscar issues: {str(e)}")]


async def get_issue_details(# ... (como antes) ...
    issue_key: str = Field(..., description="La clave del issue (ej. 'PROJ-123').")
) -> JiraIssueDetails:
    # ... (código como antes) ...
    logfire.info("Ejecutando get_issue_details para: {issue_key}", issue_key=issue_key)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        with logfire.span("jira.issue_details", issue_key=issue_key):
            issue_data = await loop.run_in_executor(None, jira.issue, issue_key)

        if not issue_data:
            return JiraIssueDetails(key=issue_key, summary=f"No se encontró el issue con clave {issue_key}", status="NOT_FOUND")

        fields = issue_data.get("fields", {})
        assignee_info = fields.get("assignee")
        reporter_info = fields.get("reporter")
        
        details = JiraIssueDetails(
            key=issue_data.get("key"),
            summary=fields.get("summary"),
            status=fields.get("status", {}).get("name"),
            assignee=assignee_info.get("displayName") if assignee_info else None,
            reporter=reporter_info.get("displayName") if reporter_info else None,
            description=fields.get("description"), # El formato puede ser Atlassian Document Format
            created=fields.get("created"),
            updated=fields.get("updated"),
        )
        logfire.info("get_issue_details obtuvo detalles para {issue_key}", issue_key=issue_key)
        return details
    except Exception as e:
        logfire.error("Error en get_issue_details para {issue_key}: {error_message}", 
                      issue_key=issue_key, error_message=str(e), exc_info=True)
        return JiraIssueDetails(key=issue_key, summary=f"Error al obtener detalles: {str(e)}", status="ERROR")

# --- NUEVAS HERRAMIENTAS DE ESCRITURA ---

async def create_jira_issue(
    project_key: str = Field(..., description="La clave del proyecto donde crear el issue (ej. 'PROJ')."),
    summary: str = Field(..., description="Un resumen conciso del issue."),
    issue_type: str = Field(..., description="El tipo de issue (ej. 'Bug', 'Task', 'Story', 'Epic'). Debe ser un tipo válido en el proyecto."),
    description: Optional[str] = Field(default=None, description="Una descripción detallada del issue (opcional).")
) -> CreatedJiraIssue:
    """
    Crea un nuevo issue en un proyecto de Jira especificado.
    Descripción para el LLM: Crea un nuevo issue en Jira. Necesitas la clave del proyecto, un resumen y el tipo de issue. La descripción es opcional.
    """
    logfire.info("Intentando crear issue en {project_key} con summary: '{summary}'", 
                 project_key=project_key, summary=summary)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        issue_dict = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if description:
            # Para Jira Cloud, la descripción puede necesitar el formato Atlassian Document Format (ADF)
            # Para simplificar, asumimos texto plano. Si se requiere ADF, esto necesitaría un conversor.
            issue_dict["description"] = description 
            # Para ADF:
            # issue_dict["description"] = {
            #     "type": "doc",
            #     "version": 1,
            #     "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            # }

        with logfire.span("jira.create_issue", project=project_key, summary=summary, type=issue_type):
            created_issue_data = await loop.run_in_executor(None, jira.create_issue, fields=issue_dict)
        
        logfire.info("Issue {issue_key} creado exitosamente.", issue_key=created_issue_data['key'])
        return CreatedJiraIssue(
            key=created_issue_data['key'],
            id=created_issue_data['id'],
            self_link=created_issue_data['self']
        )
    except Exception as e:
        logfire.error("Error al crear issue en Jira: {error_message}", error_message=str(e), exc_info=True)
        # Devolver un objeto con un error
        return CreatedJiraIssue(key="ERROR", id="ERROR", self_link=f"Error al crear issue: {str(e)}")


async def add_comment_to_jira_issue(
    issue_key: str = Field(..., description="La clave del issue al que añadir el comentario (ej. 'PROJ-123')."),
    comment_body: str = Field(..., description="El contenido del comentario.")
) -> JiraComment:
    """
    Añade un comentario a un issue existente en Jira.
    Descripción para el LLM: Añade un comentario a un issue específico de Jira. Necesitas la clave del issue y el texto del comentario.
    """
    logfire.info("Intentando añadir comentario al issue: {issue_key}", issue_key=issue_key)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()

        with logfire.span("jira.add_comment_to_issue", issue_key=issue_key): # Renombrado el span para claridad
            # CORRECCIÓN: Usar el método correcto de la biblioteca
            comment_data_dict = await loop.run_in_executor(None, jira.issue_add_comment, issue_key, comment_body)
        
        # La respuesta de issue_add_comment es un diccionario directamente
        if not isinstance(comment_data_dict, dict) or 'id' not in comment_data_dict:
            logfire.error("Respuesta inesperada de jira.issue_add_comment: {response_data}", response_data=comment_data_dict)
            return JiraComment(id="ERROR", body=f"Respuesta inesperada de la API de Jira al añadir comentario.")


        author_info = comment_data_dict.get("author", {})
        # El cuerpo del comentario puede estar en 'body' o dentro de un objeto ADF más complejo.
        # Para texto simple, 'body' debería funcionar. Si es ADF, necesitaría un parseo.
        raw_body = comment_data_dict.get('body')
        comment_text = raw_body # Asumimos texto plano por ahora.
        # Si raw_body fuera ADF (un dict), necesitarías extraer el texto:
        # if isinstance(raw_body, dict) and raw_body.get('type') == 'doc':
        #     try:
        #         comment_text = raw_body['content'][0]['content'][0]['text']
        #     except (IndexError, KeyError, TypeError):
        #         comment_text = "Contenido ADF no pudo ser parseado a texto simple."

        created_comment = JiraComment(
            id=comment_data_dict['id'],
            body=comment_text, 
            author=author_info.get('displayName'),
            created=comment_data_dict.get('created')
        )
        logfire.info("Comentario añadido exitosamente al issue {issue_key}, ID comentario: {comment_id}",
                     issue_key=issue_key, comment_id=created_comment.id)
        return created_comment
    except Exception as e:
        logfire.error("Error al añadir comentario al issue {issue_key}: {error_message}", 
                      issue_key=issue_key, error_message=str(e), exc_info=True)
        return JiraComment(id="ERROR", body=f"Error al añadir comentario: {str(e)}")

if __name__ == "__main__":
    from config import settings
    import asyncio # Asegúrate que asyncio está importado aquí también
    logfire.configure(token=settings.LOGFIRE_TOKEN, send_to_logfire="if-token-present", service_name="jira_tools_comment_test")
    
    async def test_jira_add_comment_tool():
        # !! IMPORTANTE: CAMBIA ESTE VALOR POR UNA CLAVE DE ISSUE VÁLIDA Y EXISTENTE EN TU JIRA DE PRUEBAS !!
        existing_issue_key = "PSIMDESASW-6701" # Por ejemplo, "TESTPROJ-123"
        
        if existing_issue_key == "YOUR_EXISTING_JIRA_ISSUE_KEY":
            print("Por favor, edita 'tools/jira_tools.py' y cambia 'YOUR_EXISTING_JIRA_ISSUE_KEY' por una clave de issue real para probar.")
            return

        print(f"\nProbando add_comment_to_jira_issue en {existing_issue_key}...")
        try:
            comment = await add_comment_to_jira_issue(
                issue_key=existing_issue_key,
                comment_body="Este es un comentario de prueba añadido por el agente (prueba directa de tool)."
            )
            if comment.id != "ERROR":
                print(f"Comentario añadido: ID {comment.id} - Autor: {comment.author} - Creado: {comment.created}")
                print(f"Cuerpo del comentario (puede ser ADF o texto): {comment.body[:100] if comment.body else 'N/A'}...")
            else:
                print(f"Error al añadir comentario: {comment.body}")
        except Exception as e:
            print(f"Error durante la prueba de añadir comentario en Jira: {e}")
            import traceback
            traceback.print_exc()
            
    asyncio.run(test_jira_add_comment_tool())