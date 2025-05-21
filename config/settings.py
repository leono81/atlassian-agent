import os
from dotenv import load_dotenv

load_dotenv() # Carga variables desde el archivo .env

# Jira Configuration
JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Confluence Configuration
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")

# Logfire Configuration
LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")

# PydanticAI Model (opcional, puedes definirlo directamente en el agente)
PYDANTIC_AI_MODEL = os.getenv("PYDANTIC_AI_MODEL", "openai:gpt-4o-mini") # Default model

def validate_config():
    """Valida que las configuraciones esenciales estén presentes."""
    required_jira = [JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]
    required_confluence = [CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN]

    if not all(required_jira):
        raise ValueError("Faltan variables de entorno para Jira. Revisa JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN.")
    if not all(required_confluence):
        raise ValueError("Faltan variables de entorno para Confluence. Revisa CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN.")
    print("Configuración de entorno cargada correctamente.")

if __name__ == "__main__":
    # Para probar que la carga funciona
    try:
        validate_config()
        print(f"Jira URL: {JIRA_URL}")
        print(f"Confluence URL: {CONFLUENCE_URL}")
        print(f"Logfire Token: {'Presente' if LOGFIRE_TOKEN else 'No presente'}")
        print(f"Pydantic AI Model: {PYDANTIC_AI_MODEL}")
    except ValueError as e:
        print(f"Error de configuración: {e}")