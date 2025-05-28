import os
from dotenv import load_dotenv

# Intentar cargar desde .env primero (desarrollo local)
load_dotenv()

# Función para obtener variables de entorno con fallback a Streamlit secrets
def get_env_var(key: str, default: str = None):
    """
    Obtiene una variable de entorno, con fallback a Streamlit secrets si está disponible.
    """
    # Primero intentar desde variables de entorno
    value = os.getenv(key, default)
    
    # Si no está disponible y estamos en Streamlit, intentar desde secrets
    if value is None or value == default:
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and key in st.secrets:
                value = st.secrets[key]
        except (ImportError, AttributeError, KeyError):
            pass
    
    return value

# Jira Configuration
JIRA_URL = get_env_var("JIRA_URL")
JIRA_USERNAME = get_env_var("JIRA_USERNAME")
JIRA_API_TOKEN = get_env_var("JIRA_API_TOKEN")

# Confluence Configuration
CONFLUENCE_URL = get_env_var("CONFLUENCE_URL")
CONFLUENCE_USERNAME = get_env_var("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = get_env_var("CONFLUENCE_API_TOKEN")

# OpenAI Configuration (CRÍTICO para PydanticAI)
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY")

# Logfire Configuration
LOGFIRE_TOKEN = get_env_var("LOGFIRE_TOKEN")

# PydanticAI Model (opcional, puedes definirlo directamente en el agente)
PYDANTIC_AI_MODEL = get_env_var("PYDANTIC_AI_MODEL", "openai:gpt-4o-mini")

# Timezone Configuration
TIMEZONE = get_env_var("TIMEZONE", "UTC")

# Mem0 Configuration
MEM0_API_KEY = get_env_var("MEM0_API_KEY")

# Asegurar que OpenAI API Key esté disponible como variable de entorno
# (PydanticAI la busca directamente en os.environ)
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

def validate_config():
    """Valida que las configuraciones esenciales estén presentes."""
    required_jira = [JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]
    required_confluence = [CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN]

    if not all(required_jira):
        raise ValueError("Faltan variables de entorno para Jira. Revisa JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN.")
    if not all(required_confluence):
        raise ValueError("Faltan variables de entorno para Confluence. Revisa CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN.")
    
    if not OPENAI_API_KEY:
        raise ValueError("Falta OPENAI_API_KEY. Es requerida para PydanticAI.")
    
    print("Configuración de entorno cargada correctamente.")

def get_timezone():
    """Devuelve un objeto de zona horaria según TIMEZONE, o UTC si no está definida o es inválida."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(TIMEZONE)
    except Exception:
        try:
            import pytz
            return pytz.timezone(TIMEZONE)
        except Exception:
            from datetime import timezone
            return timezone.utc

if __name__ == "__main__":
    # Para probar que la carga funciona
    try:
        validate_config()
        print(f"Jira URL: {JIRA_URL}")
        print(f"Confluence URL: {CONFLUENCE_URL}")
        print(f"OpenAI API Key: {'Presente' if OPENAI_API_KEY else 'No presente'}")
        print(f"Logfire Token: {'Presente' if LOGFIRE_TOKEN else 'No presente'}")
        print(f"Pydantic AI Model: {PYDANTIC_AI_MODEL}")
    except ValueError as e:
        print(f"Error de configuración: {e}")