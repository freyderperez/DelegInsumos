"""
DelegInsumos - Modelo de Datos: Insumo
Define la estructura y comportamiento de la entidad Insumo
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from utils.validators import validate_insumo_data, DataValidator
from utils.helpers import get_stock_status, format_currency, format_date
from utils import generar_id
from exceptions.custom_exceptions import ValidationException


@dataclass
class Insumo:
    """
    Modelo de datos para un insumo del inventario
    """
    
    # Campos principales
    id: Optional[str] = None                 # ID interno (numérico/autoincremental)
    codigo: Optional[str] = None             # Código público legible (INS-YYYY-XXXX)
    nombre: str = ""
    categoria: str = ""
    cantidad_actual: int = 0
    cantidad_minima: int = 5
    cantidad_maxima: int = 100
    unidad_medida: str = "unidad"
    proveedor: str = ""
    
    # Campos de auditoría
    fecha_creacion: Optional[datetime] = None
    fecha_actualizacion: Optional[datetime] = None
    activo: bool = True
    
    def __post_init__(self):
        """Validaciones y conversiones post-inicialización"""
        # Generar ID si no se proporciona
        if not self.id:
            self.id = generar_id("INS")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Insumo':
        """
        Crea una instancia de Insumo desde un diccionario.
        
        Args:
            data: Diccionario con datos del insumo
            
        Returns:
            Instancia de Insumo
        """
        # Convertir fechas si están como string
        fecha_creacion = data.get('fecha_creacion')
        if isinstance(fecha_creacion, str):
            fecha_creacion = datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
        
        fecha_actualizacion = data.get('fecha_actualizacion')
        if isinstance(fecha_actualizacion, str):
            fecha_actualizacion = datetime.fromisoformat(fecha_actualizacion.replace('Z', '+00:00'))
        
        return cls(
            id=data.get('id'),
            codigo=data.get('codigo'),
            nombre=data.get('nombre', ''),
            categoria=data.get('categoria', ''),
            cantidad_actual=data.get('cantidad_actual', 0),
            cantidad_minima=data.get('cantidad_minima', 5),
            cantidad_maxima=data.get('cantidad_maxima', 100),
            unidad_medida=data.get('unidad_medida', 'unidad'),
            proveedor=data.get('proveedor', ''),
            fecha_creacion=fecha_creacion,
            fecha_actualizacion=fecha_actualizacion,
            activo=bool(data.get('activo', True))
        )
    
    def to_dict(self, include_audit: bool = True) -> Dict[str, Any]:
        """
        Convierte la instancia a diccionario.
        
        Args:
            include_audit: Si incluir campos de auditoría
            
        Returns:
            Diccionario con datos del insumo
        """
        result = {
            'nombre': self.nombre,
            'categoria': self.categoria,
            'cantidad_actual': self.cantidad_actual,
            'cantidad_minima': self.cantidad_minima,
            'cantidad_maxima': self.cantidad_maxima,
            'unidad_medida': self.unidad_medida,
            'proveedor': self.proveedor
        }
        
        if include_audit:
            result.update({
                'id': self.id,
                'codigo': self.codigo,
                'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
                'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
                'activo': self.activo
            })
        
        return result
    
    def validate_data(self) -> None:
        """
        Valida los datos del insumo.
        
        Raises:
            ValidationException: Si los datos no son válidos
        """
        data_dict = self.to_dict(include_audit=False)
        validate_insumo_data(data_dict)
        
        # Validaciones adicionales específicas del modelo
        if self.cantidad_actual < 0:
            raise ValidationException('cantidad_actual', 'No puede ser negativa')
        
        if self.cantidad_minima < 0:
            raise ValidationException('cantidad_minima', 'No puede ser negativa')
        
        if self.cantidad_maxima < self.cantidad_minima:
            raise ValidationException('cantidad_maxima', 'Debe ser mayor o igual a la cantidad mínima')
        
    
    def get_stock_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del stock.
        
        Returns:
            Diccionario con información del estado del stock
        """
        return get_stock_status(self.cantidad_actual, self.cantidad_minima, self.cantidad_maxima)
    
    def needs_restock(self) -> bool:
        """
        Determina si el insumo necesita reabastecimiento.
        
        Returns:
            True si el stock está por debajo del mínimo
        """
        return self.cantidad_actual <= self.cantidad_minima
    
    def is_critical_stock(self) -> bool:
        """
        Determina si el insumo tiene stock crítico.
        
        Returns:
            True si no hay stock disponible
        """
        return self.cantidad_actual <= 0
    
    def is_overstocked(self) -> bool:
        """
        Determina si el insumo tiene exceso de stock.
        
        Returns:
            True si el stock excede el máximo recomendado
        """
        return self.cantidad_actual >= self.cantidad_maxima
    
    def can_fulfill_request(self, cantidad_solicitada: int) -> bool:
        """
        Verifica si se puede entregar la cantidad solicitada.
        
        Args:
            cantidad_solicitada: Cantidad que se desea entregar
            
        Returns:
            True si hay stock suficiente
        """
        return self.cantidad_actual >= cantidad_solicitada
    
    
    def get_suggested_order_quantity(self) -> int:
        """
        Sugiere cantidad para pedido basada en niveles min/max.
        
        Returns:
            Cantidad sugerida para pedido
        """
        if not self.needs_restock():
            return 0
        
        # Sugerir cantidad para llegar al nivel máximo
        return max(0, self.cantidad_maxima - self.cantidad_actual)
    
    def update_stock(self, nueva_cantidad: int) -> None:
        """
        Actualiza la cantidad en stock.
        
        Args:
            nueva_cantidad: Nueva cantidad de stock
            
        Raises:
            ValidationException: Si la cantidad es inválida
        """
        if nueva_cantidad < 0:
            raise ValidationException('nueva_cantidad', 'No puede ser negativa')
        
        self.cantidad_actual = nueva_cantidad
    
    def reduce_stock(self, cantidad_entregada: int) -> None:
        """
        Reduce el stock por una entrega.
        
        Args:
            cantidad_entregada: Cantidad entregada
            
        Raises:
            ValidationException: Si no hay stock suficiente
        """
        if cantidad_entregada <= 0:
            raise ValidationException('cantidad_entregada', 'Debe ser mayor a cero')
        
        if not self.can_fulfill_request(cantidad_entregada):
            raise ValidationException(
                'cantidad_entregada', 
                f'Stock insuficiente. Disponible: {self.cantidad_actual}'
            )
        
        self.cantidad_actual -= cantidad_entregada
    
    def add_stock(self, cantidad_agregada: int) -> None:
        """
        Agrega stock al inventario.
        
        Args:
            cantidad_agregada: Cantidad a agregar
            
        Raises:
            ValidationException: Si la cantidad es inválida
        """
        if cantidad_agregada <= 0:
            raise ValidationException('cantidad_agregada', 'Debe ser mayor a cero')
        
        self.cantidad_actual += cantidad_agregada
    
    def get_display_info(self) -> Dict[str, str]:
        """
        Obtiene información formateada para mostrar en la UI.
        
        Returns:
            Diccionario con información formateada
        """
        status = self.get_stock_status()
        
        return {
            'id': str(self.id) if self.id else 'N/A',
            'codigo': self.codigo or 'N/A',
            'nombre': self.nombre,
            'categoria': self.categoria,
            'stock_actual': f"{self.cantidad_actual} {self.unidad_medida}",
            'stock_minimo': f"{self.cantidad_minima} {self.unidad_medida}",
            'stock_maximo': f"{self.cantidad_maxima} {self.unidad_medida}",
            'proveedor': self.proveedor or 'No especificado',
            'estado_stock': status['status'],
            'color_estado': status['color'],
            'mensaje_estado': status['message'],
            'fecha_creacion': format_date(self.fecha_creacion) if self.fecha_creacion else 'N/A',
            'fecha_actualizacion': format_date(self.fecha_actualizacion) if self.fecha_actualizacion else 'N/A',
            'activo': 'Sí' if self.activo else 'No'
        }
    
    def __str__(self) -> str:
        """Representación string del insumo"""
        return f"Insumo({self.id}): {self.nombre} - {self.cantidad_actual} {self.unidad_medida}"
    
    def __repr__(self) -> str:
        """Representación detallada del insumo"""
        return (f"Insumo(id={self.id}, nombre='{self.nombre}', "
                f"categoria='{self.categoria}', stock={self.cantidad_actual})")
    
    def __eq__(self, other) -> bool:
        """Comparación por igualdad basada en ID"""
        if not isinstance(other, Insumo):
            return False
        return self.id == other.id if self.id and other.id else False
    
    def __hash__(self) -> int:
        """Hash basado en ID"""
        return hash(self.id) if self.id else hash((self.nombre, self.categoria))


# Funciones auxiliares para trabajar con insumos

def create_insumo_from_form_data(form_data: Dict[str, Any]) -> Insumo:
    """
    Crea un insumo desde datos de formulario (UI).
    
    Args:
        form_data: Datos del formulario
        
    Returns:
        Instancia de Insumo validada
        
    Raises:
        ValidationException: Si los datos son inválidos
    """
    # Validar y limpiar datos
    validated_data = validate_insumo_data(form_data)
    
    # Crear instancia
    insumo = Insumo.from_dict(validated_data)
    
    # Validar modelo completo
    insumo.validate_data()
    
    return insumo


def get_insumos_by_status(insumos: list[Insumo]) -> Dict[str, list[Insumo]]:
    """
    Agrupa insumos por su estado de stock.
    
    Args:
        insumos: Lista de insumos
        
    Returns:
        Diccionario agrupando insumos por estado
    """
    grouped = {
        'CRITICO': [],
        'BAJO': [],
        'NORMAL': [],
        'EXCESO': []
    }
    
    for insumo in insumos:
        status = insumo.get_stock_status()
        status_key = status['status']
        
        if status_key in grouped:
            grouped[status_key].append(insumo)
        else:
            grouped['NORMAL'].append(insumo)
    
    return grouped


def calculate_inventory_value(insumos: list[Insumo]) -> Dict[str, Any]:
    """
    Calcula el valor total del inventario.
    
    Args:
        insumos: Lista de insumos
        
    Returns:
        Diccionario con estadísticas de valor del inventario
    """
    total_value = Decimal('0.00')
    total_items = 0
    categories = {}
    
    for insumo in insumos:
        if insumo.activo:
            # Sin manejo de valores monetarios
            total_items += insumo.cantidad_actual

            # Agrupar por categoría
            cat = insumo.categoria
            if cat not in categories:
                categories[cat] = {'value': Decimal('0.00'), 'items': 0, 'count': 0}
            
            # Mantener 'value' en 0.00 para compatibilidad
            categories[cat]['items'] += insumo.cantidad_actual
            categories[cat]['count'] += 1
    
    return {
        'total_value': total_value,
        'total_items': total_items,
        'total_insumos': len([i for i in insumos if i.activo]),
        'categories': categories,
        'average_value_per_item': total_value / max(total_items, 1),
        'formatted_total_value': format_currency(total_value)
    }