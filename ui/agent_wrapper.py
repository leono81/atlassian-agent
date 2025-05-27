# ui/agent_wrapper.py
import asyncio
import inspect
from typing import Any, Dict, List
from agent_core.main_agent import main_agent
import logfire

class SimpleAgentWrapper:
    """Wrapper simplificado para el agente - sin tracking automático de herramientas."""
    
    def __init__(self, original_agent):
        self.original_agent = original_agent
    
    async def run(self, prompt: str, message_history: List = None):
        """Ejecuta el agente de forma simple."""
        try:
            logfire.info("Ejecutando agente con prompt", prompt_length=len(prompt))
            result = await self.original_agent.run(prompt, message_history=message_history or [])
            logfire.info("Agente completado exitosamente")
            return result
        except Exception as e:
            logfire.error(f"Error en ejecución del agente: {e}", exc_info=True)
            raise

# Crear la instancia simplificada del agente
simple_agent = SimpleAgentWrapper(main_agent) 