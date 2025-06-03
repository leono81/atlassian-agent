# config/logfire_instrumentation.py
"""
Configuración avanzada de instrumentación de Logfire para aplicación multi-usuario.
Proporciona instrumentación automática, métricas personalizadas y monitoreo completo.
"""

import logfire
from config import settings
from config.logging_context import logger, log_system_event
from typing import Optional, Dict, Any
import time
import threading
import os
from datetime import datetime

# Import opcional de psutil para monitoreo del sistema
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

class LogfireInstrumentation:
    """Gestor de instrumentación avanzada de Logfire."""
    
    _instance = None
    _configured = False
    _metrics_thread = None
    _stop_metrics = threading.Event()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._configured:
            self._setup_logfire()
            self._setup_custom_metrics()
            self._configured = True
    
    def _setup_logfire(self):
        """Configura Logfire con instrumentación completa."""
        try:
            if not settings.LOGFIRE_TOKEN:
                log_system_event('logfire_token_missing', 
                               severity='warning',
                               component='instrumentation')
                return
            
            # Configuración principal de Logfire
            logfire.configure(
                token=settings.LOGFIRE_TOKEN,
                send_to_logfire="if-token-present",
                service_name="atlassian_agent_multi_user",
                service_version="1.0.0",
                # Configuración avanzada
                console=logfire.ConsoleOptions(
                    colors='auto',
                    verbose=False,
                    include_timestamps=True
                )
            )
            
            # Lista de instrumentaciones disponibles
            enabled_instrumentations = []
            
            # Instrumentación automática de PydanticAI
            try:
                logfire.instrument_pydantic_ai()
                enabled_instrumentations.append('pydantic_ai')
            except (AttributeError, Exception) as e:
                logger.warning('instrumentation_not_available', instrumentation='pydantic_ai', error=str(e))
            
            # Instrumentación de HTTPX para llamadas a APIs de Atlassian
            try:
                logfire.instrument_httpx(
                    capture_request_headers=True,
                    capture_response_headers=True,
                    capture_request_body=False,  # Por seguridad con credenciales
                    capture_response_body=False  # Por rendimiento
                )
                enabled_instrumentations.append('httpx')
            except (AttributeError, Exception) as e:
                logger.warning('instrumentation_not_available', instrumentation='httpx', error=str(e))
            
            # Instrumentación de SQLite3 para base de datos de credenciales
            try:
                logfire.instrument_sqlite3()
                enabled_instrumentations.append('sqlite3')
            except (AttributeError, Exception) as e:
                logger.warning('instrumentation_not_available', instrumentation='sqlite3', error=str(e))
            
            # Instrumentación de requests para APIs HTTP
            try:
                logfire.instrument_requests()
                enabled_instrumentations.append('requests')
            except (AttributeError, Exception) as e:
                logger.warning('instrumentation_not_available', instrumentation='requests', error=str(e))
            
            # Instrumentación de métricas del sistema
            try:
                logfire.instrument_system_metrics()
                enabled_instrumentations.append('system_metrics')
            except (AttributeError, Exception) as e:
                logger.warning('instrumentation_not_available', instrumentation='system_metrics', error=str(e))
            
            log_system_event('logfire_instrumentation_configured',
                           component='instrumentation',
                           instrumentations=enabled_instrumentations)
            
        except Exception as e:
            log_system_event('logfire_configuration_failed',
                           severity='error',
                           error=str(e),
                           component='instrumentation')
    
    def _setup_custom_metrics(self):
        """Configura métricas personalizadas para la aplicación."""
        try:
            # Métricas de contador para acciones de usuario
            self.user_actions_counter = logfire.metric_counter(
                'user_actions_total',
                unit='1',
                description='Total number of user actions performed'
            )
            
            # Métricas de latencia para operaciones de Jira/Confluence
            self.atlassian_operation_latency = logfire.metric_histogram(
                'atlassian_operation_duration_ms',
                unit='ms',
                description='Duration of Atlassian API operations in milliseconds'
            )
            
            # Métricas de errores por servicio
            self.service_errors_counter = logfire.metric_counter(
                'service_errors_total',
                unit='1',
                description='Total number of errors by service'
            )
            
            # Métricas de usuarios activos
            self.active_users_gauge = logfire.metric_up_down_counter(
                'active_users',
                unit='1',
                description='Number of currently active users'
            )
            
            # Métricas de sistema (CPU, memoria)
            self.system_cpu_gauge = logfire.metric_gauge(
                'system_cpu_usage_percent',
                unit='%',
                description='System CPU usage percentage'
            )
            
            self.system_memory_gauge = logfire.metric_gauge(
                'system_memory_usage_mb',
                unit='MB',
                description='System memory usage in megabytes'
            )
            
            log_system_event('custom_metrics_configured',
                           component='instrumentation',
                           metrics_count=6)
            
        except Exception as e:
            log_system_event('metrics_configuration_failed',
                           severity='error',
                           error=str(e),
                           component='instrumentation')
    
    def start_system_monitoring(self, interval_seconds: int = 30):
        """Inicia el monitoreo automático del sistema."""
        if not PSUTIL_AVAILABLE:
            log_system_event('system_monitoring_skipped',
                           component='instrumentation',
                           reason='psutil_not_available')
            return
            
        if self._metrics_thread is not None:
            return
        
        def _collect_system_metrics():
            while not self._stop_metrics.wait(interval_seconds):
                try:
                    # Recopilar métricas del sistema
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_info = psutil.virtual_memory()
                    memory_mb = memory_info.used / (1024 * 1024)
                    
                    # Enviar métricas a Logfire
                    self.system_cpu_gauge.set(cpu_percent)
                    self.system_memory_gauge.set(memory_mb)
                    
                    # Log de métricas del sistema cada 5 minutos
                    if int(time.time()) % 300 == 0:  # Cada 5 minutos
                        logger.info('system_metrics_collected',
                                   cpu_percent=cpu_percent,
                                   memory_mb=round(memory_mb, 2),
                                   memory_percent=memory_info.percent)
                
                except Exception as e:
                    logger.error('system_metrics_collection_failed', error=e)
        
        self._metrics_thread = threading.Thread(target=_collect_system_metrics, daemon=True)
        self._metrics_thread.start()
        
        log_system_event('system_monitoring_started',
                       component='instrumentation',
                       interval_seconds=interval_seconds)
    
    def stop_system_monitoring(self):
        """Detiene el monitoreo automático del sistema."""
        if self._metrics_thread is not None:
            self._stop_metrics.set()
            self._metrics_thread.join(timeout=5)
            self._metrics_thread = None
            self._stop_metrics.clear()
            
            log_system_event('system_monitoring_stopped',
                           component='instrumentation')
    
    def record_user_action(self, action: str, **attributes):
        """Registra una acción de usuario en las métricas."""
        try:
            self.user_actions_counter.add(1, action=action, **attributes)
        except Exception as e:
            logger.error('user_action_metric_failed', error=e, action=action)
    
    def record_atlassian_operation(self, operation: str, duration_ms: float, success: bool, **attributes):
        """Registra una operación de Atlassian en las métricas."""
        try:
            self.atlassian_operation_latency.record(duration_ms, 
                                                   operation=operation,
                                                   success=success,
                                                   **attributes)
            
            if not success:
                self.service_errors_counter.add(1, 
                                               service='atlassian',
                                               operation=operation,
                                               **attributes)
        except Exception as e:
            logger.error('atlassian_operation_metric_failed', error=e, operation=operation)
    
    def record_service_error(self, service: str, error_type: str, **attributes):
        """Registra un error de servicio en las métricas."""
        try:
            self.service_errors_counter.add(1,
                                           service=service,
                                           error_type=error_type,
                                           **attributes)
        except Exception as e:
            logger.error('service_error_metric_failed', error=e, service=service)
    
    def track_user_session(self, user_id: str, action: str):
        """Rastrea sesiones de usuario (login/logout)."""
        try:
            if action == 'login':
                self.active_users_gauge.add(1)
                logger.info('user_session_started', 
                           user_id=user_id,
                           session_action=action)
            elif action == 'logout':
                self.active_users_gauge.add(-1)
                logger.info('user_session_ended',
                           user_id=user_id,
                           session_action=action)
        except Exception as e:
            logger.error('user_session_tracking_failed', error=e, user_id=user_id, action=action)
    
    def create_custom_span(self, operation_name: str, **attributes):
        """Crea un span personalizado de Logfire con atributos."""
        return logfire.span(operation_name, **attributes)
    
    def log_performance_alert(self, metric_name: str, value: float, threshold: float, **context):
        """Registra una alerta de rendimiento cuando se exceden umbrales."""
        logger.warning('performance_alert',
                      metric=metric_name,
                      value=value,
                      threshold=threshold,
                      exceeded_by=value - threshold,
                      **context)
        
        # También crear una métrica específica para alertas
        try:
            alert_counter = logfire.metric_counter(
                'performance_alerts_total',
                unit='1',
                description='Total number of performance alerts triggered'
            )
            alert_counter.add(1, metric=metric_name, **context)
        except Exception as e:
            logger.error('performance_alert_metric_failed', error=e)

# Instancia global de instrumentación
instrumentation = LogfireInstrumentation()

def get_instrumentation() -> LogfireInstrumentation:
    """Obtiene la instancia global de instrumentación."""
    return instrumentation

def setup_application_monitoring():
    """Configura el monitoreo completo de la aplicación."""
    instr = get_instrumentation()
    instr.start_system_monitoring()
    
    # Definir características de monitoreo según disponibilidad
    monitoring_features = ['user_actions', 'api_latency', 'error_tracking']
    if PSUTIL_AVAILABLE:
        monitoring_features.append('system_metrics')
    
    log_system_event('application_monitoring_enabled',
                   component='instrumentation',
                   monitoring_features=monitoring_features,
                   psutil_available=PSUTIL_AVAILABLE)

def shutdown_monitoring():
    """Cierra el monitoreo de la aplicación."""
    instr = get_instrumentation()
    instr.stop_system_monitoring()
    
    log_system_event('application_monitoring_disabled',
                   component='instrumentation')

# Decorador para instrumentación automática de funciones
def instrument_function(operation_name: str, record_metrics: bool = True):
    """
    Decorador para instrumentar automáticamente funciones con spans y métricas.
    
    Args:
        operation_name: Nombre de la operación para el span
        record_metrics: Si registrar métricas de latencia
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            with instrumentation.create_custom_span(operation_name, 
                                                   function=func.__name__) as span:
                try:
                    result = func(*args, **kwargs)
                    
                    if record_metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        instrumentation.record_atlassian_operation(
                            operation_name, duration_ms, True
                        )
                    
                    return result
                    
                except Exception as e:
                    if record_metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        instrumentation.record_atlassian_operation(
                            operation_name, duration_ms, False, error_type=type(e).__name__
                        )
                    raise
        
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            with instrumentation.create_custom_span(operation_name, 
                                                   function=func.__name__,
                                                   is_async=True) as span:
                try:
                    result = await func(*args, **kwargs)
                    
                    if record_metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        instrumentation.record_atlassian_operation(
                            operation_name, duration_ms, True
                        )
                    
                    return result
                    
                except Exception as e:
                    if record_metrics:
                        duration_ms = (time.time() - start_time) * 1000
                        instrumentation.record_atlassian_operation(
                            operation_name, duration_ms, False, error_type=type(e).__name__
                        )
                    raise
        
        # Retornar wrapper apropiado
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator 