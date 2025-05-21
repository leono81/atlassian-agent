# Agente Conversacional Jira/Confluence

Este proyecto implementa un agente conversacional construido con PydanticAI para interactuar con Jira y Confluence utilizando lenguaje natural. La interfaz de usuario se desarrolla con Streamlit y la observabilidad se gestiona con Logfire.

## Características (Planeadas)
- Consultar issues de Jira (búsqueda, detalles).
- Crear y modificar issues en Jira (crear, comentar).
- Buscar y leer páginas de Confluence.
- Crear y modificar páginas en Confluence.
- Interfaz de chat amigable.
- Preparado para comunicación A2A.

## Stack Tecnológico
- Python 3.10+
- PydanticAI
- Streamlit
- atlassian-python-api
- Logfire
- uv (para gestión de dependencias y entorno)

## Configuración
1.  Clona el repositorio.
2.  Crea un entorno virtual e instala las dependencias:
    ```bash
    uv venv
    uv pip install -e .[dev]
    # o si solo quieres las dependencias de producción:
    # uv pip install -e .
    ```
3.  Crea un archivo `.env` en la raíz del proyecto, basándote en `.env.example`, y completa tus credenciales y URLs para Jira y Confluence.

## Ejecución
Para iniciar la aplicación Streamlit:
```bash
streamlit run ui/app.py
