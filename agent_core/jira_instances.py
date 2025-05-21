from atlassian import Jira
from config import settings
import logfire

# Aunque ya configuramos Logfire en ui/app.py, si este módulo se importa
# antes o se usa en un contexto sin Streamlit (ej. tests), es bueno tenerlo.
# Logfire es idempotente, así que llamarlo múltiples veces no es un problema.
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent",
    service_version="0.1.0" # Puedes versionar tu servicio
)
# Si atlassian-python-api usa httpx internamente y queremos trazas detalladas:
# logfire.instrument_httpx() # Descomentar si es necesario y se ha instalado httpx explícitamente.

# --- JIRA Client Instance ---
_jira_client = None

def get_jira_client() -> Jira:
    """
    Retorna una instancia inicializada y autenticada del cliente Jira.
    Utiliza un patrón singleton simple para evitar reinicializaciones.
    """
    global _jira_client
    if _jira_client is None:
        if not all([settings.JIRA_URL, settings.JIRA_USERNAME, settings.JIRA_API_TOKEN]):
            logfire.error("Credenciales de Jira no configuradas completamente en .env")
            raise ValueError("Credenciales de Jira no configuradas completamente. Revisa tu archivo .env.")
        try:
            with logfire.span("jira_client.initialization"):
                _jira_client = Jira(
                    url=settings.JIRA_URL,
                    username=settings.JIRA_USERNAME,
                    password=settings.JIRA_API_TOKEN, # 'password' se usa para el API token aquí
                    cloud=True # Asumimos Jira Cloud, ajustar si es Server
                )
                # Probar la conexión (opcional pero recomendado)
                user = _jira_client.myself()
                logfire.info("Cliente Jira inicializado y conectado exitosamente como {user_displayName}", user_displayName=user.get('displayName'))
        except Exception as e:
            logfire.error("Error al inicializar el cliente Jira: {error_message}", error_message=str(e), exc_info=True)
            _jira_client = None # Asegurar que no se use una instancia fallida
            raise ConnectionError(f"No se pudo conectar a Jira: {e}")
    return _jira_client

if __name__ == "__main__":
    # Prueba rápida para verificar la inicialización del cliente Jira
    try:
        print("Intentando inicializar el cliente Jira...")
        jira = get_jira_client()
        print(f"Cliente Jira inicializado. Usuario: {jira.myself().get('displayName')}")
        
        # Ejemplo: Obtener todos los proyectos accesibles para probar
        print("\nObteniendo todos los proyectos accesibles (esto puede tardar un momento)...")
        # projects = jira.projects() # Devuelve un generador
        all_projects = jira.get_all_projects() # Intenta obtener todos los proyectos

        if all_projects:
            print(f"Se encontraron {len(all_projects)} proyectos.")
            print("Primeros 5 proyectos accesibles (o todos si son menos de 5):")
            for project in all_projects[:5]: # Mostrar solo los primeros 5
                print(f"- {project['name']} (Key: {project['key']})")
        else:
            print("No se encontraron proyectos o no hay acceso.")

    except ValueError as e:
        print(f"Error de configuración: {e}")
    except ConnectionError as e:
        print(f"Error de conexión: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}")
        # Imprimir el traceback para más detalles en caso de error
        import traceback
        traceback.print_exc()