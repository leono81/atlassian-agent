# tools/jira_tools.py
# ... (importaciones y clases Pydantic como antes, y _parse_time_spent_to_seconds) ...
# ... (search_issues, get_issue_details, add_comment_to_jira_issue como antes) ...
import asyncio
import re 
import functools
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo 

from agent_core.jira_instances import get_jira_client
import logfire
from tools.date_utils import parse_relative_date, get_weekday_name

class JiraIssue(BaseModel):
    key: str
    summary: str
    status: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    duedate: Optional[str] = None  # Fecha de vencimiento (YYYY-MM-DD)

class JiraIssueDetails(JiraIssue):
    description: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None

class CreatedJiraIssue(BaseModel):
    key: str
    id: str
    self_link: Optional[str] = Field(default=None, alias="self")

class JiraComment(BaseModel):
    id: str
    body: Optional[str] = None 
    author: Optional[str] = None
    created: Optional[str] = None

class JiraWorklog(BaseModel):
    id: str
    self_link: Optional[str] = Field(default=None, alias="self")
    author: Optional[str] = None
    time_spent_seconds: Optional[int] = Field(default=None, alias="timeSpentSeconds")
    started: Optional[str] = None
    comment: Optional[str] = None


async def search_issues(
    jql_query: str = Field(..., description="La consulta JQL para buscar issues. Ejemplo: 'project = \"PROJ\" AND status = Open ORDER BY priority DESC'"),
    max_results: int = 10
) -> List[JiraIssue]:
    actual_max_results = min(max(1, max_results), 100)
    logfire.info("Ejecutando search_issues con JQL: {jql_query}, max_results: {max_results}",
                 jql_query=jql_query, max_results=actual_max_results)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        with logfire.span("jira.jql_search", jql=jql_query, limit=actual_max_results):
            issues_raw = await loop.run_in_executor(None, lambda: jira.jql(jql_query, limit=actual_max_results))
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
                        duedate=fields.get("duedate")  # Nueva línea para poblar la fecha de vencimiento
                    )
                )
        logfire.info("search_issues encontró {count} issues.", count=len(issues_found))
        return issues_found
    except Exception as e:
        logfire.error("Error en search_issues: {error_message}", error_message=str(e), exc_info=True)
        return [JiraIssue(key="ERROR", summary=f"Error al buscar issues: {str(e)}")]

async def get_issue_details(
    issue_key: str = Field(..., description="La clave del issue (ej. 'PROJ-123').")
) -> JiraIssueDetails:
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
            description=fields.get("description"), 
            created=fields.get("created"),
            updated=fields.get("updated"),
        )
        logfire.info("get_issue_details obtuvo detalles para {issue_key}", issue_key=issue_key)
        return details
    except Exception as e:
        logfire.error("Error en get_issue_details para {issue_key}: {error_message}", 
                      issue_key=issue_key, error_message=str(e), exc_info=True)
        return JiraIssueDetails(key=issue_key, summary=f"Error al obtener detalles: {str(e)}", status="ERROR")

async def add_comment_to_jira_issue(
    issue_key: str = Field(..., description="La clave del issue al que añadir el comentario (ej. 'PROJ-123')."),
    comment_body: str = Field(..., description="El contenido del comentario.")
) -> JiraComment:
    logfire.info("Intentando añadir comentario al issue: {issue_key}", issue_key=issue_key)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        with logfire.span("jira.add_comment_to_issue", issue_key=issue_key):
            comment_data_dict = await loop.run_in_executor(None, jira.issue_add_comment, issue_key, comment_body)
        if not isinstance(comment_data_dict, dict) or 'id' not in comment_data_dict:
            logfire.error("Respuesta inesperada de jira.issue_add_comment: {response_data}", response_data=comment_data_dict)
            return JiraComment(id="ERROR", body=f"Respuesta inesperada de la API de Jira al añadir comentario.")
        author_info = comment_data_dict.get("author", {})
        raw_body = comment_data_dict.get('body')
        comment_text = raw_body 
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

def _parse_time_spent_to_seconds(time_str_param: Any) -> int: # Cambiado a Any para manejar FieldInfo
    time_str: str
    if isinstance(time_str_param, FieldInfo):
        # Este caso NO debería ocurrir para un campo obligatorio como time_spent si el LLM lo llena.
        # Si ocurre, es un problema en cómo PydanticAI llama a la tool o el LLM no lo está proveyendo.
        logfire.error("time_spent llegó como FieldInfo, lo cual es inesperado para un campo obligatorio. Revisar llamada del LLM.")
        raise ValueError("time_spent es obligatorio y no se recibió un valor de string.")
    elif not time_str_param or not isinstance(time_str_param, str):
        raise ValueError(f"time_spent debe ser un string no vacío, se recibió: {time_str_param} (tipo: {type(time_str_param)})")
    else:
        time_str = time_str_param

    seconds = 0
    time_str_cleaned = time_str.lower().replace(" ", "")
    
    # Intenta encontrar patrones como Xh, Ym, Zs
    pattern = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?")
    match = pattern.fullmatch(time_str_cleaned)

    if match:
        h, m, s = match.groups()
        if h: seconds += int(h) * 3600
        if m: seconds += int(m) * 60
        if s: seconds += int(s)
        # Si solo es un número sin unidad, asumirlo como segundos (si no hubo h, m, o s)
        if not (h or m or s) and time_str_cleaned.isdigit():
            seconds = int(time_str_cleaned)
    elif time_str_cleaned.isdigit(): # Si es solo un número
        seconds = int(time_str_cleaned)
    
    if seconds == 0 and not (time_str_cleaned == "0" or time_str_cleaned == "0s"):
        is_just_zero_digit = time_str_cleaned.isdigit() and int(time_str_cleaned) == 0
        if not is_just_zero_digit:
            raise ValueError(f"Formato de 'time_spent' ('{time_str}') no reconocido o es cero sin unidad. Usa 'Xh Ym Zs' o solo segundos.")
    return seconds

async def add_worklog_to_jira_issue(
    issue_key: str = Field(..., description="La clave del issue de Jira (ej. 'PROJ-123')."),
    time_spent: str = Field(..., description="El tiempo trabajado. Ejemplos: '2h', '30m', '1h 30m', '900s' (para 15 minutos) o solo el número de segundos como '900'. Debe ser un valor positivo."),
    started_datetime_str: Optional[str] = Field(
        default=None, 
        description="Opcional. Fecha y hora de inicio del trabajo. Usa 'ahora' para el momento actual, o un formato ISO 8601 como 'AAAA-MM-DDTHH:MM:SS+ZZZZ' (ej. '2024-07-30T14:30:00+02:00'). Si se omite, se usará la hora actual."
    ),
    comment: Optional[str] = Field(default=None, description="Un comentario opcional para el worklog."),
    confirm: bool = Field(default=False, description="Confirma si se debe proceder con el registro si la fecha fue interpretada.")
) -> JiraWorklog:
    # --- CORRECTO MANEJO DE VALORES DE ENTRADA ---
    actual_started_datetime_str_val: Optional[str]
    if isinstance(started_datetime_str, FieldInfo):
        actual_started_datetime_str_val = started_datetime_str.default
    else:
        actual_started_datetime_str_val = started_datetime_str

    actual_comment_val: Optional[str]
    if isinstance(comment, FieldInfo):
        actual_comment_val = comment.default
    else:
        actual_comment_val = comment

    if isinstance(time_spent, FieldInfo):
         logfire.error("El parámetro obligatorio 'time_spent' fue recibido como FieldInfo. Esto no debería ocurrir.")
         raise ValueError("Error interno: 'time_spent' no fue proporcionado correctamente.")

    logfire.info("Intentando añadir worklog al issue: {issue_key} por '{ts_str}'", issue_key=issue_key, ts_str=time_spent)
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()

        time_spent_seconds_int = _parse_time_spent_to_seconds(time_spent)
        if time_spent_seconds_int <= 0:
            raise ValueError("El tiempo trabajado (time_spent) debe ser mayor que cero segundos para Jira.")

        # --- Manejo robusto de fechas ---
        # Si started_datetime_str es una fecha relativa (no ISO ni 'ahora'), usar parse_relative_date
        if not actual_started_datetime_str_val or (isinstance(actual_started_datetime_str_val, str) and actual_started_datetime_str_val.lower() == 'ahora'):
            _started_dt_object = datetime.datetime.now(datetime.timezone.utc).astimezone()
        else:
            try:
                _started_dt_object = datetime.datetime.fromisoformat(actual_started_datetime_str_val.replace("Z", "+00:00"))
                if _started_dt_object.tzinfo is None:
                    _started_dt_object = _started_dt_object.replace(tzinfo=datetime.timezone.utc).astimezone()
            except ValueError:
                # Usar date_utils para fechas relativas
                parsed_date = parse_relative_date(actual_started_datetime_str_val)
                if parsed_date:
                    # Por defecto, hora 08:30 si no se especifica
                    _started_dt_object = datetime.datetime.combine(parsed_date, datetime.time(8, 30)).astimezone()
                    if not confirm:
                        # Devuelve un mensaje de confirmación antes de proceder
                        weekday = get_weekday_name(parsed_date)
                        fecha_str = parsed_date.strftime('%d/%m/%Y')
                        hora_str = '08:30'
                        msg = f"¿Quieres registrar el tiempo el {weekday} {fecha_str} a las {hora_str}? Confirma para continuar."
                        # Devuelve un JiraWorklog especial solo con el mensaje de confirmación
                        return JiraWorklog(id="CONFIRM_REQUIRED", comment=msg)
                else:
                    raise ValueError(f"No se pudo interpretar la fecha '{actual_started_datetime_str_val}'. Usa formato ISO o una fecha relativa reconocida.")
        # Formatear como string para Jira
        started_str = _started_dt_object.strftime("%Y-%m-%dT%H:%M:%S.000%z")
        # Llamada correcta: argumentos posicionales
        with logfire.span("jira.add_worklog_final_call", issue_key=issue_key, started=started_str, time_spent_seconds=time_spent_seconds_int):
            call_func = functools.partial(
                jira.issue_worklog,
                issue_key,
                started_str,
                time_spent_seconds_int
            )
            worklog_data = await loop.run_in_executor(None, call_func)

        author_info = worklog_data.get("author", {})
        comment_from_response = worklog_data.get('comment')
        comment_text_to_store = ""
        if isinstance(comment_from_response, str):
            comment_text_to_store = comment_from_response
        elif isinstance(comment_from_response, dict): 
            try: comment_text_to_store = comment_from_response['content'][0]['content'][0]['text']
            except: comment_text_to_store = str(comment_from_response)

        created_worklog = JiraWorklog(
            id=str(worklog_data['id']),
            self_link=worklog_data.get('self'),
            author=author_info.get('displayName'),
            time_spent_seconds=worklog_data.get('timeSpentSeconds'),
            started=worklog_data.get('started'), 
            comment=comment_text_to_store
        )
        logfire.info("Worklog añadido exitosamente al issue {issue_key}, ID worklog: {worklog_id}",
                     issue_key=issue_key, worklog_id=created_worklog.id)
        return created_worklog
    except ValueError as ve:
        logfire.warning("Error de valor en add_worklog_to_jira_issue: {error_message}", error_message=str(ve))
        return JiraWorklog(id="ERROR", comment=f"Error de datos: {str(ve)}")
    except Exception as e:
        logfire.error("Error al añadir worklog al issue {issue_key}: {error_message}", 
                      issue_key=issue_key, error_message=str(e), exc_info=True)
        return JiraWorklog(id="ERROR", comment=f"Error al añadir worklog: {str(e)}")

async def get_user_worklog_hours_for_issue(
    issue_key: str,
    username_or_accountid: str
) -> float:
    """
    Devuelve la cantidad total de horas que un usuario trabajó en una historia (issue).
    El usuario puede ser identificado por 'name' (Jira Server) o 'accountId' (Jira Cloud).
    """
    jira = get_jira_client()
    loop = asyncio.get_running_loop()
    worklogs_data = await loop.run_in_executor(None, lambda: jira.issue_get_worklog(issue_key))
    total_seconds = 0
    for worklog in worklogs_data.get('worklogs', []):
        author = worklog.get('author', {})
        # Compatibilidad con Jira Cloud y Server
        if (
            author.get('name') == username_or_accountid or
            author.get('accountId') == username_or_accountid or
            author.get('displayName') == username_or_accountid
        ):
            total_seconds += worklog.get('timeSpentSeconds', 0)
    total_hours = total_seconds / 3600
    return total_hours

from pydantic import Field

async def get_user_hours_on_story(
    issue_key: str = Field(..., description="Clave de la historia (issue), ej: 'PROJ-123'"),
    username_or_accountid: str = Field(..., description="Usuario (accountId, name o displayName)")
) -> float:
    """
    Devuelve la cantidad total de horas que un usuario trabajó en una historia (issue).
    """
    return await get_user_worklog_hours_for_issue(issue_key, username_or_accountid)

async def get_child_issues_status(
    parent_issue_key: str = Field(..., description="Clave de la historia o iniciativa principal (ej: 'PROJ-123')"),
    days_soon: int = 3
) -> List[dict]:
    """
    Devuelve las subtareas/tareas hijas de una historia/iniciativa, con análisis de vencimiento y responsable.
    """
    # Buscar subtareas (issues cuyo parent es la historia)
    jql_subtasks = f'parent = "{parent_issue_key}" ORDER BY priority DESC'
    subtasks = await search_issues(jql_subtasks, max_results=50)
    results = []
    now = datetime.now().date()
    soon_threshold = now + timedelta(days=days_soon)

    for issue in subtasks:
        duedate = None
        status_due = "Sin vencimiento"
        if issue.duedate:
            try:
                duedate = datetime.strptime(issue.duedate, "%Y-%m-%d").date()
                if duedate < now:
                    status_due = "Vencida"
                elif duedate <= soon_threshold:
                    status_due = "Próxima a vencer"
                else:
                    status_due = "En tiempo"
            except Exception:
                status_due = "Fecha inválida"
        results.append({
            "key": issue.key,
            "summary": issue.summary,
            "assignee": issue.assignee,
            "status": issue.status,
            "duedate": issue.duedate,
            "vencimiento": status_due
        })
    return results

if __name__ == "__main__":
    from config import settings
    import asyncio
    logfire.configure(token=settings.LOGFIRE_TOKEN, send_to_logfire="if-token-present", service_name="jira_tools_worklog_test_v3")

    async def test_jira_add_worklog_tool_detailed():
        existing_issue_key = "PSIMDESASW-6701" # CAMBIA ESTO
        if existing_issue_key == "YOUR_EXISTING_JIRA_ISSUE_KEY":
            print("Edita 'tools/jira_tools.py' y cambia 'YOUR_EXISTING_JIRA_ISSUE_KEY' en la prueba.")
            return

        print(f"\nProbando add_worklog_to_jira_issue en {existing_issue_key}...")
        test_cases = [
            {"time_spent": "30m", "started_datetime_str": "ahora", "comment": "30 min, ahora (v3 test)"},
            {"time_spent": "7200", "started_datetime_str": None, "comment": "2 horas (segundos), inicio default (v3 test)"},
            {"time_spent": "1h", "started_datetime_str": "2024-07-30T10:00:00+00:00", "comment": "1h, inicio ISO (v3 test)"},
            {"time_spent": "15s", "comment": "Solo 15 segundos (v3 test)"},
        ]

        for i, case in enumerate(test_cases):
            print(f"\n--- Caso de prueba {i+1} ---")
            try:
                worklog = await add_worklog_to_jira_issue(
                    issue_key=existing_issue_key,
                    time_spent=case["time_spent"],
                    started_datetime_str=case.get("started_datetime_str"),
                    comment=case["comment"]
                )
                if worklog.id != "ERROR":
                    print(f"Worklog añadido: ID {worklog.id}, Tiempo: {worklog.time_spent_seconds}s, Inicio: {worklog.started}, Comment: {worklog.comment}")
                else:
                    print(f"Error al añadir worklog: {worklog.comment}")
            except Exception as e:
                print(f"Excepción durante el caso de prueba {i+1}: {e}")
                import traceback
                traceback.print_exc()
            await asyncio.sleep(1)

    asyncio.run(test_jira_add_worklog_tool_detailed())