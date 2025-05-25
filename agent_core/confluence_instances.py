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
                    password=settings.CONFLUENCE_API_TOKEN,
                    cloud=True 
                )
                # Probar la conexión
                # get_all_spaces devuelve un dict con una lista en 'results'
                spaces_data = _confluence_client.get_all_spaces(limit=1)
                if spaces_data and spaces_data.get('results'):
                    first_space_result = spaces_data['results'][0] # Acceder al primer elemento de la lista
                    logfire.info(
                        "Cliente Confluence inicializado y conectado exitosamente.", 
                        space_name=first_space_result.get('name')
                    )
                else:
                     logfire.info("Cliente Confluence inicializado, pero no se encontraron espacios o no hay acceso (puede ser normal).")

        except Exception as e:
            logfire.error("Error al inicializar el cliente Confluence: {error_message}", error_message=str(e), exc_info=True)
            _confluence_client = None 
            raise ConnectionError(f"No se pudo conectar a Confluence: {e}")
    return _confluence_client

if __name__ == "__main__":
    # Prueba rápida para verificar la inicialización del cliente Confluence
    try:
        print("Intentando inicializar el cliente Confluence...")
        confluence = get_confluence_client()
        print("Cliente Confluence inicializado.")

        # Ejemplo: Obtener los primeros 5 espacios para probar
        print("\nObteniendo los primeros 5 espacios accesibles...")
        spaces_data = confluence.get_all_spaces(limit=5) # Este método debería funcionar con limit
        
        if spaces_data and spaces_data.get('results'):
            print(f"Se encontraron {len(spaces_data['results'])} espacios (hasta un máximo de 5).")
            print("Espacios accesibles:")
            for space in spaces_data['results']:
                print(f"- {space['name']} (Key: {space['key']})")
        else:
            print("No se encontraron espacios o no hay acceso.")

    except ValueError as e:
        print(f"Error de configuración: {e}")
    except ConnectionError as e:
        print(f"Error de conexión: {e}")
    except Exception as e:
        print(f"Un error inesperado ocurrió: {e}")
        import traceback
        traceback.print_exc()