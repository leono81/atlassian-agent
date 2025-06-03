# agent_core/confluence_instances.py

from atlassian import Confluence
from config import settings
import logfire
from typing import Optional

# Configuración de Logfire (similar a jira_instances.py)
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    service_name="jira_confluence_agent",
    service_version="0.1.0"
)
# logfire.instrument_httpx() # Descomentar si es necesario

# --- Confluence Client Instance ---
# _confluence_client = None # Eliminamos el singleton global para permitir instancias por usuario

def get_confluence_client(username: Optional[str] = None, api_key: Optional[str] = None) -> Confluence:
    """
    Retorna una instancia inicializada y autenticada del cliente Confluence.
    Si se proveen username y api_key, se usan esas credenciales.
    De lo contrario, recurre a las configuraciones globales en settings.
    """
    # global _confluence_client # Ya no es global
    # if _confluence_client is None: # Ya no es singleton
    
    confluence_url = settings.CONFLUENCE_URL
    confluence_user = username if username else settings.CONFLUENCE_USERNAME
    confluence_token = api_key if api_key else settings.CONFLUENCE_API_TOKEN

    if not all([confluence_url, confluence_user, confluence_token]):
        logfire.error("Credenciales de Confluence (URL, Username, Token) no configuradas completamente.")
        raise ValueError("Credenciales de Confluence no configuradas completamente. Revisa tu configuración.")
    
    try:
        with logfire.span("confluence_client.initialization", user=confluence_user):
            client = Confluence(
                url=confluence_url,
                username=confluence_user,
                password=confluence_token, # API Token
                cloud=True # Assuming Confluence Cloud. Adjust if using Server.
            )
            # Probar la conexión intentando obtener al menos un espacio
            # Esta prueba es importante para asegurar que las credenciales (de usuario o globales) son válidas
            spaces_data = client.get_all_spaces(limit=1)
            if spaces_data and spaces_data.get('results'):
                logfire.info(f"Cliente Confluence inicializado y conectado exitosamente para el usuario {confluence_user}. Acceso a espacios confirmado.")
            elif spaces_data:
                logfire.info(f"Cliente Confluence inicializado para {confluence_user}. Conexión establecida, pero no se encontraron espacios accesibles o la respuesta está vacía.")
            else:
                logfire.warn(f"Cliente Confluence inicializado para {confluence_user}, pero get_all_spaces no devolvió datos. Verificar permisos.")
            return client
    except Exception as e:
        logfire.error(f"Error al inicializar el cliente Confluence para {confluence_user}: {e}", exc_info=True)
        # _confluence_client = None # Ya no es global
        raise ConnectionError(f"No se pudo conectar a Confluence para {confluence_user}: {e}")
    # return _confluence_client # Ya no es global

def check_confluence_connection() -> tuple[bool, str]:
    """
    Verifica la conexión con Confluence intentando obtener información del servidor.
    Retorna una tupla (status: bool, message: str).
    """
    try:
        # Attempt to get a new client instance for a fresh check
        # This avoids relying on a potentially stale global _confluence_client state for the check itself
        # Para el health check, seguimos usando las globales por ahora, ya que es una verificación del sistema.
        # Si se quisiera un health check por usuario, esta función debería aceptar credenciales también.
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