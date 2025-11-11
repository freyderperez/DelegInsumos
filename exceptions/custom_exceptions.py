"""
DelegInsumos - Excepciones Personalizadas
Define excepciones específicas del sistema para manejo de errores controlado
"""

class DelegInsumosException(Exception):
    """Excepción base del sistema DelegInsumos"""
    def __init__(self, message: str, code: str = "GENERAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class DatabaseException(DelegInsumosException):
    """Excepciones relacionadas con la base de datos"""
    def __init__(self, message: str, code: str = "DB_ERROR"):
        super().__init__(message, code)

class DatabaseConnectionException(DatabaseException):
    """Error de conexión a la base de datos"""
    def __init__(self, message: str = "No se pudo conectar a la base de datos"):
        super().__init__(message, "DB_CONNECTION_ERROR")

class DatabaseIntegrityException(DatabaseException):
    """Error de integridad de datos en la base de datos"""
    def __init__(self, message: str = "Error de integridad en la base de datos"):
        super().__init__(message, "DB_INTEGRITY_ERROR")

class DatabaseMigrationException(DatabaseException):
    """Error durante migración de base de datos"""
    def __init__(self, message: str = "Error en la migración de base de datos"):
        super().__init__(message, "DB_MIGRATION_ERROR")

class ValidationException(DelegInsumosException):
    """Excepciones de validación de datos"""
    def __init__(self, field: str, message: str):
        self.field = field
        full_message = f"Error de validación en '{field}': {message}"
        super().__init__(full_message, "VALIDATION_ERROR")

class BusinessLogicException(DelegInsumosException):
    """Excepciones de lógica de negocio"""
    def __init__(self, message: str):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")

class InsufficientStockException(BusinessLogicException):
    """Stock insuficiente para realizar la operación"""
    def __init__(self, insumo_nombre: str, stock_actual: int, cantidad_solicitada: int):
        message = (f"Stock insuficiente para '{insumo_nombre}'. "
                  f"Disponible: {stock_actual}, Solicitado: {cantidad_solicitada}")
        super().__init__(message)
        self.insumo_nombre = insumo_nombre
        self.stock_actual = stock_actual
        self.cantidad_solicitada = cantidad_solicitada

class DuplicateRecordException(BusinessLogicException):
    """Registro duplicado en el sistema"""
    def __init__(self, entity: str, field: str, value: str):
        message = f"Ya existe un {entity} con {field}: '{value}'"
        super().__init__(message)
        self.entity = entity
        self.field = field
        self.value = value

class RecordNotFoundException(BusinessLogicException):
    """Registro no encontrado"""
    def __init__(self, entity: str, identifier: str):
        message = f"No se encontró {entity} con identificador: '{identifier}'"
        super().__init__(message)
        self.entity = entity
        self.identifier = identifier

class ServiceException(DelegInsumosException):
    """Excepciones de la capa de servicios"""
    def __init__(self, service: str, message: str):
        self.service = service
        full_message = f"Error en servicio '{service}': {message}"
        super().__init__(full_message, "SERVICE_ERROR")

class UIException(DelegInsumosException):
    """Excepciones de la interfaz de usuario"""
    def __init__(self, component: str, message: str):
        self.component = component
        full_message = f"Error en UI '{component}': {message}"
        super().__init__(full_message, "UI_ERROR")

class ReportGenerationException(DelegInsumosException):
    """Error en la generación de reportes"""
    def __init__(self, report_type: str, message: str):
        self.report_type = report_type
        full_message = f"Error generando reporte '{report_type}': {message}"
        super().__init__(full_message, "REPORT_ERROR")

class BackupException(DelegInsumosException):
    """Excepciones del sistema de backup"""
    def __init__(self, operation: str, message: str):
        self.operation = operation
        full_message = f"Error en backup '{operation}': {message}"
        super().__init__(full_message, "BACKUP_ERROR")

class ConfigurationException(DelegInsumosException):
    """Error de configuración del sistema"""
    def __init__(self, config_key: str, message: str = "Configuración inválida"):
        self.config_key = config_key
        full_message = f"Error de configuración en '{config_key}': {message}"
        super().__init__(full_message, "CONFIG_ERROR")

class FileOperationException(DelegInsumosException):
    """Excepciones de operaciones de archivos"""
    def __init__(self, operation: str, filepath: str, message: str):
        self.operation = operation
        self.filepath = filepath
        full_message = f"Error en operación '{operation}' del archivo '{filepath}': {message}"
        super().__init__(full_message, "FILE_ERROR")

# Función auxiliar para manejo centralizado de errores
def handle_exception(exception: Exception, logger=None) -> str:
    """
    Maneja excepciones de forma centralizada.
    
    Args:
        exception: La excepción a manejar
        logger: Logger opcional para registrar el error
        
    Returns:
        Mensaje de error formateado para mostrar al usuario
    """
    if isinstance(exception, DelegInsumosException):
        error_msg = f"[{exception.code}] {exception.message}"
    else:
        error_msg = f"Error inesperado: {str(exception)}"
    
    if logger:
        logger.error(f"Exception: {error_msg}", exc_info=True)
    
    return error_msg

# Decorador para manejo automático de excepciones en servicios
def service_exception_handler(service_name: str):
    """
    Decorador para capturar y convertir excepciones en ServiceException
    
    Args:
        service_name: Nombre del servicio para identificación
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DelegInsumosException:
                # Re-lanzar excepciones del sistema tal como están
                raise
            except Exception as e:
                # Convertir excepciones genéricas en ServiceException
                raise ServiceException(service_name, str(e))
        return wrapper
    return decorator