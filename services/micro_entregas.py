"""
DelegInsumos - Microservicio de Entregas
Maneja toda la lógica de negocio para la gestión de entregas de insumos
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

from database.operations import entrega_repo, insumo_repo, empleado_repo
from models.entrega import Entrega, create_entrega_from_form_data, calculate_delivery_statistics
from services.micro_insumos import micro_insumos
from services.micro_empleados import micro_empleados
from utils.logger import LoggerMixin, log_operation
from utils.validators import validate_entrega_data
from utils.helpers import format_date
from exceptions.custom_exceptions import (
    service_exception_handler,
    BusinessLogicException,
    RecordNotFoundException,
    InsufficientStockException
)


class MicroEntregasService(LoggerMixin):
    """
    Microservicio para gestión completa de entregas
    """
    
    def __init__(self):
        super().__init__()
        self._repository = entrega_repo
        self._insumo_repo = insumo_repo
        self._empleado_repo = empleado_repo
        self.logger.info("MicroEntregasService inicializado")
    
    @service_exception_handler("MicroEntregasService")
    def crear_entrega(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea una nueva entrega de insumos.
        
        Args:
            form_data: Datos del formulario de entrega
            
        Returns:
            Diccionario con información de la entrega creada
            
        Raises:
            ValidationException: Si los datos no son válidos
            RecordNotFoundException: Si el empleado o insumo no existen
            InsufficientStockException: Si no hay stock suficiente
        """
        self.logger.info(f"Creando nueva entrega: Empleado ID {form_data.get('empleado_id', 'N/A')}, "
                        f"Insumo ID {form_data.get('insumo_id', 'N/A')}")
        
        # Validar datos básicos
        validated_data = validate_entrega_data(form_data)
        
        # Verificar que el empleado existe y puede recibir insumos
        empleado_validation = micro_empleados.validar_empleado_para_entrega(validated_data['empleado_id'])
        if not empleado_validation['can_receive']:
            raise BusinessLogicException(empleado_validation['message'])
        
        # Verificar que el insumo existe y hay stock suficiente
        stock_validation = micro_insumos.validar_stock_para_entrega(
            validated_data['insumo_id'], 
            validated_data['cantidad']
        )
        if not stock_validation['can_fulfill']:
            raise InsufficientStockException(
                stock_validation['insumo_nombre'],
                stock_validation['stock_actual'],
                validated_data['cantidad']
            )
        
        # Agregar fecha actual si no se especifica
        if 'fecha_entrega' not in validated_data:
            validated_data['fecha_entrega'] = datetime.now()
        
        # Crear entrega en base de datos (los triggers de BD actualizarán el stock automáticamente)
        entrega_id = self._repository.create(validated_data)
        
        # Obtener la entrega completa con información relacionada
        entrega_completa = self.obtener_entrega(entrega_id)
        
        log_operation("ENTREGA_CREADA", 
                     f"ID: {entrega_id}, Empleado: {empleado_validation['empleado_nombre']}, "
                     f"Insumo: {stock_validation['insumo_nombre']}, "
                     f"Cantidad: {validated_data['cantidad']}")
        
        self.logger.info(f"Entrega creada exitosamente con ID: {entrega_id}")
        
        return {
            'success': True,
            'entrega_id': entrega_id,
            'entrega': entrega_completa,
            'stock_anterior': stock_validation['stock_actual'],
            'stock_nuevo': stock_validation['stock_restante'],
            'message': f"Entrega registrada exitosamente"
        }
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entrega(self, entrega_id: int, include_details: bool = True) -> Dict[str, Any]:
        """
        Obtiene una entrega específica por su ID.
        
        Args:
            entrega_id: ID de la entrega
            include_details: Si incluir información detallada
            
        Returns:
            Diccionario con información completa de la entrega
            
        Raises:
            RecordNotFoundException: Si la entrega no existe
        """
        self.logger.debug(f"Obteniendo entrega ID: {entrega_id}")
        
        # Obtener de base de datos con información completa
        entrega_data = self._repository.get_by_id(entrega_id)
        if not entrega_data:
            raise RecordNotFoundException("entrega", str(entrega_id))
        
        # Crear modelo
        entrega = Entrega.from_dict(entrega_data)
        result = entrega.to_dict(include_relations=True)
        
        if include_details:
            result.update({
                'display_info': entrega.get_display_info(),
                'audit_info': entrega.get_audit_info(),
                'priority': entrega.get_priority_level(),
                'summary': entrega.get_delivery_summary(),
                'is_recent': entrega.is_recent(),
                'is_high_value': entrega.is_high_value(),
                'is_high_quantity': entrega.is_high_quantity()
            })
        
        return result
    
    @service_exception_handler("MicroEntregasService")
    def eliminar_entrega(self, entrega_id: int) -> Dict[str, Any]:
        """
        Elimina una entrega del sistema.
        
        Nota importante:
            Esta operación elimina el registro de la entrega, pero NO ajusta
            automáticamente el stock del insumo asociado. Si la entrega fue
            registrada por error, se recomienda corregir manualmente el stock
            desde la pestaña de Insumos.
        
        Args:
            entrega_id: ID de la entrega a eliminar
        
        Returns:
            Diccionario con resultado de la operación
        
        Raises:
            RecordNotFoundException: Si la entrega no existe
        """
        self.logger.info(f"Eliminando entrega ID: {entrega_id}")
        
        # Verificar que la entrega exista
        entrega_data = self._repository.get_by_id(entrega_id)
        if not entrega_data:
            raise RecordNotFoundException("entrega", str(entrega_id))
        
        # Guardar datos para logging/mensajes
        codigo = entrega_data.get("codigo") or f"#{entrega_id}"
        empleado_nombre = entrega_data.get("empleado_nombre", "N/D")
        insumo_nombre = entrega_data.get("insumo_nombre", "N/D")
        cantidad = entrega_data.get("cantidad", 0)
        
        # Eliminar la entrega
        success = self._repository.delete(entrega_id)
        if not success:
            raise BusinessLogicException("No se pudo eliminar la entrega seleccionada")
        
        log_operation(
            "ENTREGA_ELIMINADA",
            f"ID: {entrega_id}, Código: {codigo}, Empleado: {empleado_nombre}, "
            f"Insumo: {insumo_nombre}, Cantidad: {cantidad}"
        )
        self.logger.info(f"Entrega {entrega_id} eliminada exitosamente")
        
        return {
            "success": True,
            "message": f"Entrega {codigo} eliminada exitosamente"
        }
    
    @service_exception_handler("MicroEntregasService")
    def listar_entregas(self, limit: Optional[int] = 100, offset: int = 0, 
                       include_stats: bool = True) -> Dict[str, Any]:
        """
        Lista las entregas del sistema.
        
        Args:
            limit: Límite de resultados para paginación
            offset: Desplazamiento para paginación
            include_stats: Si incluir estadísticas
            
        Returns:
            Diccionario con lista de entregas y estadísticas
        """
        self.logger.debug(f"Listando entregas (limit: {limit}, offset: {offset})")
        
        # Obtener entregas de base de datos
        entregas_data = self._repository.get_all(limit=limit, offset=offset)
        
        # Crear modelos
        entregas = [Entrega.from_dict(data) for data in entregas_data]
        
        result = {
            'entregas': [entrega.to_dict(include_relations=True) for entrega in entregas],
            'total_returned': len(entregas),
            'offset': offset,
            'limit': limit
        }
        
        if include_stats:
            # Obtener estadísticas generales
            stats = self._repository.get_statistics()
            
            # Calcular estadísticas detalladas de las entregas actuales
            detailed_stats = calculate_delivery_statistics(entregas)
            
            result.update({
                'general_statistics': stats,
                'current_page_statistics': detailed_stats
            })
        
        # Obtener total de registros para paginación
        total_count = self._repository.count_total()
        result['total_count'] = total_count
        
        log_operation("ENTREGAS_LISTADAS", f"Devueltas: {len(entregas)}, Offset: {offset}")
        return result
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_por_empleado(self, empleado_id: int, 
                                    limit: Optional[int] = 50) -> Dict[str, Any]:
        """
        Obtiene entregas de un empleado específico.
        
        Args:
            empleado_id: ID del empleado
            limit: Límite de resultados
            
        Returns:
            Diccionario con entregas del empleado
        """
        self.logger.debug(f"Obteniendo entregas del empleado ID: {empleado_id}")
        
        # Verificar que el empleado existe
        empleado_info = micro_empleados.obtener_empleado(empleado_id)
        
        # Obtener entregas
        entregas_data = self._repository.get_by_empleado(empleado_id, limit=limit)
        entregas = [Entrega.from_dict(data) for data in entregas_data]
        
        # Calcular estadísticas del empleado
        empleado_stats = calculate_delivery_statistics(entregas)
        
        return {
            'empleado_info': {
                'id': empleado_info['id'],
                'nombre_completo': empleado_info['nombre_completo'],
                'cedula': empleado_info['cedula'],
                'departamento': empleado_info['departamento'],
                'cargo': empleado_info['cargo']
            },
            'entregas': [entrega.to_dict(include_relations=True) for entrega in entregas],
            'total_entregas': len(entregas),
            'statistics': empleado_stats
        }
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_por_insumo(self, insumo_id: int, 
                                  limit: Optional[int] = 50) -> Dict[str, Any]:
        """
        Obtiene entregas de un insumo específico.
        
        Args:
            insumo_id: ID del insumo
            limit: Límite de resultados
            
        Returns:
            Diccionario con entregas del insumo
        """
        self.logger.debug(f"Obteniendo entregas del insumo ID: {insumo_id}")
        
        # Verificar que el insumo existe
        insumo_info = micro_insumos.obtener_insumo(insumo_id)
        
        # Obtener entregas
        entregas_data = self._repository.get_by_insumo(insumo_id, limit=limit)
        entregas = [Entrega.from_dict(data) for data in entregas_data]
        
        # Calcular estadísticas del insumo
        insumo_stats = calculate_delivery_statistics(entregas)
        
        return {
            'insumo_info': {
                'id': insumo_info['id'],
                'nombre': insumo_info['nombre'],
                'categoria': insumo_info['categoria'],
                'cantidad_actual': insumo_info['cantidad_actual'],
                'unidad_medida': insumo_info['unidad_medida']
            },
            'entregas': [entrega.to_dict(include_relations=True) for entrega in entregas],
            'total_entregas': len(entregas),
            'statistics': insumo_stats
        }
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_por_rango_fechas(self, fecha_inicio: date, fecha_fin: date) -> Dict[str, Any]:
        """
        Obtiene entregas en un rango de fechas.
        
        Args:
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            
        Returns:
            Diccionario con entregas del rango
        """
        self.logger.debug(f"Obteniendo entregas del {fecha_inicio} al {fecha_fin}")
        
        # Normalizar a tipo date en caso de recibir datetime
        try:
            if isinstance(fecha_inicio, datetime):
                fecha_inicio = fecha_inicio.date()
            if isinstance(fecha_fin, datetime):
                fecha_fin = fecha_fin.date()
        except Exception:
            # Si falla la normalización, continuar con los valores originales
            pass
        
        # Validar rango de fechas (seguro con tipos date)
        if fecha_inicio > fecha_fin:
            raise BusinessLogicException("La fecha de inicio no puede ser mayor a la fecha de fin")
        
        today = date.today()
        if fecha_fin > today:
            fecha_fin = today  # No mostrar fechas futuras
        
        # Obtener entregas
        entregas_data = self._repository.get_by_date_range(fecha_inicio, fecha_fin)
        entregas = [Entrega.from_dict(data) for data in entregas_data]
        
        # Calcular estadísticas del período
        period_stats = calculate_delivery_statistics(entregas)
        
        return {
            'fecha_inicio': fecha_inicio.isoformat(),
            'fecha_fin': fecha_fin.isoformat(),
            'dias_periodo': (fecha_fin - fecha_inicio).days + 1,
            'entregas': [entrega.to_dict(include_relations=True) for entrega in entregas],
            'total_entregas': len(entregas),
            'statistics': period_stats
        }
    
    @service_exception_handler("MicroEntregasService")
    def buscar_entregas(self, termino: str, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        Busca entregas por término de búsqueda.
        
        Args:
            termino: Término de búsqueda
            limit: Límite de resultados
            
        Returns:
            Lista de entregas que coinciden
        """
        self.logger.debug(f"Buscando entregas: '{termino}'")
        
        # Obtener todas las entregas recientes para buscar
        entregas_data = self._repository.get_all(limit=limit or 200)
        
        # Filtrar por término de búsqueda
        matching_entregas = []
        for data in entregas_data:
            entrega = Entrega.from_dict(data)
            if entrega.matches_search_term(termino):
                entrega_dict = entrega.to_dict(include_relations=True)
                entrega_dict['display_info'] = entrega.get_display_info()
                matching_entregas.append(entrega_dict)
                
                # Limitar resultados
                if limit and len(matching_entregas) >= limit:
                    break
        
        log_operation("ENTREGAS_BUSCADAS", f"Término: '{termino}', Encontradas: {len(matching_entregas)}")
        return matching_entregas
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_recientes(self, dias: int = 7, limit: Optional[int] = 50) -> Dict[str, Any]:
        """
        Obtiene entregas recientes.
        
        Args:
            dias: Número de días hacia atrás
            limit: Límite de resultados
            
        Returns:
            Diccionario con entregas recientes
        """
        self.logger.debug(f"Obteniendo entregas de los últimos {dias} días")
        
        # Calcular rango de fechas
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=dias)
        
        return self.obtener_entregas_por_rango_fechas(fecha_inicio, fecha_fin)
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_hoy(self) -> Dict[str, Any]:
        """
        Obtiene entregas del día actual.
        
        Returns:
            Diccionario con entregas de hoy
        """
        today = date.today()
        return self.obtener_entregas_por_rango_fechas(today, today)
    
    @service_exception_handler("MicroEntregasService")
    def obtener_estadisticas_entregas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas completas de entregas.
        
        Returns:
            Diccionario con estadísticas detalladas
        """
        self.logger.debug("Obteniendo estadísticas completas de entregas")
        
        # Estadísticas generales de la base de datos
        general_stats = self._repository.get_statistics()
        
        # Obtener entregas recientes para análisis detallado
        recent_data = self._repository.get_all(limit=500)  # Últimas 500 entregas
        recent_entregas = [Entrega.from_dict(data) for data in recent_data]
        
        # Calcular estadísticas detalladas
        detailed_stats = calculate_delivery_statistics(recent_entregas)
        
        # Estadísticas por período
        today_stats = self.obtener_entregas_hoy()
        week_stats = self.obtener_entregas_recientes(7)
        month_stats = self.obtener_entregas_recientes(30)
        
        complete_stats = {
            'general': general_stats,
            'detailed': detailed_stats,
            'periods': {
                'today': {
                    'total_entregas': today_stats['total_entregas'],
                    'valor_total': today_stats['statistics']['valor_total_formatted']
                },
                'week': {
                    'total_entregas': week_stats['total_entregas'],
                    'valor_total': week_stats['statistics']['valor_total_formatted']
                },
                'month': {
                    'total_entregas': month_stats['total_entregas'],
                    'valor_total': month_stats['statistics']['valor_total_formatted']
                }
            },
            'last_updated': datetime.now().isoformat()
        }
        
        log_operation("ESTADISTICAS_ENTREGAS_OBTENIDAS", f"Análisis de {len(recent_entregas)} entregas")
        return complete_stats
    
    @service_exception_handler("MicroEntregasService")
    def obtener_entregas_alto_valor(self, threshold: float = 50000.0) -> List[Dict[str, Any]]:
        """
        Obtiene entregas de alto valor.
        
        Args:
            threshold: Umbral de valor en pesos
            
        Returns:
            Lista de entregas de alto valor
        """
        # Obtener entregas recientes
        entregas_data = self._repository.get_all(limit=200)
        
        # Filtrar por alto valor
        high_value_entregas = []
        for data in entregas_data:
            entrega = Entrega.from_dict(data)
            if entrega.is_high_value(threshold):
                entrega_dict = entrega.to_dict(include_relations=True)
                entrega_dict['display_info'] = entrega.get_display_info()
                high_value_entregas.append(entrega_dict)
        
        return high_value_entregas
    
    @service_exception_handler("MicroEntregasService")
    def obtener_top_empleados_entregas(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene los empleados con más entregas.
        
        Args:
            limit: Número de empleados a retornar
            
        Returns:
            Lista de empleados ordenados por número de entregas
        """
        # Obtener todas las entregas de los últimos 30 días
        thirty_days_ago = date.today() - timedelta(days=30)
        entregas_data = self._repository.get_by_date_range(thirty_days_ago, date.today())
        
        # Contar entregas por empleado
        employee_counts = {}
        for data in entregas_data:
            emp_key = f"{data['empleado_id']}"
            if emp_key not in employee_counts:
                employee_counts[emp_key] = {
                    'empleado_id': data['empleado_id'],
                    'empleado_nombre': data['empleado_nombre'],
                    'empleado_departamento': data['empleado_departamento'],
                    'empleado_cedula': data['empleado_cedula'],
                    'total_entregas': 0,
                    'total_cantidad': 0,
                    'valor_total': 0
                }
            
            employee_counts[emp_key]['total_entregas'] += 1
            employee_counts[emp_key]['total_cantidad'] += data['cantidad']
            if data.get('valor_total'):
                employee_counts[emp_key]['valor_total'] += float(data['valor_total'])
        
        # Ordenar por número de entregas
        top_employees = sorted(employee_counts.values(), 
                             key=lambda x: x['total_entregas'], 
                             reverse=True)[:limit]
        
        return top_employees
    
    @service_exception_handler("MicroEntregasService")
    def obtener_top_insumos_entregados(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene los insumos más entregados.
        
        Args:
            limit: Número de insumos a retornar
            
        Returns:
            Lista de insumos ordenados por cantidad entregada
        """
        # Obtener entregas de los últimos 30 días
        thirty_days_ago = date.today() - timedelta(days=30)
        entregas_data = self._repository.get_by_date_range(thirty_days_ago, date.today())
        
        # Contar por insumo
        insumo_counts = {}
        for data in entregas_data:
            ins_key = f"{data['insumo_id']}"
            if ins_key not in insumo_counts:
                insumo_counts[ins_key] = {
                    'insumo_id': data['insumo_id'],
                    'insumo_nombre': data['insumo_nombre'],
                    'insumo_categoria': data['insumo_categoria'],
                    'insumo_unidad': data['insumo_unidad'],
                    'total_entregas': 0,
                    'cantidad_total': 0,
                    'valor_total': 0
                }
            
            insumo_counts[ins_key]['total_entregas'] += 1
            insumo_counts[ins_key]['cantidad_total'] += data['cantidad']
            if data.get('valor_total'):
                insumo_counts[ins_key]['valor_total'] += float(data['valor_total'])
        
        # Ordenar por cantidad total entregada
        top_insumos = sorted(insumo_counts.values(), 
                           key=lambda x: x['cantidad_total'], 
                           reverse=True)[:limit]
        
        return top_insumos


# Instancia global del microservicio
micro_entregas = MicroEntregasService()

# Funciones de conveniencia para uso directo
def crear_entrega(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Función de conveniencia para crear entrega"""
    return micro_entregas.crear_entrega(form_data)

def obtener_entrega(entrega_id: int) -> Dict[str, Any]:
    """Función de conveniencia para obtener entrega"""
    return micro_entregas.obtener_entrega(entrega_id)

def listar_entregas(limit: Optional[int] = 100) -> Dict[str, Any]:
    """Función de conveniencia para listar entregas"""
    return micro_entregas.listar_entregas(limit)

def obtener_entregas_hoy() -> Dict[str, Any]:
    """Función de conveniencia para obtener entregas de hoy"""
    return micro_entregas.obtener_entregas_hoy()

def obtener_estadisticas_entregas() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas"""
    return micro_entregas.obtener_estadisticas_entregas()

def eliminar_entrega(entrega_id: int) -> Dict[str, Any]:
    """Función de conveniencia para eliminar una entrega"""
    return micro_entregas.eliminar_entrega(entrega_id)