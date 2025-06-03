# config/logging_context.py
"""
Sistema de logging robusto con contexto de usuario para aplicación multi-usuario.
Proporciona logging estructurado, correlation IDs, y trazabilidad por usuario.
"""

import logfire
import uuid
import time
import inspect
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextvars import ContextVar
from datetime import datetime
import threading

# Context variables para mantener el contexto a través de threads y async
current_user_context: ContextVar[Optional[str]] = ContextVar('current_user', default=None)
current_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
current_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)

class UserLoggingContext:
    """Gestor de contexto de logging por usuario con información estructurada."""
    
    _thread_local = threading.local()
    
    def __init__(self, user_id: str, session_id: Optional[str] = None, correlation_id: Optional[str] = None):
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.correlation_id = correlation_id or str(uuid.uuid4())[:12]
        self.start_time = time.time()
        
    def __enter__(self):
        """Establece el contexto de usuario para logging."""
        current_user_context.set(self.user_id)
        current_correlation_id.set(self.correlation_id)
        current_session_id.set(self.session_id)
        
        # También almacenar en thread local como backup
        UserLoggingContext._thread_local.user_id = self.user_id
        UserLoggingContext._thread_local.correlation_id = self.correlation_id
        UserLoggingContext._thread_local.session_id = self.session_id
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Limpia el contexto al salir."""
        # No limpiar las context vars para mantener el contexto
        # a través de la sesión del usuario
        pass

class StructuredLogger:
    """Logger estructurado con contexto de usuario automático."""
    
    @staticmethod
    def _get_caller_info() -> Dict[str, str]:
        """Obtiene información del módulo y función que llama al logger."""
        frame = inspect.currentframe()
        try:
            # Subir 3 niveles: _get_caller_info -> _log -> método público
            caller_frame = frame.f_back.f_back.f_back
            if caller_frame:
                module_name = caller_frame.f_globals.get('__name__', 'unknown')
                function_name = caller_frame.f_code.co_name
                line_number = caller_frame.f_lineno
                
                return {
                    'module': module_name,
                    'function': function_name,
                    'line': str(line_number)
                }
        finally:
            del frame
        
        return {'module': 'unknown', 'function': 'unknown', 'line': 'unknown'}
    
    @staticmethod
    def _get_user_context() -> Dict[str, Any]:
        """Obtiene el contexto de usuario actual."""
        context = {}
        
        # Intentar obtener de context vars
        try:
            user_id = current_user_context.get()
            correlation_id = current_correlation_id.get()
            session_id = current_session_id.get()
            
            if user_id:
                context['user_id'] = user_id
            if correlation_id:
                context['correlation_id'] = correlation_id
            if session_id:
                context['session_id'] = session_id
                
        except LookupError:
            # Fallback a thread local
            try:
                if hasattr(StructuredLogger._thread_local, 'user_id'):
                    context['user_id'] = StructuredLogger._thread_local.user_id
                if hasattr(StructuredLogger._thread_local, 'correlation_id'):
                    context['correlation_id'] = StructuredLogger._thread_local.correlation_id
                if hasattr(StructuredLogger._thread_local, 'session_id'):
                    context['session_id'] = StructuredLogger._thread_local.session_id
            except AttributeError:
                pass
        
        return context
    
    @staticmethod
    def _log(level: str, event: str, **kwargs):
        """Método interno para realizar el logging estructurado."""
        # Obtener información del caller
        caller_info = StructuredLogger._get_caller_info()
        
        # Obtener contexto de usuario
        user_context = StructuredLogger._get_user_context()
        
        # Construir el log estructurado
        log_data = {
            'event': event,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            **caller_info,
            **user_context,
            **kwargs
        }
        
        # Log usando logfire según el nivel
        if level == 'info':
            logfire.info(event, **log_data)
        elif level == 'error':
            logfire.error(event, **log_data)
        elif level == 'warning':
            logfire.warn(event, **log_data)
        elif level == 'debug':
            logfire.debug(event, **log_data)
        else:
            logfire.info(event, **log_data)
    
    @staticmethod
    def info(event: str, **kwargs):
        """Log de información con contexto estructurado."""
        StructuredLogger._log('info', event, **kwargs)
    
    @staticmethod
    def error(event: str, error: Optional[Exception] = None, **kwargs):
        """Log de error con contexto estructurado."""
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
        StructuredLogger._log('error', event, **kwargs)
    
    @staticmethod
    def warning(event: str, **kwargs):
        """Log de warning con contexto estructurado."""
        StructuredLogger._log('warning', event, **kwargs)
    
    @staticmethod
    def debug(event: str, **kwargs):
        """Log de debug con contexto estructurado."""
        StructuredLogger._log('debug', event, **kwargs)

# Instancia global del logger estructurado
logger = StructuredLogger()

def log_operation(operation_name: str, log_input: bool = False, log_output: bool = False):
    """
    Decorador para loguear automáticamente operaciones con contexto y métricas.
    
    Args:
        operation_name: Nombre de la operación para el log
        log_input: Si loguear los argumentos de entrada
        log_output: Si loguear el resultado de salida
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            operation_id = str(uuid.uuid4())[:8]
            
            # Log de inicio de operación
            log_data = {
                'operation_id': operation_id,
                'operation_type': 'start',
                'function_name': func.__name__
            }
            
            if log_input:
                log_data['input_args'] = str(args)[:200]  # Limitar tamaño
                log_data['input_kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
            
            logger.info(f"{operation_name}_started", **log_data)
            
            try:
                # Usar span de logfire para la operación
                with logfire.span(f"{operation_name}_operation", 
                                operation_id=operation_id,
                                function=func.__name__):
                    result = func(*args, **kwargs)
                
                # Log de éxito
                duration_ms = (time.time() - start_time) * 1000
                success_data = {
                    'operation_id': operation_id,
                    'operation_type': 'success',
                    'duration_ms': round(duration_ms, 2),
                    'function_name': func.__name__
                }
                
                if log_output and result is not None:
                    success_data['output'] = str(result)[:200]  # Limitar tamaño
                
                logger.info(f"{operation_name}_completed", **success_data)
                return result
                
            except Exception as e:
                # Log de error
                duration_ms = (time.time() - start_time) * 1000
                error_data = {
                    'operation_id': operation_id,
                    'operation_type': 'error',
                    'duration_ms': round(duration_ms, 2),
                    'function_name': func.__name__,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
                
                logger.error(f"{operation_name}_failed", error=e, **error_data)
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            operation_id = str(uuid.uuid4())[:8]
            
            # Log de inicio de operación
            log_data = {
                'operation_id': operation_id,
                'operation_type': 'start',
                'function_name': func.__name__,
                'is_async': True
            }
            
            if log_input:
                log_data['input_args'] = str(args)[:200]
                log_data['input_kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}
            
            logger.info(f"{operation_name}_started", **log_data)
            
            try:
                # Usar span de logfire para la operación async
                with logfire.span(f"{operation_name}_operation", 
                                operation_id=operation_id,
                                function=func.__name__,
                                is_async=True):
                    result = await func(*args, **kwargs)
                
                # Log de éxito
                duration_ms = (time.time() - start_time) * 1000
                success_data = {
                    'operation_id': operation_id,
                    'operation_type': 'success',
                    'duration_ms': round(duration_ms, 2),
                    'function_name': func.__name__,
                    'is_async': True
                }
                
                if log_output and result is not None:
                    success_data['output'] = str(result)[:200]
                
                logger.info(f"{operation_name}_completed", **success_data)
                return result
                
            except Exception as e:
                # Log de error
                duration_ms = (time.time() - start_time) * 1000
                error_data = {
                    'operation_id': operation_id,
                    'operation_type': 'error',
                    'duration_ms': round(duration_ms, 2),
                    'function_name': func.__name__,
                    'is_async': True,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
                
                logger.error(f"{operation_name}_failed", error=e, **error_data)
                raise
        
        # Retornar wrapper apropiado según si la función es async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Métricas de usuario para logfire
def log_user_action(action: str, **metadata):
    """Log específico para acciones de usuario con métricas."""
    user_context = StructuredLogger._get_user_context()
    
    action_data = {
        'action_type': action,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **user_context,
        **metadata
    }
    
    # Log la acción
    logger.info(f"user_action_{action}", **action_data)
    
    # También crear métrica en logfire si es apropiado
    if user_context.get('user_id'):
        with logfire.span(f"user_action", 
                         action=action, 
                         user_id=user_context['user_id']):
            pass  # El span automáticamente registra la métrica

def log_system_event(event: str, severity: str = 'info', **metadata):
    """Log específico para eventos del sistema."""
    system_data = {
        'event_type': 'system',
        'severity': severity,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **metadata
    }
    
    if severity == 'error':
        logger.error(f"system_{event}", **system_data)
    elif severity == 'warning':
        logger.warning(f"system_{event}", **system_data)
    else:
        logger.info(f"system_{event}", **system_data) 