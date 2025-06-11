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
PYDANTIC_AI_MODEL = os.getenv("PYDANTIC_AI_MODEL", "openai:gpt-4.1-mini") # Default model

# Timezone Configuration
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Mem0 Configuration
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

def validate_config():
    """Valida que las configuraciones esenciales estén presentes."""
    required_jira = [JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]
    required_confluence = [CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN]

    if not all(required_jira):
        raise ValueError("Faltan variables de entorno para Jira. Revisa JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN.")
    if not all(required_confluence):
        raise ValueError("Faltan variables de entorno para Confluence. Revisa CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN.")
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

def parse_datetime_robust(datetime_str, fallback_to_now=True):
    """
    Parsea una fecha de forma robusta manejando múltiples formatos y usando la zona horaria configurada.
    
    Args:
        datetime_str: String con la fecha a parsear. Puede ser None, 'ahora', o formato ISO
        fallback_to_now: Si True, retorna datetime.now() en caso de error
    
    Returns:
        datetime object con la zona horaria configurada
    """
    from datetime import datetime, timezone
    import re
    
    # Si es None o 'ahora', retornar fecha actual
    if not datetime_str or (isinstance(datetime_str, str) and datetime_str.lower() == 'ahora'):
        return datetime.now(get_timezone())
    
    try:
        # Limpiar string de entrada
        clean_str = str(datetime_str).strip()
        
        # Normalizar formatos comunes de zona horaria
        # Convertir .000+0000 a +00:00
        clean_str = re.sub(r'\.(\d{3})\+0000$', r'+00:00', clean_str)
        # Convertir .000-0300 a -03:00  
        clean_str = re.sub(r'\.(\d{3})([+-])(\d{2})(\d{2})$', r'\2\3:\4', clean_str)
        # Convertir Z a +00:00
        clean_str = clean_str.replace("Z", "+00:00")
        
        # Intentar parsear con fromisoformat
        parsed_dt = datetime.fromisoformat(clean_str)
        
        # Si no tiene zona horaria, asignar la configurada
        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=get_timezone())
        else:
            # Convertir a la zona horaria configurada
            parsed_dt = parsed_dt.astimezone(get_timezone())
        
        return parsed_dt
        
    except Exception as e:
        if fallback_to_now:
            # Log del error para debugging pero seguir funcionando
            return datetime.now(get_timezone())
        else:
            raise ValueError(f"No se pudo parsear la fecha '{datetime_str}': {str(e)}")

def format_datetime_for_jira(dt):
    """
    Formatea un datetime para que sea compatible con la API de Jira.
    
    Args:
        dt: datetime object
    
    Returns:
        String en formato ISO 8601 compatible con Jira
    """
    # Jira espera formato: YYYY-MM-DDTHH:MM:SS.000+ZZZZ
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000%z")

if __name__ == "__main__":
    # Para probar que la carga funciona
    try:
        validate_config()
        print(f"Jira URL: {JIRA_URL}")
        print(f"Confluence URL: {CONFLUENCE_URL}")
        print(f"Logfire Token: {'Presente' if LOGFIRE_TOKEN else 'No presente'}")
        print(f"Pydantic AI Model: {PYDANTIC_AI_MODEL}")
        print(f"Timezone: {TIMEZONE}")
        
        # Probar funciones de fecha
        print("\n--- Pruebas de manejo de fechas ---")
        test_dates = [
            None,
            'ahora',
            '2025-06-12T12:00:00-03:00',
            '2025-06-12T00:00:00.000+0000',
            '2024-07-30T14:30:00+02:00'
        ]
        
        for test_date in test_dates:
            try:
                parsed = parse_datetime_robust(test_date)
                formatted = format_datetime_for_jira(parsed)
                print(f"Input: {test_date} -> Parsed: {parsed} -> Jira format: {formatted}")
            except Exception as e:
                print(f"Error con {test_date}: {e}")
                
    except ValueError as e:
        print(f"Error de configuración: {e}")