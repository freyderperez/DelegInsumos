"""
DelegInsumos - Sistema de Migraciones de Base de Datos
Maneja la creación y actualización del esquema de la base de datos
"""

from typing import List, Dict, Any
from datetime import datetime

from database.connection import db_connection
from utils.logger import LoggerMixin, log_database_operation
from exceptions.custom_exceptions import DatabaseMigrationException
from utils import generar_id


class Migration(LoggerMixin):
    """
    Clase base para migraciones de base de datos
    """
    
    def __init__(self, version: str, description: str):
        super().__init__()
        self.version = version
        self.description = description
    
    def up(self) -> None:
        """Aplica la migración (debe ser implementado por subclases)"""
        raise NotImplementedError("Método up() debe ser implementado")
    
    def down(self) -> None:
        """Revierte la migración (debe ser implementado por subclases)"""
        raise NotImplementedError("Método down() debe ser implementado")


class InitialMigration(Migration):
    """Migración inicial - Crea todas las tablas base del sistema"""
    
    def __init__(self):
        super().__init__("001", "Crear tablas iniciales del sistema")
    
    def up(self) -> None:
        """Crea el esquema inicial de la base de datos"""
        
        # Tabla: insumos
        create_insumos_sql = """
        CREATE TABLE IF NOT EXISTS insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre VARCHAR(100) NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            cantidad_actual INTEGER DEFAULT 0 CHECK(cantidad_actual >= 0),
            cantidad_minima INTEGER DEFAULT 5 CHECK(cantidad_minima >= 0),
            cantidad_maxima INTEGER DEFAULT 100 CHECK(cantidad_maxima >= cantidad_minima),
            unidad_medida VARCHAR(20) DEFAULT 'unidad',
            precio_unitario DECIMAL(10,2) DEFAULT 0.00 CHECK(precio_unitario >= 0),
            proveedor VARCHAR(100),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT 1
        )
        """
        
        # Tabla: empleados
        create_empleados_sql = """
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo VARCHAR(150) NOT NULL,
            cargo VARCHAR(100),
            departamento VARCHAR(100),
            cedula VARCHAR(20) UNIQUE NOT NULL,
            email VARCHAR(100),
            telefono VARCHAR(20),
            fecha_ingreso DATE,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT 1
        )
        """
        
        # Tabla: entregas
        create_entregas_sql = """
        CREATE TABLE IF NOT EXISTS entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            insumo_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL CHECK(cantidad > 0),
            fecha_entrega TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observaciones TEXT,
            entregado_por VARCHAR(100),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
            FOREIGN KEY (insumo_id) REFERENCES insumos(id) ON DELETE CASCADE
        )
        """
        
        # Ejecutar creación de tablas
        with db_connection.transaction() as cursor:
            cursor.execute(create_insumos_sql)
            cursor.execute(create_empleados_sql)
            cursor.execute(create_entregas_sql)
            
            self.logger.info("Tablas principales creadas exitosamente")
    
    def down(self) -> None:
        """Elimina las tablas del esquema inicial"""
        with db_connection.transaction() as cursor:
            cursor.execute("DROP TABLE IF EXISTS entregas")
            cursor.execute("DROP TABLE IF EXISTS empleados")
            cursor.execute("DROP TABLE IF EXISTS insumos")
            
            self.logger.info("Tablas principales eliminadas")


class IndexMigration(Migration):
    """Migración de índices - Crea índices para optimizar consultas"""
    
    def __init__(self):
        super().__init__("002", "Crear índices de optimización")
    
    def up(self) -> None:
        """Crea índices para optimizar consultas"""
        
        indices = [
            # Índices para tabla insumos
            "CREATE INDEX IF NOT EXISTS idx_insumos_categoria ON insumos(categoria)",
            "CREATE INDEX IF NOT EXISTS idx_insumos_stock_bajo ON insumos(cantidad_actual, cantidad_minima)",
            "CREATE INDEX IF NOT EXISTS idx_insumos_activos ON insumos(activo)",
            "CREATE INDEX IF NOT EXISTS idx_insumos_nombre ON insumos(nombre)",
            
            # Índices para tabla empleados
            "CREATE INDEX IF NOT EXISTS idx_empleados_cedula ON empleados(cedula)",
            "CREATE INDEX IF NOT EXISTS idx_empleados_departamento ON empleados(departamento)",
            "CREATE INDEX IF NOT EXISTS idx_empleados_activos ON empleados(activo)",
            "CREATE INDEX IF NOT EXISTS idx_empleados_nombre ON empleados(nombre_completo)",
            
            # Índices para tabla entregas
            "CREATE INDEX IF NOT EXISTS idx_entregas_fecha ON entregas(fecha_entrega)",
            "CREATE INDEX IF NOT EXISTS idx_entregas_empleado ON entregas(empleado_id)",
            "CREATE INDEX IF NOT EXISTS idx_entregas_insumo ON entregas(insumo_id)",
            "CREATE INDEX IF NOT EXISTS idx_entregas_empleado_fecha ON entregas(empleado_id, fecha_entrega)",
            "CREATE INDEX IF NOT EXISTS idx_entregas_insumo_fecha ON entregas(insumo_id, fecha_entrega)"
        ]
        
        with db_connection.transaction() as cursor:
            for indice_sql in indices:
                cursor.execute(indice_sql)
            
            self.logger.info(f"Se crearon {len(indices)} índices de optimización")
    
    def down(self) -> None:
        """Elimina los índices creados"""
        indices_names = [
            "idx_insumos_categoria",
            "idx_insumos_stock_bajo", 
            "idx_insumos_activos",
            "idx_insumos_nombre",
            "idx_empleados_cedula",
            "idx_empleados_departamento",
            "idx_empleados_activos", 
            "idx_empleados_nombre",
            "idx_entregas_fecha",
            "idx_entregas_empleado",
            "idx_entregas_insumo",
            "idx_entregas_empleado_fecha",
            "idx_entregas_insumo_fecha"
        ]
        
        with db_connection.transaction() as cursor:
            for indice_name in indices_names:
                cursor.execute(f"DROP INDEX IF EXISTS {indice_name}")
            
            self.logger.info("Índices de optimización eliminados")


class TriggerMigration(Migration):
    """Migración de triggers - Crea triggers para automatización"""
    
    def __init__(self):
        super().__init__("003", "Crear triggers de automatización")
    
    def up(self) -> None:
        """Crea triggers para automatizar tareas"""
        
        # Trigger para actualizar fecha_actualizacion en insumos
        trigger_update_insumos = """
        CREATE TRIGGER IF NOT EXISTS tr_insumos_updated_at
        AFTER UPDATE ON insumos
        FOR EACH ROW
        BEGIN
            UPDATE insumos 
            SET fecha_actualizacion = CURRENT_TIMESTAMP 
            WHERE id = NEW.id;
        END
        """
        
        # Trigger para actualizar stock después de entregas
        trigger_update_stock = """
        CREATE TRIGGER IF NOT EXISTS tr_entregas_update_stock
        AFTER INSERT ON entregas
        FOR EACH ROW
        BEGIN
            UPDATE insumos 
            SET cantidad_actual = cantidad_actual - NEW.cantidad,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = NEW.insumo_id;
        END
        """
        
        # Trigger para validar stock antes de entregas
        trigger_validate_stock = """
        CREATE TRIGGER IF NOT EXISTS tr_entregas_validate_stock
        BEFORE INSERT ON entregas
        FOR EACH ROW
        WHEN (SELECT cantidad_actual FROM insumos WHERE id = NEW.insumo_id) < NEW.cantidad
        BEGIN
            SELECT RAISE(ABORT, 'Stock insuficiente para realizar la entrega');
        END
        """
        
        with db_connection.transaction() as cursor:
            cursor.execute(trigger_update_insumos)
            cursor.execute(trigger_update_stock)
            cursor.execute(trigger_validate_stock)
            
            self.logger.info("Triggers de automatización creados exitosamente")
    
    def down(self) -> None:
        """Elimina los triggers creados"""
        triggers = [
            "tr_insumos_updated_at",
            "tr_entregas_update_stock",
            "tr_entregas_validate_stock"
        ]
        
        with db_connection.transaction() as cursor:
            for trigger_name in triggers:
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
            
            self.logger.info("Triggers de automatización eliminados")


class ViewsMigration(Migration):
    """Migración de vistas - Crea vistas para consultas complejas"""
    
    def __init__(self):
        super().__init__("004", "Crear vistas de consulta")
    
    def up(self) -> None:
        """Crea vistas para simplificar consultas complejas"""
        
        # Vista: Stock bajo/crítico
        view_stock_alerts = """
        CREATE VIEW IF NOT EXISTS vw_stock_alerts AS
        SELECT 
            i.id,
            i.nombre,
            i.categoria,
            i.cantidad_actual,
            i.cantidad_minima,
            i.unidad_medida,
            CASE 
                WHEN i.cantidad_actual = 0 THEN 'CRITICO'
                WHEN i.cantidad_actual <= i.cantidad_minima THEN 'BAJO'
                ELSE 'NORMAL'
            END as estado_stock,
            CASE 
                WHEN i.cantidad_actual = 0 THEN '#F44336'
                WHEN i.cantidad_actual <= i.cantidad_minima THEN '#FF9800'
                ELSE '#4CAF50'
            END as color_estado
        FROM insumos i
        WHERE i.activo = 1
        ORDER BY i.cantidad_actual ASC, i.nombre ASC
        """
        
        # Vista: Entregas con información completa
        view_entregas_completas = """
        CREATE VIEW IF NOT EXISTS vw_entregas_completas AS
        SELECT 
            e.id,
            e.cantidad,
            e.fecha_entrega,
            e.observaciones,
            e.entregado_por,
            emp.nombre_completo as empleado_nombre,
            emp.cargo as empleado_cargo,
            emp.departamento as empleado_departamento,
            emp.cedula as empleado_cedula,
            i.nombre as insumo_nombre,
            i.categoria as insumo_categoria,
            i.unidad_medida as insumo_unidad,
            i.precio_unitario as insumo_precio,
            (e.cantidad * i.precio_unitario) as valor_total
        FROM entregas e
        INNER JOIN empleados emp ON e.empleado_id = emp.id
        INNER JOIN insumos i ON e.insumo_id = i.id
        ORDER BY e.fecha_entrega DESC
        """
        
        # Vista: Resumen de inventario
        view_resumen_inventario = """
        CREATE VIEW IF NOT EXISTS vw_resumen_inventario AS
        SELECT 
            categoria,
            COUNT(*) as total_insumos,
            SUM(cantidad_actual) as cantidad_total,
            SUM(cantidad_actual * precio_unitario) as valor_total,
            AVG(cantidad_actual) as promedio_cantidad,
            MIN(cantidad_actual) as minimo_stock,
            MAX(cantidad_actual) as maximo_stock,
            SUM(CASE WHEN cantidad_actual <= cantidad_minima THEN 1 ELSE 0 END) as insumos_stock_bajo
        FROM insumos
        WHERE activo = 1
        GROUP BY categoria
        ORDER BY categoria
        """
        
        with db_connection.transaction() as cursor:
            cursor.execute(view_stock_alerts)
            cursor.execute(view_entregas_completas) 
            cursor.execute(view_resumen_inventario)
            
            self.logger.info("Vistas de consulta creadas exitosamente")
    
    def down(self) -> None:
        """Elimina las vistas creadas"""
        views = [
            "vw_stock_alerts",
            "vw_entregas_completas", 
            "vw_resumen_inventario"
        ]
        
        with db_connection.transaction() as cursor:
            for view_name in views:
                cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
            
            self.logger.info("Vistas de consulta eliminadas")


class UniqueIdsMigration(Migration):
    """Migración para agregar códigos únicos legibles (codigo) a insumos, empleados y entregas"""

    def __init__(self):
        super().__init__("005", "Agregar columna 'codigo' y poblarla con IDs únicos")

    def up(self) -> None:
        """Agrega columna 'codigo' a tablas y la puebla con valores únicos"""
        try:
            with db_connection.transaction() as cursor:
                # Intentar agregar columna 'codigo' a cada tabla (ignorar si ya existe)
                alter_statements = [
                    ("insumos", "ALTER TABLE insumos ADD COLUMN codigo TEXT"),
                    ("empleados", "ALTER TABLE empleados ADD COLUMN codigo TEXT"),
                    ("entregas", "ALTER TABLE entregas ADD COLUMN codigo TEXT"),
                ]
                for table, stmt in alter_statements:
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        # Si la columna ya existe, continuar
                        if "duplicate column name" not in str(e).lower():
                            raise

                # Poblar códigos únicos
                def backfill_codigo(table: str, prefix: str):
                    rows = cursor.execute(f"SELECT id, codigo FROM {table}").fetchall()
                    # Recolectar códigos existentes para evitar duplicados
                    existing = set(
                        r["codigo"] for r in rows if isinstance(r, dict) and r.get("codigo")
                    ) if rows and isinstance(rows[0], dict) else set(
                        r[1] for r in rows if len(r) > 1 and r[1]
                    )

                    for row in rows:
                        # Soportar tanto sqlite3.Row indexado por nombre como por índice
                        row_id = row["id"] if isinstance(row, dict) else row[0]
                        current_code = (row.get("codigo") if isinstance(row, dict) else row[1]) if (len(row) > 1) else None

                        if not current_code:
                            # Generar hasta que sea único en memoria
                            code = generar_id(prefix)
                            while code in existing:
                                code = generar_id(prefix)
                            existing.add(code)
                            cursor.execute(f"UPDATE {table} SET codigo = ? WHERE id = ?", (code, row_id))

                backfill_codigo("insumos", "INS")
                backfill_codigo("empleados", "EMP")
                backfill_codigo("entregas", "ENT")

                # Crear índices únicos para 'codigo'
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_insumos_codigo ON insumos(codigo)")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_empleados_codigo ON empleados(codigo)")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_entregas_codigo ON entregas(codigo)")

                self.logger.info("Columna 'codigo' agregada y poblada exitosamente en todas las tablas")

        except Exception as e:
            self.logger.error(f"Error en UniqueIdsMigration.up: {e}")
            raise DatabaseMigrationException(f"Error agregando/poblando columna codigo: {e}")

    def down(self) -> None:
        """Revierte índices únicos (SQLite no soporta DROP COLUMN sin recrear tabla)"""
        try:
            with db_connection.transaction() as cursor:
                cursor.execute("DROP INDEX IF EXISTS uq_insumos_codigo")
                cursor.execute("DROP INDEX IF EXISTS uq_empleados_codigo")
                cursor.execute("DROP INDEX IF EXISTS uq_entregas_codigo")
            self.logger.info("Índices únicos de 'codigo' eliminados")
        except Exception as e:
            self.logger.error(f"Error revirtiendo índices de 'codigo': {e}")
            raise DatabaseMigrationException(f"Error revirtiendo índices de 'codigo': {e}")


class ViewsPatchMigration(Migration):
    """Migración para actualizar vista vw_entregas_completas con columnas de IDs crudos"""

    def __init__(self):
        super().__init__("006", "Actualizar vista vw_entregas_completas con empleado_id e insumo_id")

    def up(self) -> None:
        """Recrea la vista vw_entregas_completas incluyendo empleado_id e insumo_id"""
        view_sql_drop = "DROP VIEW IF EXISTS vw_entregas_completas"
        view_sql_create = """
        CREATE VIEW IF NOT EXISTS vw_entregas_completas AS
        SELECT
            e.id,
            e.empleado_id,
            e.insumo_id,
            e.cantidad,
            e.fecha_entrega,
            e.observaciones,
            e.entregado_por,
            emp.nombre_completo as empleado_nombre,
            emp.cargo as empleado_cargo,
            emp.departamento as empleado_departamento,
            emp.cedula as empleado_cedula,
            i.nombre as insumo_nombre,
            i.categoria as insumo_categoria,
            i.unidad_medida as insumo_unidad,
            i.precio_unitario as insumo_precio,
            (e.cantidad * i.precio_unitario) as valor_total
        FROM entregas e
        INNER JOIN empleados emp ON e.empleado_id = emp.id
        INNER JOIN insumos i ON e.insumo_id = i.id
        ORDER BY e.fecha_entrega DESC
        """
        with db_connection.transaction() as cursor:
            cursor.execute(view_sql_drop)
            cursor.execute(view_sql_create)
        self.logger.info("Vista vw_entregas_completas actualizada para incluir empleado_id e insumo_id")

    def down(self) -> None:
        """Revierte a la definición anterior (sin columnas de IDs explícitas)"""
        view_sql_drop = "DROP VIEW IF EXISTS vw_entregas_completas"
        view_sql_create = """
        CREATE VIEW IF NOT EXISTS vw_entregas_completas AS
        SELECT
            e.id,
            e.cantidad,
            e.fecha_entrega,
            e.observaciones,
            e.entregado_por,
            emp.nombre_completo as empleado_nombre,
            emp.cargo as empleado_cargo,
            emp.departamento as empleado_departamento,
            emp.cedula as empleado_cedula,
            i.nombre as insumo_nombre,
            i.categoria as insumo_categoria,
            i.unidad_medida as insumo_unidad,
            i.precio_unitario as insumo_precio,
            (e.cantidad * i.precio_unitario) as valor_total
        FROM entregas e
        INNER JOIN empleados emp ON e.empleado_id = emp.id
        INNER JOIN insumos i ON e.insumo_id = i.id
        ORDER BY e.fecha_entrega DESC
        """
        with db_connection.transaction() as cursor:
            cursor.execute(view_sql_drop)
            cursor.execute(view_sql_create)
        self.logger.info("Vista vw_entregas_completas revertida a definición previa")


class MigrationManager(LoggerMixin):
    """
    Gestor de migraciones de base de datos
    """
    
    def __init__(self):
        super().__init__()
        self.migrations: List[Migration] = [
            InitialMigration(),
            IndexMigration(),
            TriggerMigration(),
            ViewsMigration(),
            UniqueIdsMigration(),
            ViewsPatchMigration()
        ]
        
        # Crear tabla de control de migraciones
        self._create_migrations_table()
    
    def _create_migrations_table(self) -> None:
        """Crea la tabla para controlar migraciones aplicadas"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(10) PRIMARY KEY,
            description VARCHAR(255),
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        try:
            with db_connection.get_cursor() as cursor:
                cursor.execute(create_sql)
            
            self.logger.debug("Tabla schema_migrations creada/verificada")
            
        except Exception as e:
            raise DatabaseMigrationException(f"Error creando tabla de migraciones: {e}")
    
    def get_applied_migrations(self) -> List[str]:
        """
        Obtiene la lista de migraciones ya aplicadas.
        
        Returns:
            Lista de versiones de migraciones aplicadas
        """
        try:
            query = "SELECT version FROM schema_migrations ORDER BY version"
            results = db_connection.execute_query(query)
            return [row[0] for row in results]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo migraciones aplicadas: {e}")
            return []
    
    def is_migration_applied(self, version: str) -> bool:
        """
        Verifica si una migración específica ya fue aplicada.
        
        Args:
            version: Versión de la migración
            
        Returns:
            True si la migración ya fue aplicada
        """
        applied = self.get_applied_migrations()
        return version in applied
    
    def apply_migration(self, migration: Migration) -> bool:
        """
        Aplica una migración específica.
        
        Args:
            migration: Migración a aplicar
            
        Returns:
            True si la migración fue aplicada exitosamente
        """
        if self.is_migration_applied(migration.version):
            self.logger.info(f"Migración {migration.version} ya fue aplicada")
            return True
        
        try:
            self.logger.info(f"Aplicando migración {migration.version}: {migration.description}")
            
            # Aplicar migración
            migration.up()
            
            # Registrar migración aplicada
            insert_sql = """
            INSERT INTO schema_migrations (version, description) 
            VALUES (?, ?)
            """
            db_connection.execute_command(insert_sql, (migration.version, migration.description))
            
            self.logger.info(f"Migración {migration.version} aplicada exitosamente")
            log_database_operation("MIGRATION_APPLIED", "schema", migration.version)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error aplicando migración {migration.version}: {e}")
            raise DatabaseMigrationException(f"Error en migración {migration.version}: {e}")
    
    def migrate_up(self) -> None:
        """Aplica todas las migraciones pendientes"""
        self.logger.info("Iniciando proceso de migración")
        
        applied_count = 0
        for migration in self.migrations:
            if self.apply_migration(migration):
                if not self.is_migration_applied(migration.version):
                    applied_count += 1
        
        if applied_count > 0:
            self.logger.info(f"Se aplicaron {applied_count} migraciones nuevas")
        else:
            self.logger.info("Base de datos actualizada - No hay nuevas migraciones")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de las migraciones.
        
        Returns:
            Diccionario con estado de migraciones
        """
        applied = self.get_applied_migrations()
        pending = []
        
        for migration in self.migrations:
            if migration.version not in applied:
                pending.append({
                    'version': migration.version,
                    'description': migration.description
                })
        
        return {
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_versions': applied,
            'pending_migrations': pending,
            'last_migration': applied[-1] if applied else None
        }
    
    def initialize_database(self) -> bool:
        """
        Inicializa completamente la base de datos.
        
        Returns:
            True si la inicialización fue exitosa
        """
        try:
            self.logger.info("Inicializando base de datos DelegInsumos")
            
            # Aplicar todas las migraciones
            self.migrate_up()
            
            # Verificar integridad
            if not self._verify_schema():
                raise DatabaseMigrationException("Error en verificación de esquema")
            
            self.logger.info("Base de datos inicializada exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando base de datos: {e}")
            raise DatabaseMigrationException(f"Error en inicialización: {e}")
    
    def _verify_schema(self) -> bool:
        """
        Verifica que el esquema esté correctamente aplicado.
        
        Returns:
            True si el esquema es válido
        """
        try:
            # Verificar que las tablas principales existan
            required_tables = ['insumos', 'empleados', 'entregas', 'schema_migrations']
            
            query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ({})
            """.format(','.join('?' * len(required_tables)))
            
            results = db_connection.execute_query(query, tuple(required_tables))
            found_tables = {row[0] for row in results}
            
            missing_tables = set(required_tables) - found_tables
            if missing_tables:
                self.logger.error(f"Tablas faltantes: {missing_tables}")
                return False
            
            self.logger.debug("Verificación de esquema exitosa")
            return True
            
        except Exception as e:
            self.logger.error(f"Error verificando esquema: {e}")
            return False


# Instancia global del gestor de migraciones
migration_manager = MigrationManager()

# Función de conveniencia para inicializar la BD
def initialize_database() -> bool:
    """Función de conveniencia para inicializar la base de datos"""
    return migration_manager.initialize_database()

def get_migration_status() -> Dict[str, Any]:
    """Función de conveniencia para obtener estado de migraciones"""
    return migration_manager.get_migration_status()