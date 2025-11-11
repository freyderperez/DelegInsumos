"""
DelegInsumos - Sistema de Logging Centralizado
Maneja el registro de eventos, errores y operaciones del sistema
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.config_manager import config


class DelegInsumosLogger:
    """
    Logger centralizado del sistema con configuración automática
    basada en settings.json
    """
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str = 'deleginsumos') -> logging.Logger:
        """
        Obtiene o crea un logger con la configuración del sistema.
        
        Args:
            name: Nombre del logger (por defecto: 'deleginsumos')
            
        Returns:
            Instancia de logger configurado
        """
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        
        return cls._loggers[name]
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """Crea y configura un nuevo logger"""
        # Obtener configuración de logging
        log_config = config.get_logging_config()
        
        # Crear logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_config.get('nivel', 'INFO')))
        
        # Evitar duplicar handlers
        if logger.handlers:
            return logger
        
        # Configurar formato
        formatter = logging.Formatter(
            log_config.get('formato', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo
        log_file = log_config.get('archivo', './logs/deleginsumos.log')
        cls._ensure_log_directory(log_file)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_tamaño_mb', 10) * 1024 * 1024,  # MB a bytes
            backupCount=log_config.get('cantidad_respaldos', 5),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola (solo errores críticos)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.ERROR)
        
        # Agregar handlers al logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    @classmethod
    def _ensure_log_directory(cls, log_file_path: str) -> None:
        """Crea el directorio de logs si no existe"""
        log_dir = Path(log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)


class LoggerMixin:
    """
    Mixin para agregar capacidades de logging a cualquier clase
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Obtiene el logger para la clase actual"""
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__.lower()
            self._logger = DelegInsumosLogger.get_logger(f'deleginsumos.{class_name}')
        return self._logger


def log_operation(operation_name: str, details: str = "", level: str = "INFO"):
    """
    Función de conveniencia para registrar operaciones del sistema.
    
    Args:
        operation_name: Nombre de la operación
        details: Detalles adicionales
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = DelegInsumosLogger.get_logger()
    log_method = getattr(logger, level.lower())
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"OPERACIÓN: {operation_name}"
    if details:
        message += f" | DETALLES: {details}"
    
    log_method(message)


def log_database_operation(operation: str, table: str, record_id: Optional[str] = None, 
                         changes: Optional[dict] = None):
    """
    Registra operaciones de base de datos para auditoría.
    
    Args:
        operation: Tipo de operación (CREATE, READ, UPDATE, DELETE)
        table: Tabla afectada
        record_id: ID del registro (opcional)
        changes: Diccionario con los cambios realizados (opcional)
    """
    logger = DelegInsumosLogger.get_logger('deleginsumos.database')
    
    details = f"Tabla: {table}"
    if record_id:
        details += f" | ID: {record_id}"
    if changes:
        details += f" | Cambios: {changes}"
    
    logger.info(f"DB_{operation}: {details}")


def log_user_action(action: str, component: str, details: Optional[str] = None):
    """
    Registra acciones del usuario en la interfaz.
    
    Args:
        action: Acción realizada
        component: Componente de la UI
        details: Detalles adicionales (opcional)
    """
    logger = DelegInsumosLogger.get_logger('deleginsumos.ui')
    
    message = f"ACCIÓN_USUARIO: {action} en {component}"
    if details:
        message += f" | {details}"
    
    logger.info(message)


def log_error(error_type: str, message: str, component: str, 
              exception: Optional[Exception] = None):
    """
    Registra errores del sistema con contexto adicional.
    
    Args:
        error_type: Tipo de error
        message: Mensaje del error
        component: Componente donde ocurrió el error
        exception: Excepción original (opcional)
    """
    logger = DelegInsumosLogger.get_logger()
    
    error_msg = f"ERROR_{error_type}: {message} | Componente: {component}"
    
    if exception:
        logger.error(error_msg, exc_info=True)
    else:
        logger.error(error_msg)


def log_system_startup():
    """Registra el inicio del sistema con información del entorno"""
    logger = DelegInsumosLogger.get_logger()
    
    system_info = config.get_system_info()
    
    logger.info("="*80)
    logger.info(f"INICIO DEL SISTEMA: {system_info['nombre']} v{system_info['version']}")
    logger.info(f"Descripción: {system_info['descripcion']}")
    logger.info(f"Autor: {system_info['autor']}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*80)


def log_system_shutdown():
    """Registra el cierre del sistema"""
    logger = DelegInsumosLogger.get_logger()
    
    logger.info("="*80)
    logger.info("CIERRE DEL SISTEMA")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("="*80)


# Instancia del logger principal para uso directo
main_logger = DelegInsumosLogger.get_logger()

# Configurar logging al importar el módulo
if __name__ == "__main__":
    # Ejemplo de uso
    test_logger = DelegInsumosLogger.get_logger('test')
    test_logger.info("Sistema de logging inicializado correctamente")
    
    log_operation("PRUEBA_LOGGING", "Verificación del sistema de logs")
    log_database_operation("CREATE", "insumos", "1", {"nombre": "Papel A4"})
    log_user_action("CLICK", "btnGuardar", "Guardando nuevo insumo")
    log_error("VALIDATION", "Campo requerido vacío", "FormInsumos")