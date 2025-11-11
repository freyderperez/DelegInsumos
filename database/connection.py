"""
DelegInsumos - Manejador de Conexiones de Base de Datos
Gestiona conexiones SQLite con pool de conexiones y transacciones
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Any, List, Dict
from pathlib import Path

from config.config_manager import config
from exceptions.custom_exceptions import (
    DatabaseConnectionException, 
    DatabaseIntegrityException
)
from utils.logger import LoggerMixin, log_database_operation


class DatabaseConnection(LoggerMixin):
    """
    Manejador de conexiones SQLite con pool de conexiones thread-safe
    """
    
    _instance: Optional['DatabaseConnection'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'DatabaseConnection':
        """Implementación Singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el manejador de conexiones"""
        if getattr(self, '_initialized', False):
            return
        
        super().__init__()
        self.db_config = config.get_database_config()
        self.db_path = self.db_config.get('archivo', './data/deleginsumos.db')
        self._local = threading.local()
        self._initialized = True
        
        # Crear directorio de base de datos si no existe
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"DatabaseConnection inicializado - DB: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Obtiene una conexión SQLite thread-local.
        
        Returns:
            Conexión SQLite configurada
            
        Raises:
            DatabaseConnectionException: Si no se puede conectar
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                self._local.connection = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                
                # Configurar conexión
                self._configure_connection(self._local.connection)
                
                self.logger.debug(f"Nueva conexión creada para thread {threading.current_thread().name}")
                
            except sqlite3.Error as e:
                self.logger.error(f"Error conectando a la base de datos: {e}")
                raise DatabaseConnectionException(f"No se pudo conectar a la base de datos: {e}")
        
        return self._local.connection
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """
        Configura una conexión SQLite con los parámetros optimizados.
        
        Args:
            conn: Conexión a configurar
        """
        # Configurar WAL mode para mejor concurrencia
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Habilitar foreign keys
        conn.execute("PRAGMA foreign_keys=ON")
        
        # Configurar timeout para locks
        conn.execute("PRAGMA busy_timeout=30000")
        
        # Optimizar para SSD
        conn.execute("PRAGMA synchronous=NORMAL")
        
        # Configurar cache
        conn.execute("PRAGMA cache_size=10000")
        
        # Row factory para acceso por nombre de columna
        conn.row_factory = sqlite3.Row
    
    @contextmanager
    def get_cursor(self, transaction: bool = False):
        """
        Context manager para obtener un cursor.
        
        Args:
            transaction: Si debe usar transacción
            
        Yields:
            Cursor SQLite configurado
            
        Raises:
            DatabaseConnectionException: Si hay errores de conexión
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if transaction:
                cursor.execute("BEGIN IMMEDIATE")
            
            yield cursor
            
            if transaction:
                conn.commit()
                
        except sqlite3.IntegrityError as e:
            if transaction:
                conn.rollback()
            self.logger.error(f"Error de integridad en base de datos: {e}")
            raise DatabaseIntegrityException(str(e))
            
        except sqlite3.Error as e:
            if transaction:
                conn.rollback()
            self.logger.error(f"Error en operación de base de datos: {e}")
            raise DatabaseConnectionException(f"Error de base de datos: {e}")
            
        except Exception as e:
            if transaction:
                conn.rollback()
            self.logger.error(f"Error inesperado en base de datos: {e}")
            raise
        
        finally:
            cursor.close()
    
    @contextmanager
    def transaction(self):
        """
        Context manager para transacciones explícitas.
        
        Yields:
            Cursor dentro de una transacción
        """
        with self.get_cursor(transaction=True) as cursor:
            yield cursor
    
    def execute_query(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """
        Ejecuta una consulta SELECT y retorna los resultados.
        
        Args:
            query: Consulta SQL
            params: Parámetros de la consulta
            
        Returns:
            Lista de filas resultado
            
        Raises:
            DatabaseConnectionException: Si hay errores en la consulta
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            
            log_database_operation("SELECT", self._extract_table_name(query))
            self.logger.debug(f"Query ejecutada: {query} | Resultados: {len(results)}")
            
            return results
    
    def execute_command(self, command: str, params: tuple = None) -> int:
        """
        Ejecuta un comando INSERT/UPDATE/DELETE.
        
        Args:
            command: Comando SQL
            params: Parámetros del comando
            
        Returns:
            ID de la fila insertada o número de filas afectadas
            
        Raises:
            DatabaseConnectionException: Si hay errores en el comando
        """
        with self.transaction() as cursor:
            cursor.execute(command, params or ())
            
            # Determinar tipo de operación
            operation = command.strip().upper().split()[0]
            table_name = self._extract_table_name(command)
            
            if operation == "INSERT":
                result_id = cursor.lastrowid
                log_database_operation("INSERT", table_name, str(result_id))
                self.logger.debug(f"INSERT ejecutado - ID: {result_id}")
                return result_id
            else:
                affected_rows = cursor.rowcount
                log_database_operation(operation, table_name, f"rows:{affected_rows}")
                self.logger.debug(f"{operation} ejecutado - Filas afectadas: {affected_rows}")
                return affected_rows
    
    def execute_many(self, command: str, params_list: List[tuple]) -> int:
        """
        Ejecuta un comando para múltiples conjuntos de parámetros.
        
        Args:
            command: Comando SQL
            params_list: Lista de tuplas con parámetros
            
        Returns:
            Número total de filas afectadas
            
        Raises:
            DatabaseConnectionException: Si hay errores en los comandos
        """
        with self.transaction() as cursor:
            cursor.executemany(command, params_list)
            
            operation = command.strip().upper().split()[0]
            table_name = self._extract_table_name(command)
            affected_rows = cursor.rowcount
            
            log_database_operation(f"{operation}_MANY", table_name, f"rows:{affected_rows}")
            self.logger.debug(f"{operation}_MANY ejecutado - Filas afectadas: {affected_rows}")
            
            return affected_rows
    
    def _extract_table_name(self, sql: str) -> str:
        """
        Extrae el nombre de la tabla de una consulta SQL.
        
        Args:
            sql: Consulta SQL
            
        Returns:
            Nombre de la tabla o "unknown"
        """
        try:
            sql_upper = sql.upper().strip()
            
            if sql_upper.startswith('SELECT'):
                # Buscar FROM
                from_index = sql_upper.find(' FROM ')
                if from_index != -1:
                    after_from = sql_upper[from_index + 6:].strip()
                    table_name = after_from.split()[0]
                    return table_name.lower()
            
            elif sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE')):
                # Buscar INTO/FROM/FROM después de DELETE
                keywords = [' INTO ', ' FROM ']
                for keyword in keywords:
                    keyword_index = sql_upper.find(keyword)
                    if keyword_index != -1:
                        after_keyword = sql_upper[keyword_index + len(keyword):].strip()
                        table_name = after_keyword.split()[0]
                        return table_name.lower()
            
            return "unknown"
            
        except Exception:
            return "unknown"
    
    def check_connection(self) -> bool:
        """
        Verifica si la conexión a la base de datos está funcionando.
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            self.logger.error(f"Verificación de conexión falló: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Obtiene información sobre la base de datos.
        
        Returns:
            Diccionario con información de la BD
        """
        try:
            with self.get_cursor() as cursor:
                # Información básica
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                
                # Listar tablas
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Tamaño del archivo
                db_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024)
                
                return {
                    "sqlite_version": sqlite_version,
                    "database_path": self.db_path,
                    "database_size_mb": round(db_size_mb, 2),
                    "tables": tables,
                    "table_count": len(tables)
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo información de BD: {e}")
            return {"error": str(e)}
    
    def vacuum_database(self) -> bool:
        """
        Ejecuta VACUUM para optimizar la base de datos.
        
        Returns:
            True si el VACUUM fue exitoso
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("VACUUM")
            
            self.logger.info("VACUUM ejecutado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error ejecutando VACUUM: {e}")
            return False
    
    def close_connection(self) -> None:
        """Cierra la conexión thread-local si existe"""
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
                self._local.connection = None
                self.logger.debug("Conexión cerrada")
            except Exception as e:
                self.logger.error(f"Error cerrando conexión: {e}")
    
    def close_all_connections(self) -> None:
        """Cierra todas las conexiones (para shutdown de la app)"""
        self.close_connection()
        self.logger.info("Todas las conexiones cerradas")


# Instancia global del manejador de conexiones
db_connection = DatabaseConnection()

# Funciones de conveniencia para uso directo
def get_db_cursor(transaction: bool = False):
    """Función de conveniencia para obtener cursor"""
    return db_connection.get_cursor(transaction=transaction)

def execute_query(query: str, params: tuple = None) -> List[sqlite3.Row]:
    """Función de conveniencia para ejecutar consultas"""
    return db_connection.execute_query(query, params)

def execute_command(command: str, params: tuple = None) -> int:
    """Función de conveniencia para ejecutar comandos"""
    return db_connection.execute_command(command, params)

def get_db_path() -> Path:
    """
    Obtiene la ruta absoluta de la base de datos SQLite.

    Returns:
        Path: Ruta absoluta al archivo de base de datos
    """
    return Path(db_connection.db_path).resolve()