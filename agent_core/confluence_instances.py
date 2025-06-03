# agent_core/confluence_instances.py

from atlassian import Confluence
from config import settings
import logfire
from typing import Optional

# Configuración condicional de Logfire para evitar duplicados
def _configure_logfire_if_needed():
    """Configura Logfire solo si es necesario para evitar logs duplicados"""
    try:
        # Verificar si ya está configurado comprobando si hay un token
        if hasattr(logfire, '_configured') and getattr(logfire, '_configured', False):
            return
        
        if settings.LOGFIRE_TOKEN:
            logfire.configure(
                token=settings.LOGFIRE_TOKEN,
                send_to_logfire="if-token-present",
                service_name="jira_confluence_agent",
                service_version="0.1.0"
            )
            setattr(logfire, '_configured', True)
    except Exception:
        # Si hay error configurando logfire, continuar sin él
        pass

_configure_logfire_if_needed()

# --- Confluence Client Instance ---

def get_confluence_client(username: Optional[str] = None, api_key: Optional[str] = None) -> Confluence:
    """
    Retorna una instancia inicializada y autenticada del cliente Confluence.
    Si se proveen username y api_key, se usan esas credenciales.
    De lo contrario, recurre a las configuraciones globales en settings.
    """
    confluence_url = settings.CONFLUENCE_URL
    confluence_user = username if username else settings.CONFLUENCE_USERNAME
    confluence_token = api_key if api_key else settings.CONFLUENCE_API_TOKEN

    if not all([confluence_url, confluence_user, confluence_token]):
        # Solo loggear si las credenciales fueron explícitamente provistas
        if username and api_key:
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
        raise ConnectionError(f"No se pudo conectar a Confluence para {confluence_user}: {e}")

def check_confluence_connection(username: Optional[str] = None, api_key: Optional[str] = None) -> tuple[bool, str]:
    """
    Verifica la conexión con Confluence intentando obtener información del servidor.
    Si se proveen credenciales específicas, las usa. Si no, usa las globales.
    Retorna una tupla (status: bool, message: str).
    """
    try:
        # Usar credenciales específicas si se proveen, sino las globales
        if username and api_key:
            confluence_url = settings.CONFLUENCE_URL
            confluence_user = username
            confluence_token = api_key
        else:
            confluence_url = settings.CONFLUENCE_URL
            confluence_user = settings.CONFLUENCE_USERNAME
            confluence_token = settings.CONFLUENCE_API_TOKEN
        
        if not all([confluence_url, confluence_user, confluence_token]):
            return False, "Credenciales de Confluence no configuradas para el health check."
        
        with logfire.span("confluence_client.health_check"):
            client_check = Confluence(
                url=confluence_url,
                username=confluence_user,
                password=confluence_token,
                cloud=True
            )
            spaces_data = client_check.get_all_spaces(limit=1)

        if spaces_data and spaces_data.get('results'):
            message = f"Conexión a Confluence exitosa. Acceso a espacios confirmado."
            return True, message
        elif spaces_data: # Conectado pero sin resultados de espacios, o formato inesperado
            message = "Conexión a Confluence establecida, pero no se pudo confirmar el acceso a espacios (get_all_spaces no devolvió resultados esperados)."
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