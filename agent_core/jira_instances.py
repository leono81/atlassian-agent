from atlassian import Jira
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

# --- JIRA Client Instance ---
# _jira_client = None # Eliminamos el singleton global

def get_jira_client(username: Optional[str] = None, api_key: Optional[str] = None) -> Jira:
    """
    Retorna una instancia inicializada y autenticada del cliente Jira.
    Si se proveen username y api_key, se usan esas credenciales.
    De lo contrario, recurre a las configuraciones globales en settings.
    """
    # global _jira_client # Ya no es global
    # if _jira_client is None: # Ya no es singleton

    jira_url = settings.JIRA_URL
    jira_user = username if username else settings.JIRA_USERNAME
    jira_token = api_key if api_key else settings.JIRA_API_TOKEN

    if not all([jira_url, jira_user, jira_token]):
        # Solo loggear si las credenciales fueron explícitamente provistas
        if username and api_key:
            logfire.error("Credenciales de Jira (URL, Username, Token) no configuradas completamente.")
        raise ValueError("Credenciales de Jira no configuradas completamente. Revisa tu configuración.")
    
    try:
        with logfire.span("jira_client.initialization", user=jira_user):
            client = Jira(
                url=jira_url,
                username=jira_user,
                password=jira_token, # 'password' se usa para el API token aquí
                cloud=True # Asumimos Jira Cloud, ajustar si es Server
            )
            # Probar la conexión (opcional pero recomendado)
            user_info = client.myself()
            logfire.info(f"Cliente Jira inicializado y conectado exitosamente para el usuario {jira_user} (displayName: {user_info.get('displayName')})")
            return client
    except Exception as e:
        logfire.error(f"Error al inicializar el cliente Jira para {jira_user}: {e}", exc_info=True)
        # _jira_client = None # Ya no es global
        raise ConnectionError(f"No se pudo conectar a Jira para {jira_user}: {e}")
    # return _jira_client # Ya no es global

def check_jira_connection(username: Optional[str] = None, api_key: Optional[str] = None) -> tuple[bool, str]:
    """
    Verifica la conexión con Jira intentando obtener los detalles del usuario actual.
    Si se proveen credenciales específicas, las usa. Si no, usa las globales.
    Retorna una tupla (status: bool, message: str).
    """
    try:
        # Usar credenciales específicas si se proveen, sino las globales
        client = get_jira_client(username, api_key)
        if client:
            user = client.myself()
            if user and user.get('displayName'):
                message = f"Conexión a Jira exitosa. Usuario: {user.get('displayName')}."
                return True, message
            else:
                message = "Conexión a Jira establecida, pero no se pudo obtener información del usuario."
                logfire.warn(message)
                return False, message
        else:
            message = "No se pudo obtener el cliente Jira para verificar la conexión."
            logfire.error(message)
            return False, message
    except ValueError as e:
        # Si las credenciales no están configuradas, no es un error crítico durante health check silencioso
        return False, str(e)
    except ConnectionError as e:
        message = f"Error de conexión con Jira: {e}"
        logfire.error(message, exc_info=True)
        return False, message
    except Exception as e:
        message = f"Error inesperado al verificar la conexión con Jira: {e}"
        logfire.error(message, exc_info=True)
        return False, message

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

        # Probar la nueva función de health check
        print("\n--- Prueba de Health Check Jira ---")
        status, msg = check_jira_connection()
        print(f"Estado: {'OK' if status else 'Error'}")
        print(f"Mensaje: {msg}")
        print("--- Fin Prueba de Health Check Jira ---")

    except ValueError as e:
        print(f"Error de configuración: {e}")
    except ConnectionError as e:
        print(f"Error de conexión: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}")
        # Imprimir el traceback para más detalles en caso de error
        import traceback
        traceback.print_exc()