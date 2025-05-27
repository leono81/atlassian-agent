# ui/agent_status_tracker.py
import streamlit as st
from typing import Optional
from dataclasses import dataclass

@dataclass
class CurrentStatus:
    """Representa el estado actual del agente."""
    action: str
    details: str
    icon: str
    is_running: bool = True

class AgentStatusDisplay:
    """Display simple para mostrar solo el estado actual del agente."""
    
    def __init__(self):
        self.current_status: Optional[CurrentStatus] = None
    
    def reset(self):
        """Reinicia el display."""
        self.current_status = None
    
    def update_status(self, action: str, icon: str, details: str, is_running: bool = True):
        """Actualiza el estado actual."""
        self.current_status = CurrentStatus(
            action=action,
            details=details,
            icon=icon,
            is_running=is_running
        )
    
    def start(self, message: str = "Iniciando..."):
        """Inicia el procesamiento."""
        self.update_status(message, "🚀", "Preparando el agente...", True)
    
    def finish(self, message: str = "Completado"):
        """Finaliza el procesamiento."""
        self.update_status(message, "✅", "Respuesta generada exitosamente", False)
    
    def get_current_status(self) -> Optional[CurrentStatus]:
        """Obtiene el estado actual."""
        return self.current_status

# Instancia global
status_display = AgentStatusDisplay()

def render_current_status(display: AgentStatusDisplay):
    """Renderiza solo el estado actual del agente en una línea simple."""
    current = display.get_current_status()
    
    if not current:
        return None
    
    # Mostrar solo una línea simple con el estado actual
    if current.is_running:
        st.markdown(f"🔄 {current.icon} {current.details}")
    else:
        st.markdown(f"✅ {current.icon} {current.details}")

# Funciones de conveniencia
def start_agent_process(message: str = "Procesando tu consulta..."):
    """Inicia el proceso del agente."""
    status_display.start(message)

def update_agent_status(action: str, icon: str, details: str):
    """Actualiza el estado del agente."""
    status_display.update_status(action, icon, details, True)

def finish_agent_process(message: str = "Respuesta lista"):
    """Finaliza el proceso del agente."""
    status_display.finish(message)

# Funciones específicas para cada tipo de acción
def track_context_building():
    """Trackea la construcción del contexto."""
    update_agent_status("Construyendo contexto", "📋", "Recopilando información del usuario...")

def track_memory_search(query: str = ""):
    """Trackea una búsqueda en memoria."""
    details = f"Buscando: '{query[:30]}...'" if query and len(query) > 30 else "Buscando información relevante..."
    update_agent_status("Consultando memoria", "🧠", details)

def track_tool_execution(tool_name: str):
    """Trackea la ejecución de una herramienta."""
    tool_icons = {
        "jira_search": "🎫",
        "jira_details": "📋", 
        "jira_comment": "💬",
        "jira_worklog": "⏱️",
        "confluence_search": "📚",
        "confluence_content": "📄",
        "save_memory": "💾",
        "search_memory": "🔍"
    }
    
    icon = tool_icons.get(tool_name, "🔧")
    display_name = tool_name.replace('_', ' ').title()
    update_agent_status("Ejecutando herramienta", icon, f"Usando {display_name}")

def track_llm_thinking():
    """Trackea el procesamiento del LLM."""
    update_agent_status("Analizando consulta", "🤔", "El agente está procesando la información...")

def track_response_generation():
    """Trackea la generación de la respuesta final."""
    update_agent_status("Generando respuesta", "✍️", "Formulando la respuesta final...") 