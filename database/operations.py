"""
DelegInsumos - Operaciones de Base de Datos
Contiene todas las operaciones CRUD para las entidades del sistema
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import sqlite3
import shutil
import os
from pathlib import Path

from database.connection import db_connection, get_db_path
from utils.logger import LoggerMixin
from utils import safe_filename, generar_id
from exceptions.custom_exceptions import (
    DatabaseException,
    RecordNotFoundException,
    DuplicateRecordException
)


class BaseRepository(LoggerMixin):
    """
    Repositorio base con operaciones comum para todas las entidades
    """
    
    def __init__(self, table_name: str):
        super().__init__()
        self.table_name = table_name
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convierte una fila SQLite a diccionario"""
        if not row:
            return {}
        return dict(row)
    
    def _rows_to_list(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """Convierte una lista de filas SQLite a lista de diccionarios"""
        return [self._row_to_dict(row) for row in rows]


class InsumoRepository(BaseRepository):
    """Repositorio para operaciones CRUD de insumos"""
    
    def __init__(self):
        super().__init__('insumos')
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Crea un nuevo insumo.
        
        Args:
            data: Diccionario con datos del insumo
            
        Returns:
            ID del insumo creado
            
        Raises:
            DatabaseException: Si hay errores en la creación
        """
        try:
            # Generar código único legible para el insumo
            codigo = generar_id("INS")

            sql = """
            INSERT INTO insumos (
                nombre, categoria, cantidad_actual, cantidad_minima, cantidad_maxima,
                unidad_medida, precio_unitario, proveedor, codigo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                data['nombre'],
                data['categoria'],
                data.get('cantidad_actual', 0),
                data.get('cantidad_minima', 5),
                data.get('cantidad_maxima', 100),
                data.get('unidad_medida', 'unidad'),
                data.get('precio_unitario', 0.00),
                data.get('proveedor', ''),
                codigo
            )
            
            insumo_id = db_connection.execute_command(sql, params)
            self.logger.info(f"Insumo creado con ID: {insumo_id} y código: {codigo}")
            
            return insumo_id
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateRecordException(
                    "insumo", "nombre", data['nombre']
                )
            raise DatabaseException(f"Error de integridad creando insumo: {e}")
        
        except Exception as e:
            self.logger.error(f"Error creando insumo: {e}")
            raise DatabaseException(f"Error creando insumo: {e}")
    
    def get_by_id(self, insumo_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un insumo por su ID.
        
        Args:
            insumo_id: ID del insumo
            
        Returns:
            Diccionario con datos del insumo o None si no existe
        """
        try:
            sql = "SELECT * FROM insumos WHERE id = ?"
            rows = db_connection.execute_query(sql, (insumo_id,))
            
            if not rows:
                return None
            
            return self._row_to_dict(rows[0])
            
        except Exception as e:
            self.logger.error(f"Error obteniendo insumo ID {insumo_id}: {e}")
            raise DatabaseException(f"Error obteniendo insumo: {e}")
    
    def get_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los insumos.
        
        Args:
            active_only: Si solo incluir insumos activos
            
        Returns:
            Lista de diccionarios con datos de insumos
        """
        try:
            sql = "SELECT * FROM insumos"
            params = ()
            
            if active_only:
                sql += " WHERE activo = 1"
            
            sql += " ORDER BY nombre"
            
            rows = db_connection.execute_query(sql, params)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo lista de insumos: {e}")
            raise DatabaseException(f"Error obteniendo insumos: {e}")
    
    def get_by_categoria(self, categoria: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene insumos por categoría.
        
        Args:
            categoria: Categoría a filtrar
            active_only: Si solo incluir insumos activos
            
        Returns:
            Lista de insumos de la categoría
        """
        try:
            sql = "SELECT * FROM insumos WHERE categoria = ?"
            params = [categoria]
            
            if active_only:
                sql += " AND activo = 1"
            
            sql += " ORDER BY nombre"
            
            rows = db_connection.execute_query(sql, tuple(params))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo insumos por categoría {categoria}: {e}")
            raise DatabaseException(f"Error obteniendo insumos por categoría: {e}")
    
    def get_stock_alerts(self) -> List[Dict[str, Any]]:
        """
        Obtiene insumos con alertas de stock (bajo o crítico).
        
        Returns:
            Lista de insumos con stock bajo o crítico
        """
        try:
            sql = "SELECT * FROM vw_stock_alerts WHERE estado_stock IN ('BAJO', 'CRITICO')"
            rows = db_connection.execute_query(sql)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo alertas de stock: {e}")
            raise DatabaseException(f"Error obteniendo alertas: {e}")
    
    def search(self, term: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Busca insumos por término de búsqueda.
        
        Args:
            term: Término de búsqueda
            active_only: Si solo incluir insumos activos
            
        Returns:
            Lista de insumos que coinciden con la búsqueda
        """
        try:
            sql = """
            SELECT * FROM insumos 
            WHERE (nombre LIKE ? OR categoria LIKE ? OR proveedor LIKE ?)
            """
            search_term = f"%{term}%"
            params = [search_term, search_term, search_term]
            
            if active_only:
                sql += " AND activo = 1"
            
            sql += " ORDER BY nombre"
            
            rows = db_connection.execute_query(sql, tuple(params))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error buscando insumos con término '{term}': {e}")
            raise DatabaseException(f"Error en búsqueda de insumos: {e}")
    
    def update(self, insumo_id: int, data: Dict[str, Any]) -> bool:
        """
        Actualiza un insumo existente.
        
        Args:
            insumo_id: ID del insumo
            data: Datos a actualizar
            
        Returns:
            True si la actualización fue exitosa
            
        Raises:
            RecordNotFoundException: Si el insumo no existe
        """
        try:
            # Verificar que el insumo existe
            if not self.get_by_id(insumo_id):
                raise RecordNotFoundException("insumo", str(insumo_id))
            
            # Construir SQL dinámicamente basado en los campos a actualizar
            fields = []
            values = []
            
            updateable_fields = [
                'nombre', 'categoria', 'cantidad_actual', 'cantidad_minima',
                'cantidad_maxima', 'unidad_medida', 'precio_unitario', 'proveedor',
                'activo'
            ]
            
            for field in updateable_fields:
                if field in data:
                    fields.append(f"{field} = ?")
                    values.append(data[field])
            
            if not fields:
                return False
            
            sql = f"UPDATE insumos SET {', '.join(fields)} WHERE id = ?"
            values.append(insumo_id)
            
            rows_affected = db_connection.execute_command(sql, tuple(values))
            
            if rows_affected > 0:
                self.logger.info(f"Insumo {insumo_id} actualizado exitosamente")
                return True
            
            return False
            
        except RecordNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando insumo {insumo_id}: {e}")
            raise DatabaseException(f"Error actualizando insumo: {e}")
    
    def update_stock(self, insumo_id: int, nueva_cantidad: int) -> bool:
        """
        Actualiza solo el stock de un insumo.
        
        Args:
            insumo_id: ID del insumo
            nueva_cantidad: Nueva cantidad en stock
            
        Returns:
            True si la actualización fue exitosa
        """
        return self.update(insumo_id, {'cantidad_actual': nueva_cantidad})
    
    def delete(self, insumo_id: int, soft_delete: bool = True) -> bool:
        """
        Elimina un insumo (soft o hard delete).
        
        Args:
            insumo_id: ID del insumo
            soft_delete: Si usar eliminación suave (marcar como inactivo)
            
        Returns:
            True si la eliminación fue exitosa
        """
        try:
            if soft_delete:
                # Eliminación suave - marcar como inactivo
                return self.update(insumo_id, {'activo': False})
            else:
                # Eliminación física
                sql = "DELETE FROM insumos WHERE id = ?"
                rows_affected = db_connection.execute_command(sql, (insumo_id,))
                
                if rows_affected > 0:
                    self.logger.info(f"Insumo {insumo_id} eliminado físicamente")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error eliminando insumo {insumo_id}: {e}")
            raise DatabaseException(f"Error eliminando insumo: {e}")
    
    def get_categories(self) -> List[str]:
        """
        Obtiene todas las categorías de insumos.
        
        Returns:
            Lista de categorías únicas
        """
        try:
            sql = "SELECT DISTINCT categoria FROM insumos WHERE activo = 1 ORDER BY categoria"
            rows = db_connection.execute_query(sql)
            return [row[0] for row in rows]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo categorías: {e}")
            raise DatabaseException(f"Error obteniendo categorías: {e}")
    
    def get_summary_by_category(self) -> List[Dict[str, Any]]:
        """
        Obtiene resumen de inventario por categoría.
        
        Returns:
            Lista con resumen por categoría
        """
        try:
            sql = "SELECT * FROM vw_resumen_inventario"
            rows = db_connection.execute_query(sql)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo resumen por categoría: {e}")
            raise DatabaseException(f"Error obteniendo resumen: {e}")


class EmpleadoRepository(BaseRepository):
    """Repositorio para operaciones CRUD de empleados"""
    
    def __init__(self):
        super().__init__('empleados')
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Crea un nuevo empleado.
        
        Args:
            data: Diccionario con datos del empleado
            
        Returns:
            ID del empleado creado
        """
        try:
            # Generar código único legible para el empleado
            codigo = generar_id("EMP")

            sql = """
            INSERT INTO empleados (
                nombre_completo, cargo, departamento, cedula,
                email, telefono, nota, codigo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                data['nombre_completo'],
                data.get('cargo', ''),
                data.get('departamento', ''),
                data['cedula'],
                data.get('email', ''),
                data.get('telefono', ''),
                data.get('nota', ''),
                codigo
            )
            
            empleado_id = db_connection.execute_command(sql, params)
            self.logger.info(f"Empleado creado con ID: {empleado_id} y código: {codigo}")
            
            return empleado_id
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise DuplicateRecordException(
                    "empleado", "cédula", data['cedula']
                )
            raise DatabaseException(f"Error de integridad creando empleado: {e}")
        
        except Exception as e:
            self.logger.error(f"Error creando empleado: {e}")
            raise DatabaseException(f"Error creando empleado: {e}")
    
    def get_by_id(self, empleado_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un empleado por su ID.
        
        Args:
            empleado_id: ID del empleado
            
        Returns:
            Diccionario con datos del empleado o None si no existe
        """
        try:
            sql = "SELECT * FROM empleados WHERE id = ?"
            rows = db_connection.execute_query(sql, (empleado_id,))
            
            if not rows:
                return None
            
            return self._row_to_dict(rows[0])
            
        except Exception as e:
            self.logger.error(f"Error obteniendo empleado ID {empleado_id}: {e}")
            raise DatabaseException(f"Error obteniendo empleado: {e}")
    
    def get_by_cedula(self, cedula: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un empleado por su cédula.
        
        Args:
            cedula: Cédula del empleado
            
        Returns:
            Diccionario con datos del empleado o None si no existe
        """
        try:
            sql = "SELECT * FROM empleados WHERE cedula = ?"
            rows = db_connection.execute_query(sql, (cedula,))
            
            if not rows:
                return None
            
            return self._row_to_dict(rows[0])
            
        except Exception as e:
            self.logger.error(f"Error obteniendo empleado por cédula {cedula}: {e}")
            raise DatabaseException(f"Error obteniendo empleado: {e}")
    
    def get_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene todos los empleados.
        
        Args:
            active_only: Si solo incluir empleados activos
            
        Returns:
            Lista de diccionarios con datos de empleados
        """
        try:
            sql = "SELECT * FROM empleados"
            params = ()
            
            if active_only:
                sql += " WHERE activo = 1"
            
            sql += " ORDER BY nombre_completo"
            
            rows = db_connection.execute_query(sql, params)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo lista de empleados: {e}")
            raise DatabaseException(f"Error obteniendo empleados: {e}")
    
    def get_by_departamento(self, departamento: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene empleados por departamento.
        
        Args:
            departamento: Departamento a filtrar
            active_only: Si solo incluir empleados activos
            
        Returns:
            Lista de empleados del departamento
        """
        try:
            sql = "SELECT * FROM empleados WHERE departamento = ?"
            params = [departamento]
            
            if active_only:
                sql += " AND activo = 1"
            
            sql += " ORDER BY nombre_completo"
            
            rows = db_connection.execute_query(sql, tuple(params))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo empleados por departamento {departamento}: {e}")
            raise DatabaseException(f"Error obteniendo empleados por departamento: {e}")
    
    def search(self, term: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Busca empleados por término de búsqueda.
        
        Args:
            term: Término de búsqueda
            active_only: Si solo incluir empleados activos
            
        Returns:
            Lista de empleados que coinciden con la búsqueda
        """
        try:
            sql = """
            SELECT * FROM empleados 
            WHERE (nombre_completo LIKE ? OR cedula LIKE ? OR cargo LIKE ? OR departamento LIKE ?)
            """
            search_term = f"%{term}%"
            params = [search_term, search_term, search_term, search_term]
            
            if active_only:
                sql += " AND activo = 1"
            
            sql += " ORDER BY nombre_completo"
            
            rows = db_connection.execute_query(sql, tuple(params))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error buscando empleados con término '{term}': {e}")
            raise DatabaseException(f"Error en búsqueda de empleados: {e}")
    
    def update(self, empleado_id: int, data: Dict[str, Any]) -> bool:
        """
        Actualiza un empleado existente.
        
        Args:
            empleado_id: ID del empleado
            data: Datos a actualizar
            
        Returns:
            True si la actualización fue exitosa
        """
        try:
            # Verificar que el empleado exists
            if not self.get_by_id(empleado_id):
                raise RecordNotFoundException("empleado", str(empleado_id))
            
            # Construir SQL dinámicamente
            fields = []
            values = []
            
            updateable_fields = [
                'nombre_completo', 'cargo', 'departamento', 'cedula',
                'email', 'telefono', 'nota', 'activo'
            ]
            
            for field in updateable_fields:
                if field in data:
                    fields.append(f"{field} = ?")
                    values.append(data[field])
            
            if not fields:
                return False
            
            sql = f"UPDATE empleados SET {', '.join(fields)} WHERE id = ?"
            values.append(empleado_id)
            
            rows_affected = db_connection.execute_command(sql, tuple(values))
            
            if rows_affected > 0:
                self.logger.info(f"Empleado {empleado_id} actualizado exitosamente")
                return True
            
            return False
            
        except RecordNotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error actualizando empleado {empleado_id}: {e}")
            raise DatabaseException(f"Error actualizando empleado: {e}")
    
    def delete(self, empleado_id: int, soft_delete: bool = True) -> bool:
        """
        Elimina un empleado (soft o hard delete).

        Args:
            empleado_id: ID del empleado
            soft_delete: Si usar eliminación suave

        Returns:
            True si la eliminación fue exitosa

        Raises:
            DatabaseException: Si hay entregas asociadas al empleado (hard delete)
        """
        try:
            if soft_delete:
                return self.update(empleado_id, {'activo': False})
            else:
                # Verificar si el empleado tiene entregas asociadas
                check_sql = "SELECT COUNT(*) FROM entregas WHERE empleado_id = ?"
                count_rows = db_connection.execute_query(check_sql, (empleado_id,))
                entregas_count = count_rows[0][0] if count_rows else 0

                if entregas_count > 0:
                    raise DatabaseException(
                        f"No se puede eliminar el empleado porque tiene {entregas_count} entrega(s) asociada(s). "
                        "Use eliminación suave (desactivar) en su lugar."
                    )

                # Si no tiene entregas, proceder con eliminación física
                sql = "DELETE FROM empleados WHERE id = ?"
                rows_affected = db_connection.execute_command(sql, (empleado_id,))

                if rows_affected > 0:
                    self.logger.info(f"Empleado {empleado_id} eliminado físicamente")
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Error eliminando empleado {empleado_id}: {e}")
            raise DatabaseException(f"Error eliminando empleado: {e}")
    
    def get_departments(self) -> List[str]:
        """
        Obtiene todos los departamentos.
        
        Returns:
            Lista de departamentos únicos
        """
        try:
            sql = "SELECT DISTINCT departamento FROM empleados WHERE activo = 1 AND departamento != '' ORDER BY departamento"
            rows = db_connection.execute_query(sql)
            return [row[0] for row in rows]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo departamentos: {e}")
            raise DatabaseException(f"Error obteniendo departamentos: {e}")


class EntregaRepository(BaseRepository):
    """Repositorio para operaciones CRUD de entregas"""
    
    def __init__(self):
        super().__init__('entregas')
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Crea una nueva entrega.
        
        Args:
            data: Diccionario con datos de la entrega
            
        Returns:
            ID de la entrega creada
        """
        try:
            # Generar código único legible para la entrega
            codigo = generar_id("ENT")

            sql = """
            INSERT INTO entregas (
                empleado_id, insumo_id, cantidad, observaciones, entregado_por, codigo
            ) VALUES (?, ?, ?, ?, ?, ?)
            """
            
            params = (
                data['empleado_id'],
                data['insumo_id'],
                data['cantidad'],
                data.get('observaciones', ''),
                data.get('entregado_por', ''),
                codigo
            )
            
            entrega_id = db_connection.execute_command(sql, params)
            self.logger.info(f"Entrega creada con ID: {entrega_id} y código: {codigo}")
            
            return entrega_id
            
        except Exception as e:
            self.logger.error(f"Error creando entrega: {e}")
            raise DatabaseException(f"Error creando entrega: {e}")
    
    def get_by_id(self, entrega_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene una entrega por su ID con información completa.
        
        Args:
            entrega_id: ID de la entrega
            
        Returns:
            Diccionario con datos completos de la entrega
        """
        try:
            sql = "SELECT * FROM vw_entregas_completas WHERE id = ?"
            rows = db_connection.execute_query(sql, (entrega_id,))
            
            if not rows:
                return None
            
            return self._row_to_dict(rows[0])
            
        except Exception as e:
            self.logger.error(f"Error obteniendo entrega ID {entrega_id}: {e}")
            raise DatabaseException(f"Error obteniendo entrega: {e}")
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Obtiene todas las entregas con información completa.
        
        Args:
            limit: Límite de resultados (para paginación)
            offset: Desplazamiento (para paginación)
            
        Returns:
            Lista de entregas con información completa
        """
        try:
            sql = "SELECT * FROM vw_entregas_completas ORDER BY fecha_entrega DESC"
            
            if limit:
                sql += f" LIMIT {limit} OFFSET {offset}"
            
            rows = db_connection.execute_query(sql)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo lista de entregas: {e}")
            raise DatabaseException(f"Error obteniendo entregas: {e}")
    
    def get_by_empleado(self, empleado_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene entregas de un empleado específico.
        
        Args:
            empleado_id: ID del empleado
            limit: Límite de resultados
            
        Returns:
            Lista de entregas del empleado
        """
        try:
            sql = """
            SELECT * FROM vw_entregas_completas 
            WHERE empleado_id = ? 
            ORDER BY fecha_entrega DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            rows = db_connection.execute_query(sql, (empleado_id,))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo entregas del empleado {empleado_id}: {e}")
            raise DatabaseException(f"Error obteniendo entregas del empleado: {e}")
    
    def get_by_insumo(self, insumo_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Obtiene entregas de un insumo específico.
        
        Args:
            insumo_id: ID del insumo
            limit: Límite de resultados
            
        Returns:
            Lista de entregas del insumo
        """
        try:
            sql = """
            SELECT * FROM vw_entregas_completas 
            WHERE insumo_id = ? 
            ORDER BY fecha_entrega DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            
            rows = db_connection.execute_query(sql, (insumo_id,))
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo entregas del insumo {insumo_id}: {e}")
            raise DatabaseException(f"Error obteniendo entregas del insumo: {e}")
    
    def get_by_date_range(self, fecha_inicio: date, fecha_fin: date) -> List[Dict[str, Any]]:
        """
        Obtiene entregas en un rango de fechas.
        
        Args:
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            
        Returns:
            Lista de entregas en el rango
        """
        try:
            sql = """
            SELECT * FROM vw_entregas_completas 
            WHERE DATE(fecha_entrega) BETWEEN ? AND ? 
            ORDER BY fecha_entrega DESC
            """
            
            params = (fecha_inicio.isoformat(), fecha_fin.isoformat())
            rows = db_connection.execute_query(sql, params)
            return self._rows_to_list(rows)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo entregas por rango de fechas: {e}")
            raise DatabaseException(f"Error obteniendo entregas por rango: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de entregas.
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            # Total de entregas
            total_sql = "SELECT COUNT(*) FROM entregas"
            total_rows = db_connection.execute_query(total_sql)
            total_entregas = total_rows[0][0]
            
            # Entregas hoy
            today_sql = "SELECT COUNT(*) FROM entregas WHERE DATE(fecha_entrega) = DATE('now')"
            today_rows = db_connection.execute_query(today_sql)
            entregas_hoy = today_rows[0][0]
            
            # Entregas esta semana
            week_sql = """
            SELECT COUNT(*) FROM entregas
            WHERE DATE(fecha_entrega) >= DATE('now', '-7 days')
            """
            week_rows = db_connection.execute_query(week_sql)
            entregas_semana = week_rows[0][0]
            
            # Insumo más solicitado
            popular_sql = """
            SELECT i.nombre, COUNT(*) as total_entregas
            FROM entregas e
            JOIN insumos i ON e.insumo_id = i.id
            GROUP BY e.insumo_id, i.nombre
            ORDER BY total_entregas DESC
            LIMIT 1
            """
            popular_rows = db_connection.execute_query(popular_sql)
            insumo_popular = popular_rows[0] if popular_rows else None
            
            return {
                'total_entregas': total_entregas,
                'entregas_hoy': entregas_hoy,
                'entregas_semana': entregas_semana,
                'insumo_mas_solicitado': {
                    'nombre': insumo_popular[0],
                    'total_entregas': insumo_popular[1]
                } if insumo_popular else None
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de entregas: {e}")
            raise DatabaseException(f"Error obteniendo estadísticas: {e}")
    
    def count_total(self) -> int:
        """
        Cuenta el total de entregas.
        
        Returns:
            Número total de entregas
        """
        try:
            sql = "SELECT COUNT(*) FROM entregas"
            rows = db_connection.execute_query(sql)
            return rows[0][0]
            
        except Exception as e:
            self.logger.error(f"Error contando entregas: {e}")
            raise DatabaseException(f"Error contando entregas: {e}")
    
    def delete(self, entrega_id: int) -> bool:
        """
        Elimina una entrega de forma permanente.
        
        Args:
            entrega_id: ID de la entrega
            
        Returns:
            True si la eliminación fue exitosa
        """
        try:
            sql = "DELETE FROM entregas WHERE id = ?"
            rows_affected = db_connection.execute_command(sql, (entrega_id,))
            
            if rows_affected > 0:
                self.logger.info(f"Entrega {entrega_id} eliminada físicamente")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error eliminando entrega {entrega_id}: {e}")
            raise DatabaseException(f"Error eliminando entrega: {e}")
 
 
# Instancias globales de los repositorios
insumo_repo = InsumoRepository()
empleado_repo = EmpleadoRepository()
entrega_repo = EntregaRepository()


def backup_db(backup_name: str = None) -> Dict[str, Any]:
    """
    [LEGACY] Crea un backup completo de la base de datos copiando el archivo .db.

    Esta función se mantiene solo por compatibilidad hacia atrás. El flujo
    recomendado para nuevos desarrollos es utilizar:

        services.backup_service.BackupService.crear_backup_manual

    Args:
        backup_name: Nombre personalizado para el backup (opcional)

    Returns:
        Diccionario con información del backup creado
    """
    try:
        # Obtener ruta de la base de datos
        db_path = get_db_path()
        if not db_path.exists():
            raise DatabaseException("Base de datos no encontrada")

        # Crear directorio de backups si no existe
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        # Generar nombre del backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if backup_name:
            safe_name = safe_filename(backup_name)
            backup_filename = f"{timestamp}_{safe_name}.db"
        else:
            backup_filename = f"backup_{timestamp}.db"

        backup_path = backup_dir / backup_filename

        # Crear backup usando shutil.copy2 (preserva metadatos)
        shutil.copy2(db_path, backup_path)

        # Verificar que el backup se creó correctamente
        if not backup_path.exists():
            raise DatabaseException("Error creando archivo de backup")

        # Obtener tamaño del archivo
        size_bytes = backup_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        # Información del backup
        backup_info = {
            'filename': backup_filename,
            'path': str(backup_path),
            'size_bytes': size_bytes,
            'size_mb': round(size_mb, 2),
            'created_at': datetime.now().isoformat(),
            'original_db': str(db_path)
        }

        # Log del backup exitoso
        LoggerMixin().logger.info(f"Backup creado exitosamente: {backup_filename} ({size_mb:.2f} MB)")

        return {
            'success': True,
            'message': f'Backup creado exitosamente: {backup_filename}',
            'backup_info': backup_info
        }

    except Exception as e:
        error_msg = f"Error creando backup: {str(e)}"
        LoggerMixin().logger.error(error_msg)
        return {
            'success': False,
            'message': error_msg,
            'error': str(e)
        }