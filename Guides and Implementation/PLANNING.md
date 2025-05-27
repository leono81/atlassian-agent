## 1. Visión del Producto
Crear un agente conversacional inteligente y eficiente que permita a los usuarios interactuar con Jira y Confluence mediante lenguaje natural, simplificando la gestión de tareas y el acceso a la información.

## 2. Arquitectura General
- **Núcleo del Agente:** PydanticAI Agent.
- **Interfaz de Usuario (UI):** Streamlit.
- **Herramientas (Tools):** Módulos específicos para interactuar con APIs de Jira y Confluence, utilizando PydanticAI tools.
- **Logging/Observabilidad:** Logfire.
- **Comunicación Inter-Agente:** Preparado para el protocolo A2A (actuando como servidor A2A).
- **Gestión de Configuración:** Variables de entorno para API keys y URLs.


## 3. Tech Stack
- **Lenguaje:** Python 3.10+
- **Framework del Agente:** PydanticAI
- **UI:** Streamlit
- **APIs Externas:** Jira REST API, Confluence REST API
- **Bibliotecas Clientes API:** atlassian-python-api
- **Logging:** Logfire SDK
- **Testing:** pytest
- **Gestión de Dependencias:** uv / pip + venv

## 4. Módulos Principales (Propuesta Inicial)
- `agent_core/`: Lógica principal del agente PydanticAI.
  - `main_agent.py`: Definición del agente principal.
  - `jira_instances.py`: (Nuevo) Inicialización y configuración de instancias de cliente Jira.
  - `confluence_instances.py`: (Nuevo) Inicialización y configuración de instancias de cliente Confluence.
- `tools/`: Herramientas PydanticAI.
  - `jira_tools.py`: Herramientas para Jira (usarán `jira_instances`).
  - `confluence_tools.py`: Herramientas para Confluence (usarán `confluence_instances`).
  - `common_tools.py`: (Opcional) Herramientas comunes, ej. MCP Time Server.
- `ui/`: Código de la interfaz Streamlit.
  - `app.py`: Aplicación principal de Streamlit.
- `a2a/`: (Para preparación A2A)
  - `a2a_server.py`: Lógica para exponer el agente vía A2A.
  - `agent_card.json`: Definición de la AgentCard.
- `config/`: Gestión de configuración.
  - `settings.py`: Carga de variables de entorno.
- `tests/`: Pruebas unitarias e de integración.
- `main.py`: Punto de entrada para lanzar la aplicación Streamlit.
- `README.md`, `PLANNING.md`, `TASK.md`

## 5. Herramientas Específicas (Ejemplos a Implementar)
### Jira:
  - `search_issues(jql_query: str, max_results: int = 50) -> list`
  - `get_issue_details(issue_key: str) -> dict`
  - `create_issue(project_key: str, summary: str, issue_type: str, description: str = None) -> dict`
  - `add_comment_to_issue(issue_key: str, comment_body: str) -> dict`
  - `get_project_list() -> list`
  - ... (más según la documentación de "Jira module")
### Confluence:
  - `search_pages(query: str, space_key: str = None, max_results: int = 10) -> list`
  - `get_page_content(page_id: str) -> str`
  - `create_page(space_key: str, title: str, body_content: str, parent_id: str = None) -> dict`
  - `update_page(page_id: str, new_title: str = None, new_body_content: str = None, new_version: bool = True) -> dict`
  - ... (más según la documentación de "Confluence module")
### (Opcional) MCP Time Server:
  - `get_current_time(timezone: str = "UTC") -> str`
  - `convert_time(time_str: str, from_tz: str, to_tz: str) -> str`

## 6. Consideraciones de A2A
- El agente se diseñará para poder actuar como un A2A Server.
- Se definirá una `AgentCard` básica.
- Se implementarán stubs para los endpoints JSON-RPC 2.0 (`message/send`, `tasks/get`).

## 7. Logging con Logfire
- Configurar Logfire al inicio de la aplicación.
- Instrumentar PydanticAI y otras bibliotecas relevantes (ej. HTTPX si se usa directamente).
- Usar `logfire.span` para trazas personalizadas en operaciones clave.

## 8. Gestión de "Golden Rules"
- Se seguirán activamente durante todo el ciclo de desarrollo.
- Las revisiones de código (si aplica) verificarán su cumplimiento.
- Los archivos `PLANNING.md` y `TASK.md` se mantendrán actualizados.

## 9. Variables de Entorno
- `JIRA_URL`
- `JIRA_USERNAME`
- `JIRA_API_TOKEN`
- `CONFLUENCE_URL`
- `CONFLUENCE_USERNAME`
- `CONFLUENCE_API_TOKEN`
- `LOGFIRE_TOKEN` (si se envía a la plataforma Logfire)
- (Opcional) `MCP_TIME_SERVER_URL`