# agent_core/confluence_instances.py

from atlassian import Confluence
from config import settings
import logfire

# Configuración de Logfire (similar a jira_instances.py)
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent",
    service_version="0.1.0"
)
# logfire.instrument_httpx() # Descomentar si es necesario

# --- Confluence Client Instance ---
_confluence_client = None

def get_confluence_client() -> Confluence:
    """
    Retorna una instancia inicializada y autenticada del cliente Confluence.
    Utiliza un patrón singleton simple para evitar reinicializaciones.
    """
    global _confluence_client
    if _confluence_client is None:
        if not all([settings.CONFLUENCE_URL, settings.CONFLUENCE_USERNAME, settings.CONFLUENCE_API_TOKEN]):
            logfire.error("Credenciales de Confluence no configuradas completamente en .env")
            raise ValueError("Credenciales de Confluence no configuradas completamente. Revisa tu archivo .env.")
        try:
            with logfire.span("confluence_client.initialization"):
                _confluence_client = Confluence(
                    url=settings.CONFLUENCE_URL,
                    username=settings.CONFLUENCE_USERNAME,
                    password=settings.CONFLUENCE_API_TOKEN, # API Token
                    cloud=True # Assuming Confluence Cloud. Adjust if using Server.
                )
                # Probar la conexión intentando obtener al menos un espacio
                spaces_data = _confluence_client.get_all_spaces(limit=1)
                if spaces_data and spaces_data.get('results'):
                    logfire.info("Cliente Confluence inicializado y conectado exitosamente. Acceso a espacios confirmado.")
                elif spaces_data: # La llamada fue exitosa pero no devolvió 'results' o estaba vacío
                    logfire.info("Cliente Confluence inicializado. Conexión establecida, pero no se encontraron espacios accesibles o la respuesta de espacios está vacía.")
                else: # spaces_data es None o False, lo que indicaría un problema más serio
                    logfire.warn("Cliente Confluence inicializado, pero la llamada a get_all_spaces no devolvió datos. Verificar permisos o configuración.")

        except Exception as e:
            logfire.error(f"Error al inicializar el cliente Confluence: {e}", exc_info=True)
            _confluence_client = None
            raise ConnectionError(f"No se pudo conectar a Confluence: {e}")
    return _confluence_client

def check_confluence_connection() -> tuple[bool, str]:
    """
    Verifica la conexión con Confluence intentando obtener información del servidor.
    Retorna una tupla (status: bool, message: str).
    """
    try:
        # Attempt to get a new client instance for a fresh check
        # This avoids relying on a potentially stale global _confluence_client state for the check itself
        if not all([settings.CONFLUENCE_URL, settings.CONFLUENCE_USERNAME, settings.CONFLUENCE_API_TOKEN]):
             message = "Credenciales de Confluence no configuradas para el health check."
             logfire.warn(message)
             return False, message
        
        with logfire.span("confluence_client.health_check"):
            client_check = Confluence(
                url=settings.CONFLUENCE_URL,
                username=settings.CONFLUENCE_USERNAME,
                password=settings.CONFLUENCE_API_TOKEN,
                cloud=True
            )
            spaces_data = client_check.get_all_spaces(limit=1)

        if spaces_data and spaces_data.get('results'):
            message = f"Conexión a Confluence exitosa. Acceso a espacios confirmado."
            #logfire.info(message)
            return True, message
        elif spaces_data: # Conectado pero sin resultados de espacios, o formato inesperado
            message = "Conexión a Confluence establecida, pero no se pudo confirmar el acceso a espacios (get_all_spaces no devolvió resultados esperados)."
            #logfire.warn(message)
            # Consideramos éxito si la llamada no falló, aunque no haya espacios.
            # La instancia del cliente está probablemente bien.
            return True, message 
        else: # spaces_data es None o False, indica fallo en la llamada.
            message = "No se pudo conectar a Confluence o verificar el acceso a espacios (get_all_spaces falló o no devolvió datos)."
            logfire.error(message)
            return False, message
            
    except ConnectionError as e:
        message = f"Error de conexión con Confluence durante el health check: {e}"
        logfire.error(message, exc_info=True)
        return False, message
    except Exception as e:
        message = f"Error inesperado al verificar la conexión con Confluence: {e}."
        logfire.error(message, exc_info=True)
        return False, message

if __name__ == "__main__":
    try:
        print("Intentando inicializar el cliente Confluence (get_confluence_client)...")
        # Test the main get_confluence_client first
        confluence = get_confluence_client()
        if confluence:
            print(f"get_confluence_client() exitoso.")
        else:
            print(f"get_confluence_client() falló.")

        print("\n--- Prueba de Health Check Confluence (check_confluence_connection) ---")
        status, msg = check_confluence_connection()
        print(f"Estado del Health Check: {'OK' if status else 'Error'}")
        print(f"Mensaje del Health Check: {msg}")
        print("--- Fin Prueba de Health Check Confluence ---")

    except ValueError as e:
        print(f"Error de configuración: {e}")
    except ConnectionError as e:
        print(f"Error de conexión: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}")
        import traceback
        traceback.print_exc()