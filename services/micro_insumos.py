"""
DelegInsumos - Microservicio de Insumos
Maneja toda la lógica de negocio para la gestión de insumos
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from database.operations import insumo_repo
from models.insumo import Insumo, create_insumo_from_form_data, get_insumos_by_status, calculate_inventory_value
from utils.logger import LoggerMixin, log_operation
from utils.validators import validate_insumo_data
from exceptions.custom_exceptions import (
    service_exception_handler,
    BusinessLogicException,
    RecordNotFoundException,
    DuplicateRecordException,
    InsufficientStockException
)


class MicroInsumosService(LoggerMixin):
    """
    Microservicio para gestión completa de insumos
    """
    
    def __init__(self):
        super().__init__()
        self._repository = insumo_repo
        self.logger.info("MicroInsumosService inicializado")
    
    @service_exception_handler("MicroInsumosService")
    def crear_insumo(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo insumo en el sistema.
        
        Args:
            form_data: Datos del formulario de insumo
            
        Returns:
            Diccionario con información del insumo creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            DuplicateRecordException: Si ya existe un insumo con el mismo nombre
        """
        self.logger.info(f"Creando nuevo insumo: {form_data.get('nombre', 'N/A')}")
        
        # Crear y validar modelo
        insumo = create_insumo_from_form_data(form_data)
        
        # Verificar duplicados por nombre
        existing = self.buscar_insumos(insumo.nombre, exact_match=True)
        if existing:
            raise DuplicateRecordException("insumo", "nombre", insumo.nombre)
        
        # Crear en base de datos
        insumo_id = self._repository.create(insumo.to_dict(include_audit=False))
        insumo.id = insumo_id
        
        log_operation("INSUMO_CREADO", f"ID: {insumo_id}, Nombre: {insumo.nombre}")
        self.logger.info(f"Insumo creado exitosamente con ID: {insumo_id}")
        
        return {
            'success': True,
            'insumo_id': insumo_id,
            'insumo': insumo.to_dict(),
            'message': f"Insumo '{insumo.nombre}' creado exitosamente"
        }
    
    @service_exception_handler("MicroInsumosService")
    def obtener_insumo(self, insumo_id: int, include_status: bool = True) -> Dict[str, Any]:
        """
        Obtiene un insumo específico por su ID.
        
        Args:
            insumo_id: ID del insumo
            include_status: Si incluir información de estado de stock
            
        Returns:
            Diccionario con información del insumo
            
        Raises:
            RecordNotFoundException: Si el insumo no existe
        """
        self.logger.debug(f"Obteniendo insumo ID: {insumo_id}")
        
        # Obtener de base de datos
        insumo_data = self._repository.get_by_id(insumo_id)
        if not insumo_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        # Crear modelo
        insumo = Insumo.from_dict(insumo_data)
        result = insumo.to_dict()
        
        if include_status:
            result.update({
                'status_info': insumo.get_stock_status(),
                'display_info': insumo.get_display_info(),
                'needs_restock': insumo.needs_restock(),
                'is_critical': insumo.is_critical_stock(),
                'suggested_order': insumo.get_suggested_order_quantity()
            })
        
        return result
    
    @service_exception_handler("MicroInsumosService")
    def listar_insumos(self, active_only: bool = True, include_status: bool = True) -> Dict[str, Any]:
        """
        Lista todos los insumos del sistema.
        
        Args:
            active_only: Si solo mostrar insumos activos
            include_status: Si incluir información de estado
            
        Returns:
            Diccionario con lista de insumos y estadísticas
        """
        self.logger.debug(f"Listando insumos (activos: {active_only})")
        
        # Obtener de base de datos
        insumos_data = self._repository.get_all(active_only=active_only)
        
        # Crear modelos
        insumos = [Insumo.from_dict(data) for data in insumos_data]
        
        result = {
            'insumos': [insumo.to_dict() for insumo in insumos],
            'total': len(insumos)
        }
        
        if include_status:
            # Agrupar por estado
            grouped = get_insumos_by_status(insumos)
            
            # Calcular estadísticas
            stats = calculate_inventory_value(insumos)
            
            result.update({
                'by_status': {
                    'criticos': len(grouped['CRITICO']),
                    'bajo_stock': len(grouped['BAJO']),
                    'normales': len(grouped['NORMAL']),
                    'exceso': len(grouped['EXCESO'])
                },
                'statistics': stats,
                'alerts': len(grouped['CRITICO']) + len(grouped['BAJO'])
            })
        
        log_operation("INSUMOS_LISTADOS", f"Total: {len(insumos)}, Activos: {active_only}")
        return result
    
    @service_exception_handler("MicroInsumosService")
    def actualizar_insumo(self, insumo_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un insumo existente.
        
        Args:
            insumo_id: ID del insumo
            form_data: Datos actualizados del formulario
            
        Returns:
            Diccionario con información del insumo actualizado
            
        Raises:
            RecordNotFoundException: Si el insumo no existe
            ValidationException: Si los datos no son válidos
        """
        self.logger.info(f"Actualizando insumo ID: {insumo_id}")
        
        # Verificar que existe
        existing_data = self._repository.get_by_id(insumo_id)
        if not existing_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        # Validar los nuevos datos
        validated_data = validate_insumo_data(form_data)
        
        # Verificar duplicados por nombre (excluyendo el mismo registro)
        if 'nombre' in validated_data:
            existing_same_name = self.buscar_insumos(validated_data['nombre'], exact_match=True)
            if existing_same_name and existing_same_name[0]['id'] != insumo_id:
                raise DuplicateRecordException("insumo", "nombre", validated_data['nombre'])
        
        # Actualizar en base de datos
        success = self._repository.update(insumo_id, validated_data)
        
        if not success:
            raise BusinessLogicException("No se pudo actualizar el insumo")
        
        # Obtener datos actualizados
        updated_insumo = self.obtener_insumo(insumo_id)
        
        log_operation("INSUMO_ACTUALIZADO", f"ID: {insumo_id}")
        self.logger.info(f"Insumo {insumo_id} actualizado exitosamente")
        
        return {
            'success': True,
            'insumo': updated_insumo,
            'message': f"Insumo actualizado exitosamente"
        }
    
    @service_exception_handler("MicroInsumosService")
    def eliminar_insumo(self, insumo_id: int, soft_delete: bool = True) -> Dict[str, Any]:
        """
        Elimina un insumo del sistema.
        
        Args:
            insumo_id: ID del insumo
            soft_delete: Si usar eliminación suave
            
        Returns:
            Diccionario con resultado de la eliminación
            
        Raises:
            RecordNotFoundException: Si el insumo no existe
        """
        self.logger.info(f"Eliminando insumo ID: {insumo_id} (soft: {soft_delete})")
        
        # Verificar que existe
        existing_data = self._repository.get_by_id(insumo_id)
        if not existing_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        insumo_nombre = existing_data.get('nombre', 'N/A')
        
        # Eliminar
        success = self._repository.delete(insumo_id, soft_delete=soft_delete)
        
        if not success:
            raise BusinessLogicException("No se pudo eliminar el insumo")
        
        delete_type = "eliminado" if not soft_delete else "desactivado"
        log_operation("INSUMO_ELIMINADO", f"ID: {insumo_id}, Tipo: {delete_type}")
        self.logger.info(f"Insumo {insumo_id} {delete_type} exitosamente")
        
        return {
            'success': True,
            'message': f"Insumo '{insumo_nombre}' {delete_type} exitosamente"
        }
    
    @service_exception_handler("MicroInsumosService")
    def actualizar_stock(self, insumo_id: int, nueva_cantidad: int, motivo: str = "") -> Dict[str, Any]:
        """
        Actualiza el stock de un insumo.
        
        Args:
            insumo_id: ID del insumo
            nueva_cantidad: Nueva cantidad de stock
            motivo: Motivo del cambio de stock
            
        Returns:
            Diccionario con resultado de la actualización
            
        Raises:
            RecordNotFoundException: Si el insumo no existe
            ValidationException: Si la cantidad no es válida
        """
        self.logger.info(f"Actualizando stock insumo {insumo_id}: {nueva_cantidad}")
        
        # Verificar que existe y obtener datos actuales
        existing_data = self._repository.get_by_id(insumo_id)
        if not existing_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        cantidad_anterior = existing_data.get('cantidad_actual', 0)
        
        if nueva_cantidad < 0:
            raise BusinessLogicException("La cantidad de stock no puede ser negativa")
        
        # Actualizar stock
        success = self._repository.update_stock(insumo_id, nueva_cantidad)
        
        if not success:
            raise BusinessLogicException("No se pudo actualizar el stock")
        
        # Obtener datos actualizados
        updated_insumo = self.obtener_insumo(insumo_id)
        
        log_operation("STOCK_ACTUALIZADO", 
                     f"ID: {insumo_id}, Anterior: {cantidad_anterior}, "
                     f"Nuevo: {nueva_cantidad}, Motivo: {motivo}")
        
        return {
            'success': True,
            'insumo': updated_insumo,
            'cantidad_anterior': cantidad_anterior,
            'cantidad_nueva': nueva_cantidad,
            'diferencia': nueva_cantidad - cantidad_anterior,
            'message': f"Stock actualizado de {cantidad_anterior} a {nueva_cantidad}"
        }
    
    @service_exception_handler("MicroInsumosService")
    def reducir_stock_por_entrega(self, insumo_id: int, cantidad_entregada: int) -> Dict[str, Any]:
        """
        Reduce el stock por una entrega.
        
        Args:
            insumo_id: ID del insumo
            cantidad_entregada: Cantidad entregada
            
        Returns:
            Diccionario con resultado de la reducción
            
        Raises:
            InsufficientStockException: Si no hay stock suficiente
        """
        # Verificar que existe y obtener datos actuales
        existing_data = self._repository.get_by_id(insumo_id)
        if not existing_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        insumo = Insumo.from_dict(existing_data)
        
        # Verificar stock suficiente
        if not insumo.can_fulfill_request(cantidad_entregada):
            raise InsufficientStockException(
                insumo.nombre, 
                insumo.cantidad_actual, 
                cantidad_entregada
            )
        
        # Reducir stock
        nueva_cantidad = insumo.cantidad_actual - cantidad_entregada
        return self.actualizar_stock(insumo_id, nueva_cantidad, "Entrega de insumo")
    
    @service_exception_handler("MicroInsumosService")
    def buscar_insumos(self, termino: str, exact_match: bool = False) -> List[Dict[str, Any]]:
        """
        Busca insumos por término de búsqueda.
        
        Args:
            termino: Término de búsqueda
            exact_match: Si buscar coincidencia exacta
            
        Returns:
            Lista de insumos que coinciden
        """
        self.logger.debug(f"Buscando insumos: '{termino}' (exacto: {exact_match})")
        
        if exact_match:
            # Búsqueda exacta por nombre
            all_insumos = self._repository.get_all(active_only=True)
            matching = [data for data in all_insumos 
                       if data['nombre'].lower() == termino.lower()]
        else:
            # Búsqueda flexible
            matching = self._repository.search(termino, active_only=True)
        
        # Crear modelos y agregar información de estado
        results = []
        for data in matching:
            insumo = Insumo.from_dict(data)
            insumo_dict = insumo.to_dict()
            insumo_dict['status_info'] = insumo.get_stock_status()
            insumo_dict['display_info'] = insumo.get_display_info()
            results.append(insumo_dict)
        
        log_operation("INSUMOS_BUSCADOS", f"Término: '{termino}', Encontrados: {len(results)}")
        return results
    
    @service_exception_handler("MicroInsumosService")
    def obtener_por_categoria(self, categoria: str) -> List[Dict[str, Any]]:
        """
        Obtiene insumos de una categoría específica.
        
        Args:
            categoria: Categoría a filtrar
            
        Returns:
            Lista de insumos de la categoría
        """
        self.logger.debug(f"Obteniendo insumos de categoría: {categoria}")
        
        insumos_data = self._repository.get_by_categoria(categoria, active_only=True)
        
        results = []
        for data in insumos_data:
            insumo = Insumo.from_dict(data)
            insumo_dict = insumo.to_dict()
            insumo_dict['status_info'] = insumo.get_stock_status()
            results.append(insumo_dict)
        
        return results
    
    @service_exception_handler("MicroInsumosService")
    def obtener_alertas_stock(self) -> Dict[str, Any]:
        """
        Obtiene insumos con alertas de stock.
        
        Returns:
            Diccionario con alertas organizadas por tipo
        """
        self.logger.debug("Obteniendo alertas de stock")
        
        alerts_data = self._repository.get_stock_alerts()
        
        alerts = {
            'criticas': [],
            'bajas': [],
            'total_criticas': 0,
            'total_bajas': 0
        }
        
        for data in alerts_data:
            alert_item = {
                'id': data['id'],
                'nombre': data['nombre'],
                'categoria': data['categoria'],
                'cantidad_actual': data['cantidad_actual'],
                'cantidad_minima': data['cantidad_minima'],
                'unidad_medida': data['unidad_medida'],
                'estado_stock': data['estado_stock'],
                'color_estado': data['color_estado']
            }
            
            if data['estado_stock'] == 'CRITICO':
                alerts['criticas'].append(alert_item)
                alerts['total_criticas'] += 1
            elif data['estado_stock'] == 'BAJO':
                alerts['bajas'].append(alert_item)
                alerts['total_bajas'] += 1
        
        alerts['total_alertas'] = alerts['total_criticas'] + alerts['total_bajas']
        
        log_operation("ALERTAS_STOCK_OBTENIDAS", 
                     f"Críticas: {alerts['total_criticas']}, "
                     f"Bajas: {alerts['total_bajas']}")
        
        return alerts
    
    @service_exception_handler("MicroInsumosService")
    def obtener_categorias(self) -> List[str]:
        """
        Obtiene todas las categorías de insumos disponibles.
        
        Returns:
            Lista de categorías
        """
        return self._repository.get_categories()
    
    @service_exception_handler("MicroInsumosService")
    def obtener_resumen_por_categoria(self) -> List[Dict[str, Any]]:
        """
        Obtiene resumen de inventario agrupado por categoría.
        
        Returns:
            Lista con resumen por categoría
        """
        self.logger.debug("Obteniendo resumen por categoría")
        
        summary_data = self._repository.get_summary_by_category()
        
        # Formatear datos para presentación
        formatted_summary = []
        for data in summary_data:
            formatted_item = dict(data)
            formatted_item['valor_total_formatted'] = f"${formatted_item['valor_total']:,.2f}"
            formatted_item['promedio_cantidad_formatted'] = f"{formatted_item['promedio_cantidad']:.1f}"
            formatted_summary.append(formatted_item)
        
        return formatted_summary
    
    @service_exception_handler("MicroInsumosService")
    def validar_stock_para_entrega(self, insumo_id: int, cantidad_solicitada: int) -> Dict[str, Any]:
        """
        Valida si hay stock suficiente para una entrega.
        
        Args:
            insumo_id: ID del insumo
            cantidad_solicitada: Cantidad que se desea entregar
            
        Returns:
            Diccionario con resultado de la validación
        """
        # Obtener datos actuales
        existing_data = self._repository.get_by_id(insumo_id)
        if not existing_data:
            raise RecordNotFoundException("insumo", str(insumo_id))
        
        insumo = Insumo.from_dict(existing_data)
        
        can_fulfill = insumo.can_fulfill_request(cantidad_solicitada)
        
        return {
            'can_fulfill': can_fulfill,
            'insumo_nombre': insumo.nombre,
            'stock_actual': insumo.cantidad_actual,
            'cantidad_solicitada': cantidad_solicitada,
            'stock_restante': max(0, insumo.cantidad_actual - cantidad_solicitada),
            'unidad_medida': insumo.unidad_medida,
            'message': f"Stock {'suficiente' if can_fulfill else 'insuficiente'} para la entrega"
        }


# Instancia global del microservicio
micro_insumos = MicroInsumosService()

# Funciones de conveniencia para uso directo
def crear_insumo(form_data: Dict[str, Any]) -> Dict[str, Any]:
    return micro_insumos.crear_insumo(form_data)

def obtener_insumo(insumo_id: int) -> Dict[str, Any]:
    return micro_insumos.obtener_insumo(insumo_id)

def listar_insumos(active_only: bool = True) -> Dict[str, Any]:
    return micro_insumos.listar_insumos(active_only)

def obtener_alertas_stock() -> Dict[str, Any]:
    return micro_insumos.obtener_alertas_stock()