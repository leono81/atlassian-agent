# TASK - Agente Conversacional Jira/Confluence

## Hito 1: Setup y Núcleo del Agente (Read-Only)

### En Progreso:
-   [X] **Tarea 0.1**: Configurar entorno de desarrollo (Python, uv/venv, git). *(Asumimos que esto se hará ahora)*
-   [X] **Tarea 0.2**: Crear estructura inicial de directorios y archivos (`PLANNING.md` actualizado, `TASK.md` actualizado, `README.md`).
-   [X] **Tarea 0.3**: Inicializar Logfire básico.
-   [X] **Tarea 0.4**: (Nuevo) Añadir `atlassian-python-api` a las dependencias del proyecto.

### Pendiente:
-   [X] **Tarea 1.1**: Implementar `agent_core/jira_instances.py` para inicializar y configurar el cliente Jira de `atlassian-python-api` usando variables de entorno.
-   [X] **Tarea 1.2**: Implementar `agent_core/confluence_instances.py` para inicializar y configurar el cliente Confluence de `atlassian-python-api` usando variables de entorno.
-   [X] **Tarea 1.3**: Crear `tools/jira_tools.py` con Pydantic models y 2-3 herramientas de lectura (ej. `search_issues`, `get_issue_details`) utilizando la instancia del cliente Jira.
    -   [ ] Sub-Tarea 1.3.1: Tests unitarios para `jira_tools.py` (mockeando las llamadas a `atlassian-python-api`).
-   [X] **Tarea 1.4**: Crear `tools/confluence_tools.py` con Pydantic models y 2-3 herramientas de lectura (ej. `search_pages`, `get_page_content`) utilizando la instancia del cliente Confluence.
    -   [ ] Sub-Tarea 1.4.1: Tests unitarios para `confluence_tools.py` (mockeando las llamadas a `atlassian-python-api`).
-   [X] **Tarea 1.5**: Crear `agent_core/main_agent.py` con la definición del PydanticAI `Agent` e integrar las herramientas de lectura y las instancias de cliente.
-   [X] **Tarea 1.6**: Implementar `config/settings.py` para cargar variables de entorno (JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, etc.).

## Hito 2: UI Básica y Conversación

### Pendiente:
-   [X] **Tarea 2.1**: Desarrollar `ui/app.py` con Streamlit: entrada de texto y área de respuesta simple.
-   [X] **Tarea 2.2**: Integrar el agente con la UI de Streamlit para un ciclo de request/response.
-   [ ] **Tarea 2.3**: Implementar gestión de historial de chat en el agente y visualización en Streamlit.
-   [ ] **Tarea 2.4**: Tests básicos de interacción UI-Agente.

## Hito 3: Expansión de Herramientas (Escritura y Avanzadas)

### Pendiente:
-   [X] **Tarea 3.1**: Añadir herramientas de escritura a `jira_tools.py` (ej. `create_issue`, `add_comment`).
    -   [X] Sub-Tarea 3.1.1: Tests unitarios.
-   [X] **Tarea 3.2**: Añadir herramientas de escritura a `confluence_tools.py` (ej. `create_page`).
    -   [X] Sub-Tarea 3.2.1: Tests unitarios.
-   [X] **Tarea 3.3**: Refinar el prompt del sistema del agente para mejorar el razonamiento y la selección de herramientas.

## Hito 4: Preparación A2A y Refinamientos

### Pendiente:
-   [ ] **Tarea 4.1**: Definir `a2a/agent_card.json`.
-   [ ] **Tarea 4.2**: Implementar stubs básicos en `a2a/a2a_server.py` (ej. usando FastAPI) para los endpoints A2A.
-   [ ] **Tarea 4.3**: Mejorar la visualización de resultados en Streamlit (tablas, markdown).

## Backlog / Ideas Futuras:
-   [ ] Integración completa de MCP Time Server si se valida su necesidad.
-   [ ] Soporte para subida/descarga de adjuntos.
-   [ ] Gestión de permisos más granular.
-   [ ] Streaming de respuestas en Streamlit.
-   [ ] Autenticación de usuarios en la app Streamlit.