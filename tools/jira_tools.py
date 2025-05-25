# tools/jira_tools.py
# ... (importaciones y clases Pydantic como antes, y _parse_time_spent_to_seconds) ...
# ... (search_issues, get_issue_details, add_comment_to_jira_issue como antes) ...
import asyncio
import re 
import functools
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone, time

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

# === NUEVAS CLASES PARA WORKLOG DETALLADO ===
class UserWorklogSummary(BaseModel):
    user_display_name: str
    user_account_id: Optional[str] = None
    total_hours: float
    total_seconds: int
    worklog_count: int
    worklogs: List[JiraWorklog]

class IssueWorklogReport(BaseModel):
    issue_key: str
    issue_summary: str
    total_hours_all_users: float
    total_seconds_all_users: int
    total_worklog_entries: int
    users_summary: List[UserWorklogSummary]

# === NUEVAS CLASES PARA SPRINT ===
class JiraSprint(BaseModel):
    id: str
    name: str
    state: str  # "active", "future", "closed"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    goal: Optional[str] = None

class SprintIssues(BaseModel):
    sprint: JiraSprint
    issues: List[JiraIssue]
    total_issues: int
    completed_issues: int
    in_progress_issues: int

class SprintProgress(BaseModel):
    sprint: JiraSprint
    total_story_points: Optional[int] = None
    completed_story_points: Optional[int] = None
    total_issues: int
    completed_issues: int
    progress_percentage: float
    days_remaining: Optional[int] = None

# === NUEVAS CLASES PARA BÚSQUEDA DE USUARIOS ===
class JiraUser(BaseModel):
    account_id: str
    display_name: str
    email_address: Optional[str] = None
    active: bool = True
    account_type: Optional[str] = None

class UserSearchResult(BaseModel):
    users_found: List[JiraUser]
    total_found: int
    search_query: str
    exact_match: Optional[JiraUser] = None
    suggestions: List[JiraUser] = []
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None

def _clean_field_info_param(param_value: Any) -> Any:
    """
    Función utilitaria para limpiar parámetros que pueden llegar como FieldInfo
    en lugar de sus valores reales. Esto ocurre cuando el LLM o framework
    no maneja correctamente los parámetros opcionales.
    """
    if isinstance(param_value, FieldInfo):
        return param_value.default
    elif isinstance(param_value, str) and "annotation=NoneType" in param_value:
        return None
    return param_value

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
    # Limpiar parámetros que pueden llegar como FieldInfo
    started_datetime_str = _clean_field_info_param(started_datetime_str)
    comment = _clean_field_info_param(comment)
    
    # Validar que time_spent (obligatorio) no sea FieldInfo
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
        if not started_datetime_str or (isinstance(started_datetime_str, str) and started_datetime_str.lower() == 'ahora'):
            _started_dt_object = datetime.now(timezone.utc).astimezone()
        else:
            try:
                _started_dt_object = datetime.fromisoformat(started_datetime_str.replace("Z", "+00:00"))
                if _started_dt_object.tzinfo is None:
                    _started_dt_object = _started_dt_object.replace(tzinfo=timezone.utc).astimezone()
            except ValueError:
                # Usar date_utils para fechas relativas
                parsed_date = parse_relative_date(started_datetime_str)
                if parsed_date:
                    # Por defecto, hora 08:30 si no se especifica
                    _started_dt_object = datetime.combine(parsed_date, time(8, 30)).astimezone()
                    if not confirm:
                        # Devuelve un mensaje de confirmación antes de proceder
                        weekday = get_weekday_name(parsed_date)
                        fecha_str = parsed_date.strftime('%d/%m/%Y')
                        hora_str = '08:30'
                        msg = f"¿Quieres registrar el tiempo el {weekday} {fecha_str} a las {hora_str}? Confirma para continuar."
                        # Devuelve un JiraWorklog especial solo con el mensaje de confirmación
                        return JiraWorklog(id="CONFIRM_REQUIRED", comment=msg)
                else:
                    raise ValueError(f"No se pudo interpretar la fecha '{started_datetime_str}'. Usa formato ISO o una fecha relativa reconocida.")
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

async def get_user_hours_on_story(
    issue_key: str = Field(..., description="Clave de la historia (issue), ej: 'PROJ-123'"),
    username_or_accountid: str = Field(..., description="Usuario (accountId, name o displayName)")
) -> Dict[str, Any]:
    """
    Devuelve la cantidad total de horas que un usuario trabajó en una historia (issue).
    Incluye validación del usuario y manejo de confirmaciones.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    issue_key = _clean_field_info_param(issue_key)
    username_or_accountid = _clean_field_info_param(username_or_accountid)
    
    if not issue_key or not isinstance(issue_key, str):
        return {
            "hours": 0.0,
            "requires_confirmation": False,
            "message": "La clave del issue no puede estar vacía.",
            "suggestions": []
        }
    
    if not username_or_accountid or not isinstance(username_or_accountid, str):
        return {
            "hours": 0.0,
            "requires_confirmation": False,
            "message": "El identificador de usuario no puede estar vacío.",
            "suggestions": []
        }
    
    # Validar usuario primero
    validation_result = await validate_jira_user(username_or_accountid)
    
    # Si requiere confirmación, devolver información para que el usuario confirme
    if validation_result.requires_confirmation:
        return {
            "hours": 0.0,
            "requires_confirmation": True,
            "message": validation_result.confirmation_message,
            "suggestions": [
                {
                    "display_name": user.display_name,
                    "email": user.email_address,
                    "account_id": user.account_id
                }
                for user in validation_result.suggestions
            ]
        }
    
    # Si no se encontró usuario
    if not validation_result.exact_match:
        return {
            "hours": 0.0,
            "requires_confirmation": False,
            "message": validation_result.confirmation_message or f"Usuario '{username_or_accountid}' no encontrado.",
            "suggestions": []
        }
    
    # Si hay coincidencia exacta, proceder con la consulta
    try:
        hours = await get_user_worklog_hours_for_issue(issue_key, validation_result.exact_match.account_id)
        return {
            "hours": hours,
            "requires_confirmation": False,
            "message": f"Horas trabajadas por {validation_result.exact_match.display_name} en {issue_key}: {hours}h",
            "user_confirmed": {
                "display_name": validation_result.exact_match.display_name,
                "email": validation_result.exact_match.email_address,
                "account_id": validation_result.exact_match.account_id
            }
        }
    except Exception as e:
        logfire.error("Error al obtener horas para usuario validado: {error}", error=str(e))
        return {
            "hours": 0.0,
            "requires_confirmation": False,
            "message": f"Error al consultar horas: {str(e)}",
            "suggestions": []
                 }

async def get_user_hours_with_confirmed_user(
    issue_key: str = Field(..., description="Clave de la historia (issue), ej: 'PROJ-123'"),
    user_account_id: str = Field(..., description="Account ID del usuario confirmado"),
    user_display_name: str = Field(..., description="Nombre del usuario para referencia")
) -> Dict[str, Any]:
    """
    Consulta las horas trabajadas usando un usuario ya confirmado por su account ID.
    Esta función se usa después de que el usuario ha confirmado cuál usuario quiere consultar.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    issue_key = _clean_field_info_param(issue_key)
    user_account_id = _clean_field_info_param(user_account_id)
    user_display_name = _clean_field_info_param(user_display_name)
    
    if not issue_key or not isinstance(issue_key, str):
        return {
            "hours": 0.0,
            "message": "La clave del issue no puede estar vacía."
        }
    
    if not user_account_id or not isinstance(user_account_id, str):
        return {
            "hours": 0.0,
            "message": "El account ID del usuario no puede estar vacío."
        }
    
    if not user_display_name or not isinstance(user_display_name, str):
        user_display_name = "Usuario confirmado"
    
    logfire.info("Consultando horas para usuario confirmado: {user} en {issue}", 
                 user=user_display_name, issue=issue_key)
    
    try:
        hours = await get_user_worklog_hours_for_issue(issue_key, user_account_id)
        return {
            "hours": hours,
            "message": f"Horas trabajadas por {user_display_name} en {issue_key}: {hours}h",
            "user_confirmed": {
                "display_name": user_display_name,
                "account_id": user_account_id
            }
        }
    except Exception as e:
        logfire.error("Error al obtener horas para usuario confirmado {user}: {error}", 
                      user=user_display_name, error=str(e))
        return {
            "hours": 0.0,
            "message": f"Error al consultar horas para {user_display_name}: {str(e)}"
        }

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

async def search_jira_users(
    query: str = Field(..., description="Término de búsqueda para usuarios. Puede ser nombre parcial, email o displayName"),
    max_results: int = Field(default=10, description="Número máximo de resultados (1-50)")
) -> UserSearchResult:
    """
    Busca usuarios en Jira por nombre, email o displayName.
    Útil cuando no recuerdas el nombre exacto del usuario.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    query = _clean_field_info_param(query)
    max_results = _clean_field_info_param(max_results) or 10
    
    if not query or not isinstance(query, str):
        return UserSearchResult(
            users_found=[],
            total_found=0,
            search_query=str(query) if query else "vacío",
            exact_match=None,
            suggestions=[],
            requires_confirmation=False,
            confirmation_message="La consulta de búsqueda no puede estar vacía."
        )
    
    actual_max_results = min(max(1, max_results), 50)
    logfire.info("Ejecutando search_jira_users con query: {query}, max_results: {max_results}",
                 query=query, max_results=actual_max_results)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        # Usar la API de búsqueda de usuarios de Jira
        with logfire.span("jira.user_search", query=query, limit=actual_max_results):
            # Para Jira Cloud, usar user_find_by_user_string
            users_raw = await loop.run_in_executor(
                None, 
                lambda: jira.user_find_by_user_string(
                    query=query, 
                    start=0, 
                    limit=actual_max_results, 
                    include_inactive_users=False
                )
            )
        
        if not users_raw:
            return UserSearchResult(
                users_found=[],
                total_found=0,
                search_query=query,
                exact_match=None,
                suggestions=[]
            )
        
        # Procesar usuarios encontrados
        users_found = []
        exact_match = None
        
        for user_data in users_raw:
            user = JiraUser(
                account_id=user_data.get('accountId', ''),
                display_name=user_data.get('displayName', 'Usuario sin nombre'),
                email_address=user_data.get('emailAddress'),
                active=user_data.get('active', True),
                account_type=user_data.get('accountType', 'atlassian')
            )
            users_found.append(user)
            
            # Verificar coincidencia exacta
            if (user.display_name.lower() == query.lower() or 
                (user.email_address and user.email_address.lower() == query.lower())):
                exact_match = user
        
        # Crear sugerencias (usuarios más relevantes)
        suggestions = users_found[:5] if len(users_found) > 1 else []
        
        result = UserSearchResult(
            users_found=users_found,
            total_found=len(users_found),
            search_query=query,
            exact_match=exact_match,
            suggestions=suggestions
        )
        
        logfire.info("search_jira_users encontró {count} usuarios para query '{query}'",
                     count=len(users_found), query=query)
        return result
        
    except Exception as e:
        logfire.error("Error en search_jira_users para query '{query}': {error_message}",
                      query=query, error_message=str(e), exc_info=True)
        return UserSearchResult(
            users_found=[],
            total_found=0,
            search_query=query,
            exact_match=None,
            suggestions=[],
        )

async def validate_jira_user(
    user_identifier: str = Field(..., description="Identificador del usuario: accountId, email o displayName")
) -> UserSearchResult:
    """
    Valida si un usuario existe en Jira y devuelve información para confirmación.
    Si no hay coincidencia exacta, requiere confirmación del usuario antes de proceder.
    """
    # Limpiar parámetro que puede llegar como FieldInfo
    user_identifier = _clean_field_info_param(user_identifier)
    
    if not user_identifier or not isinstance(user_identifier, str):
        return UserSearchResult(
            users_found=[],
            total_found=0,
            search_query=str(user_identifier) if user_identifier else "vacío",
            exact_match=None,
            suggestions=[],
            requires_confirmation=False,
            confirmation_message="El identificador de usuario no puede estar vacío."
        )
    
    logfire.info("Ejecutando validate_jira_user para: {user_identifier}", user_identifier=user_identifier)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        # Primero intentar obtener el usuario directamente si parece ser un accountId
        if user_identifier and len(user_identifier) > 20 and ':' in user_identifier:
            try:
                with logfire.span("jira.user_direct", user_id=user_identifier):
                    user_data = await loop.run_in_executor(None, jira.user, user_identifier)
                
                if user_data:
                    validated_user = JiraUser(
                        account_id=user_data.get('accountId', user_identifier),
                        display_name=user_data.get('displayName', 'Usuario sin nombre'),
                        email_address=user_data.get('emailAddress'),
                        active=user_data.get('active', True),
                        account_type=user_data.get('accountType', 'atlassian')
                    )
                    logfire.info("validate_jira_user encontró usuario directo: {display_name}",
                                 display_name=validated_user.display_name)
                    return UserSearchResult(
                        users_found=[validated_user],
                        total_found=1,
                        search_query=user_identifier,
                        exact_match=validated_user,
                        suggestions=[],
                        requires_confirmation=False
                    )
            except Exception:
                # Si falla, continuar con búsqueda
                pass
        
        # Si no es accountId o falló, buscar por nombre/email
        with logfire.span("jira.user_search_validation", query=user_identifier):
            users_raw = await loop.run_in_executor(
                None,
                lambda: jira.user_find_by_user_string(
                    query=user_identifier,
                    start=0,
                    limit=10,
                    include_inactive_users=False
                )
            )
        
        if not users_raw:
            logfire.info("validate_jira_user no encontró usuario para: {user_identifier}",
                         user_identifier=user_identifier)
            return UserSearchResult(
                users_found=[],
                total_found=0,
                search_query=user_identifier,
                exact_match=None,
                suggestions=[],
                requires_confirmation=False,
                confirmation_message=f"No se encontró ningún usuario con '{user_identifier}'. Verifica el nombre o email."
            )
        
        # Procesar usuarios encontrados
        users_found = []
        exact_match = None
        
        for user_data in users_raw:
            display_name = user_data.get('displayName', '')
            email = user_data.get('emailAddress', '')
            account_id = user_data.get('accountId', '')
            
            user = JiraUser(
                account_id=account_id,
                display_name=display_name,
                email_address=email,
                active=user_data.get('active', True),
                account_type=user_data.get('accountType', 'atlassian')
            )
            users_found.append(user)
            
            # Verificar coincidencia exacta (más estricta)
            if (display_name.lower() == user_identifier.lower() or
                (email and email.lower() == user_identifier.lower()) or
                account_id == user_identifier):
                exact_match = user
        
        # Si hay coincidencia exacta, no requiere confirmación
        if exact_match:
            logfire.info("validate_jira_user validó usuario exacto: {display_name}",
                         display_name=exact_match.display_name)
            return UserSearchResult(
                users_found=users_found,
                total_found=len(users_found),
                search_query=user_identifier,
                exact_match=exact_match,
                suggestions=users_found[:5],
                requires_confirmation=False
            )
        
        # Si no hay coincidencia exacta, requiere confirmación
        suggestions = users_found[:5]
        confirmation_msg = f"No se encontró coincidencia exacta para '{user_identifier}'. "
        if suggestions:
            confirmation_msg += f"¿Te refieres a alguno de estos usuarios? Confirma cuál quieres usar."
        
        logfire.info("validate_jira_user requiere confirmación para: {user_identifier}, encontró {count} sugerencias",
                     user_identifier=user_identifier, count=len(suggestions))
        
        return UserSearchResult(
            users_found=users_found,
            total_found=len(users_found),
            search_query=user_identifier,
            exact_match=None,
            suggestions=suggestions,
            requires_confirmation=True,
            confirmation_message=confirmation_msg
        )
        
    except Exception as e:
        logfire.error("Error en validate_jira_user para '{user_identifier}': {error_message}",
                      user_identifier=user_identifier, error_message=str(e), exc_info=True)
        return UserSearchResult(
            users_found=[],
            total_found=0,
            search_query=user_identifier,
            exact_match=None,
            suggestions=[],
            requires_confirmation=False,
            confirmation_message=f"Error al buscar usuario '{user_identifier}': {str(e)}"
        )

async def get_all_worklog_hours_for_issue(
    issue_key: str = Field(..., description="Clave del issue (historia, tarea o subtarea), ej: 'PROJ-123'")
) -> IssueWorklogReport:
    """
    Obtiene todas las horas registradas en un issue, detalladas por usuario.
    Devuelve un reporte completo con el desglose de tiempo por cada usuario que trabajó en el issue.
    """
    logfire.info("Ejecutando get_all_worklog_hours_for_issue para: {issue_key}", issue_key=issue_key)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        # Obtener detalles del issue para el resumen
        with logfire.span("jira.issue_details_for_worklog", issue_key=issue_key):
            issue_data = await loop.run_in_executor(None, jira.issue, issue_key)
        
        if not issue_data:
            return IssueWorklogReport(
                issue_key=issue_key,
                issue_summary=f"Issue {issue_key} no encontrado",
                total_hours_all_users=0.0,
                total_seconds_all_users=0,
                total_worklog_entries=0,
                users_summary=[]
            )
        
        issue_summary = issue_data.get("fields", {}).get("summary", "Sin resumen")
        
        # Obtener todos los worklogs del issue
        with logfire.span("jira.get_all_worklogs", issue_key=issue_key):
            worklogs_data = await loop.run_in_executor(None, lambda: jira.issue_get_worklog(issue_key))
        
        if not worklogs_data or not worklogs_data.get('worklogs'):
            return IssueWorklogReport(
                issue_key=issue_key,
                issue_summary=issue_summary,
                total_hours_all_users=0.0,
                total_seconds_all_users=0,
                total_worklog_entries=0,
                users_summary=[]
            )
        
        # Agrupar worklogs por usuario
        users_worklog_data = {}
        total_seconds_all = 0
        total_entries = 0
        
        for worklog_raw in worklogs_data.get('worklogs', []):
            author = worklog_raw.get('author', {})
            user_display_name = author.get('displayName', 'Usuario desconocido')
            user_account_id = author.get('accountId') or author.get('name')
            
            # Crear clave única para el usuario
            user_key = f"{user_display_name}|{user_account_id or 'no-id'}"
            
            # Procesar comentario del worklog
            comment_from_response = worklog_raw.get('comment')
            comment_text = ""
            if isinstance(comment_from_response, str):
                comment_text = comment_from_response
            elif isinstance(comment_from_response, dict):
                try:
                    comment_text = comment_from_response['content'][0]['content'][0]['text']
                except:
                    comment_text = str(comment_from_response) if comment_from_response else ""
            
            # Crear objeto JiraWorklog
            worklog_obj = JiraWorklog(
                id=str(worklog_raw['id']),
                self_link=worklog_raw.get('self'),
                author=user_display_name,
                time_spent_seconds=worklog_raw.get('timeSpentSeconds', 0),
                started=worklog_raw.get('started'),
                comment=comment_text
            )
            
            # Acumular datos por usuario
            if user_key not in users_worklog_data:
                users_worklog_data[user_key] = {
                    'display_name': user_display_name,
                    'account_id': user_account_id,
                    'total_seconds': 0,
                    'worklogs': []
                }
            
            users_worklog_data[user_key]['total_seconds'] += worklog_raw.get('timeSpentSeconds', 0)
            users_worklog_data[user_key]['worklogs'].append(worklog_obj)
            
            total_seconds_all += worklog_raw.get('timeSpentSeconds', 0)
            total_entries += 1
        
        # Crear resúmenes por usuario
        users_summary = []
        for user_data in users_worklog_data.values():
            user_summary = UserWorklogSummary(
                user_display_name=user_data['display_name'],
                user_account_id=user_data['account_id'],
                total_hours=round(user_data['total_seconds'] / 3600, 2),
                total_seconds=user_data['total_seconds'],
                worklog_count=len(user_data['worklogs']),
                worklogs=user_data['worklogs']
            )
            users_summary.append(user_summary)
        
        # Ordenar usuarios por total de horas (descendente)
        users_summary.sort(key=lambda x: x.total_seconds, reverse=True)
        
        # Crear reporte final
        report = IssueWorklogReport(
            issue_key=issue_key,
            issue_summary=issue_summary,
            total_hours_all_users=round(total_seconds_all / 3600, 2),
            total_seconds_all_users=total_seconds_all,
            total_worklog_entries=total_entries,
            users_summary=users_summary
        )
        
        logfire.info("get_all_worklog_hours_for_issue completado para {issue_key}: {total_hours}h total, {user_count} usuarios",
                     issue_key=issue_key, total_hours=report.total_hours_all_users, user_count=len(users_summary))
        
        return report
        
    except Exception as e:
        logfire.error("Error en get_all_worklog_hours_for_issue para {issue_key}: {error_message}", 
                      issue_key=issue_key, error_message=str(e), exc_info=True)
        return IssueWorklogReport(
            issue_key=issue_key,
            issue_summary=f"Error al obtener worklogs: {str(e)}",
            total_hours_all_users=0.0,
            total_seconds_all_users=0,
            total_worklog_entries=0,
            users_summary=[]
        )

async def get_active_sprint_issues(
    project_key: Optional[str] = Field(default=None, description="Clave del proyecto para filtrar (ej: 'PSIMDESASW'). Si no se especifica, busca en todos los proyectos."),
    max_results: int = 20
) -> SprintIssues:
    """
    Obtiene todos los issues del sprint activo con información completa del sprint.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    project_key = _clean_field_info_param(project_key)
    
    actual_max_results = min(max(1, max_results), 100)
    
    # Construir JQL para sprint activo
    if project_key:
        jql_query = f'project = "{project_key}" AND sprint in openSprints() ORDER BY priority DESC, status ASC'
    else:
        jql_query = 'sprint in openSprints() ORDER BY priority DESC, status ASC'
    
    logfire.info("Ejecutando get_active_sprint_issues con JQL: {jql_query}", jql_query=jql_query)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        # Usar expand para obtener información del sprint
        with logfire.span("jira.sprint_search", jql=jql_query, limit=actual_max_results):
            issues_raw = await loop.run_in_executor(None, lambda: jira.jql(
                jql_query, 
                limit=actual_max_results,
                expand="changelog"
            ))
        
        if not issues_raw or not issues_raw.get("issues"):
            # Sprint activo sin issues o no encontrado
            default_sprint = JiraSprint(
                id="none", 
                name="No hay sprint activo", 
                state="none"
            )
            return SprintIssues(
                sprint=default_sprint,
                issues=[],
                total_issues=0,
                completed_issues=0,
                in_progress_issues=0
            )
        
        # Procesar issues
        issues_found: List[JiraIssue] = []
        issues_raw_data = issues_raw["issues"]
        sprint_info = None
        
        for issue_data in issues_raw_data:
            fields = issue_data.get("fields", {})
            assignee_info = fields.get("assignee")
            reporter_info = fields.get("reporter")
            
            # Extraer información del sprint del primer issue (todos deberían tener el mismo sprint activo)
            if not sprint_info:
                sprint_info = _get_sprint_data_from_issue(issue_data)
            
            issues_found.append(
                JiraIssue(
                    key=issue_data.get("key"),
                    summary=fields.get("summary"),
                    status=fields.get("status", {}).get("name"),
                    assignee=assignee_info.get("displayName") if assignee_info else None,
                    reporter=reporter_info.get("displayName") if reporter_info else None,
                    duedate=fields.get("duedate")
                )
            )
        
        # Si no pudimos extraer sprint, crear uno por defecto
        if not sprint_info:
            sprint_info = JiraSprint(
                id="unknown", 
                name="Sprint Activo", 
                state="active"
            )
        
        # Calcular métricas
        progress_data = _calculate_sprint_progress(issues_found, issues_raw_data)
        
        result = SprintIssues(
            sprint=sprint_info,
            issues=issues_found,
            total_issues=progress_data["total_issues"],
            completed_issues=progress_data["completed_issues"],
            in_progress_issues=progress_data["in_progress_issues"]
        )
        
        logfire.info("get_active_sprint_issues encontró {count} issues en sprint {sprint_name}", 
                     count=len(issues_found), sprint_name=sprint_info.name)
        return result
        
    except Exception as e:
        logfire.error("Error en get_active_sprint_issues: {error_message}", error_message=str(e), exc_info=True)
        error_sprint = JiraSprint(id="error", name="Error al obtener sprint", state="error")
        return SprintIssues(
            sprint=error_sprint,
            issues=[JiraIssue(key="ERROR", summary=f"Error al buscar issues del sprint: {str(e)}")],
            total_issues=0,
            completed_issues=0,
            in_progress_issues=0
        )

async def get_my_current_sprint_work(
    project_key: Optional[str] = Field(default=None, description="Clave del proyecto para filtrar (ej: 'PSIMDESASW')."),
    assignee: Optional[str] = Field(default=None, description="Usuario asignado. Si no se especifica, usa 'currentUser()'.")
) -> SprintIssues:
    """
    Obtiene los issues del sprint activo asignados al usuario especificado o actual.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    project_key = _clean_field_info_param(project_key)
    assignee = _clean_field_info_param(assignee)
    
    # Construir JQL para trabajo del usuario en sprint activo
    assignee_clause = f'assignee = "{assignee}"' if assignee else 'assignee = currentUser()'
    
    if project_key:
        jql_query = f'project = "{project_key}" AND sprint in openSprints() AND {assignee_clause} ORDER BY status ASC, priority DESC'
    else:
        jql_query = f'sprint in openSprints() AND {assignee_clause} ORDER BY status ASC, priority DESC'
    
    logfire.info("Ejecutando get_my_current_sprint_work con JQL: {jql_query}", jql_query=jql_query)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        with logfire.span("jira.my_sprint_work", jql=jql_query):
            issues_raw = await loop.run_in_executor(None, lambda: jira.jql(
                jql_query, 
                limit=50,
                expand="changelog"
            ))
        
        if not issues_raw or not issues_raw.get("issues"):
            # Usuario sin trabajo en sprint activo
            default_sprint = JiraSprint(
                id="none", 
                name="Sin trabajo asignado en sprint activo", 
                state="none"
            )
            return SprintIssues(
                sprint=default_sprint,
                issues=[],
                total_issues=0,
                completed_issues=0,
                in_progress_issues=0
            )
        
        # Procesar issues del usuario
        issues_found: List[JiraIssue] = []
        issues_raw_data = issues_raw["issues"]
        sprint_info = None
        
        for issue_data in issues_raw_data:
            fields = issue_data.get("fields", {})
            assignee_info = fields.get("assignee")
            reporter_info = fields.get("reporter")
            
            # Extraer información del sprint
            if not sprint_info:
                sprint_info = _get_sprint_data_from_issue(issue_data)
            
            issues_found.append(
                JiraIssue(
                    key=issue_data.get("key"),
                    summary=fields.get("summary"),
                    status=fields.get("status", {}).get("name"),
                    assignee=assignee_info.get("displayName") if assignee_info else None,
                    reporter=reporter_info.get("displayName") if reporter_info else None,
                    duedate=fields.get("duedate")
                )
            )
        
        # Sprint por defecto si no se pudo extraer
        if not sprint_info:
            user_name = assignee if assignee else "Usuario actual"
            sprint_info = JiraSprint(
                id="unknown", 
                name=f"Trabajo de {user_name}", 
                state="active"
            )
        
        # Calcular métricas
        progress_data = _calculate_sprint_progress(issues_found, issues_raw_data)
        
        result = SprintIssues(
            sprint=sprint_info,
            issues=issues_found,
            total_issues=progress_data["total_issues"],
            completed_issues=progress_data["completed_issues"],
            in_progress_issues=progress_data["in_progress_issues"]
        )
        
        logfire.info("get_my_current_sprint_work encontró {count} issues para el usuario en sprint {sprint_name}", 
                     count=len(issues_found), sprint_name=sprint_info.name)
        return result
        
    except Exception as e:
        logfire.error("Error en get_my_current_sprint_work: {error_message}", error_message=str(e), exc_info=True)
        error_sprint = JiraSprint(id="error", name="Error al obtener trabajo del sprint", state="error")
        return SprintIssues(
            sprint=error_sprint,
            issues=[JiraIssue(key="ERROR", summary=f"Error al buscar trabajo del sprint: {str(e)}")],
            total_issues=0,
            completed_issues=0,
            in_progress_issues=0
        )

async def get_sprint_progress(
    project_key: Optional[str] = Field(default=None, description="Clave del proyecto para filtrar (ej: 'PSIMDESASW')."),
    sprint_name: Optional[str] = Field(default=None, description="Nombre específico del sprint. Si no se especifica, usa el sprint activo.")
) -> SprintProgress:
    """
    Obtiene el progreso completo del sprint con métricas detalladas incluyendo story points.
    """
    # Limpiar parámetros que pueden llegar como FieldInfo
    project_key = _clean_field_info_param(project_key)
    sprint_name = _clean_field_info_param(sprint_name)
    
    # Construir JQL según si se especifica sprint específico o activo
    if sprint_name:
        base_jql = f'sprint = "{sprint_name}"'
    else:
        base_jql = 'sprint in openSprints()'
    
    if project_key:
        jql_query = f'project = "{project_key}" AND {base_jql} ORDER BY status ASC, priority DESC'
    else:
        jql_query = f'{base_jql} ORDER BY status ASC, priority DESC'
    
    logfire.info("Ejecutando get_sprint_progress con JQL: {jql_query}", jql_query=jql_query)
    
    try:
        jira = get_jira_client()
        loop = asyncio.get_running_loop()
        
        with logfire.span("jira.sprint_progress", jql=jql_query):
            issues_raw = await loop.run_in_executor(None, lambda: jira.jql(
                jql_query, 
                limit=200,  # Más límite para análisis completo
                expand="changelog"
            ))
        
        if not issues_raw or not issues_raw.get("issues"):
            # Sprint sin issues
            default_sprint = JiraSprint(
                id="none", 
                name=sprint_name or "Sprint no encontrado", 
                state="none"
            )
            return SprintProgress(
                sprint=default_sprint,
                total_issues=0,
                completed_issues=0,
                progress_percentage=0.0
            )
        
        # Procesar todos los issues para análisis completo
        issues_found: List[JiraIssue] = []
        issues_raw_data = issues_raw["issues"]
        sprint_info = None
        
        for issue_data in issues_raw_data:
            fields = issue_data.get("fields", {})
            assignee_info = fields.get("assignee")
            reporter_info = fields.get("reporter")
            
            # Extraer información del sprint
            if not sprint_info:
                sprint_info = _get_sprint_data_from_issue(issue_data)
            
            issues_found.append(
                JiraIssue(
                    key=issue_data.get("key"),
                    summary=fields.get("summary"),
                    status=fields.get("status", {}).get("name"),
                    assignee=assignee_info.get("displayName") if assignee_info else None,
                    reporter=reporter_info.get("displayName") if reporter_info else None,
                    duedate=fields.get("duedate")
                )
            )
        
        # Sprint por defecto si no se pudo extraer
        if not sprint_info:
            sprint_info = JiraSprint(
                id="unknown", 
                name=sprint_name or "Sprint Analizado", 
                state="active" if not sprint_name else "unknown"
            )
        
        # Calcular métricas completas con story points
        progress_data = _calculate_sprint_progress(issues_found, issues_raw_data)
        
        # Calcular días restantes desde la fecha del sprint
        days_remaining = None
        if sprint_info.end_date:
            try:
                end_date = datetime.fromisoformat(sprint_info.end_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if end_date > now:
                    days_remaining = (end_date.date() - now.date()).days
                elif end_date.date() == now.date():
                    days_remaining = 0
                else:
                    days_remaining = -1  # Sprint vencido
            except Exception:
                pass
        
        result = SprintProgress(
            sprint=sprint_info,
            total_story_points=progress_data["total_story_points"],
            completed_story_points=progress_data["completed_story_points"],
            total_issues=progress_data["total_issues"],
            completed_issues=progress_data["completed_issues"],
            progress_percentage=progress_data["progress_percentage"],
            days_remaining=days_remaining
        )
        
        logfire.info("get_sprint_progress analizó {count} issues del sprint {sprint_name} - {progress}% completado", 
                     count=len(issues_found), sprint_name=sprint_info.name, progress=progress_data["progress_percentage"])
        return result
        
    except Exception as e:
        logfire.error("Error en get_sprint_progress: {error_message}", error_message=str(e), exc_info=True)
        error_sprint = JiraSprint(id="error", name="Error al analizar progreso", state="error")
        return SprintProgress(
            sprint=error_sprint,
            total_issues=0,
            completed_issues=0,
            progress_percentage=0.0
        )

def _extract_story_points(issue_data: dict) -> Optional[int]:
    """Extrae story points de un issue de Jira."""
    try:
        fields = issue_data.get("fields", {})
        # Los story points suelen estar en customfield_10016 o similar
        # Probamos varias posibilidades comunes
        story_points_fields = [
            "customfield_10016", "customfield_10020", "customfield_10002", 
            "customfield_10008", "storyPoints", "story_points"
        ]
        
        for field_name in story_points_fields:
            if field_name in fields and fields[field_name] is not None:
                return int(float(fields[field_name]))
        return None
    except (ValueError, TypeError):
        return None

def _get_sprint_data_from_issue(issue_data: dict) -> Optional[JiraSprint]:
    """Extrae datos del sprint de un issue."""
    try:
        fields = issue_data.get("fields", {})
        sprint_field = fields.get("customfield_10020") or fields.get("sprint")
        
        if not sprint_field:
            return None
            
        # El campo sprint puede ser una lista de sprints
        if isinstance(sprint_field, list) and sprint_field:
            # Tomar el último sprint (generalmente el activo)
            sprint_info = sprint_field[-1]
        else:
            sprint_info = sprint_field
            
        if isinstance(sprint_info, dict):
            # Calcular días restantes si hay fecha de fin
            days_remaining = None
            if sprint_info.get("endDate"):
                try:
                    end_date = datetime.fromisoformat(sprint_info["endDate"].replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    if end_date > now:
                        days_remaining = (end_date.date() - now.date()).days
                except Exception:
                    pass
                    
            return JiraSprint(
                id=str(sprint_info.get("id", "unknown")),
                name=sprint_info.get("name", "Unknown Sprint"),
                state=sprint_info.get("state", "unknown").lower(),
                start_date=sprint_info.get("startDate"),
                end_date=sprint_info.get("endDate"),
                goal=sprint_info.get("goal")
            )
        return None
    except Exception:
        return None

def _calculate_sprint_progress(issues: List[JiraIssue], issues_raw_data: List[dict] = None) -> dict:
    """Calcula métricas de progreso del sprint."""
    total_issues = len(issues)
    completed_issues = sum(1 for issue in issues if issue.status and issue.status.lower() in ["done", "closed", "resolved"])
    in_progress_issues = sum(1 for issue in issues if issue.status and issue.status.lower() in ["in progress", "doing", "development"])
    
    # Calcular story points si tenemos datos raw
    total_story_points = None
    completed_story_points = None
    
    if issues_raw_data:
        story_points_list = []
        completed_story_points_list = []
        
        for i, issue_data in enumerate(issues_raw_data):
            if i < len(issues):
                sp = _extract_story_points(issue_data)
                if sp is not None:
                    story_points_list.append(sp)
                    if issues[i].status and issues[i].status.lower() in ["done", "closed", "resolved"]:
                        completed_story_points_list.append(sp)
        
        if story_points_list:
            total_story_points = sum(story_points_list)
            completed_story_points = sum(completed_story_points_list)
    
    # Calcular porcentaje de progreso
    progress_percentage = (completed_issues / total_issues * 100) if total_issues > 0 else 0.0
    
    return {
        "total_issues": total_issues,
        "completed_issues": completed_issues,
        "in_progress_issues": in_progress_issues,
        "total_story_points": total_story_points,
        "completed_story_points": completed_story_points,
        "progress_percentage": round(progress_percentage, 1)
    }



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