"""
DelegInsumos - Modelo de Datos: Entrega
Define la estructura y comportamiento de la entidad Entrega
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

from utils.validators import validate_entrega_data
from utils.helpers import format_date
from utils import generar_id
from exceptions.custom_exceptions import ValidationException


@dataclass
class Entrega:
    """
    Modelo de datos para una entrega de insumos
    """
    
    # Campos principales
    id: Optional[int] = None
    codigo: Optional[str] = None
    empleado_id: int = 0
    insumo_id: int = 0
    cantidad: int = 0
    observaciones: str = ""
    entregado_por: str = ""
    fecha_entrega: Optional[datetime] = None
    
    # Campos de información relacionada (desde vista vw_entregas_completas)
    empleado_nombre: str = ""
    empleado_cargo: str = ""
    empleado_departamento: str = ""
    empleado_cedula: str = ""
    insumo_nombre: str = ""
    insumo_categoria: str = ""
    insumo_unidad: str = ""
    insumo_precio: Optional[Decimal] = None
    valor_total: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validaciones y conversiones post-inicialización"""
        # Generar código público si no se proporciona
        if not self.codigo:
            self.codigo = generar_id("ENT")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entrega':
        """
        Crea una instancia de Entrega desde un diccionario.
        
        Args:
            data: Diccionario con datos de la entrega
            
        Returns:
            Instancia de Entrega
        """
        # Convertir fecha si está como string
        fecha_entrega = data.get('fecha_entrega')
        if isinstance(fecha_entrega, str):
            fecha_entrega = datetime.fromisoformat(fecha_entrega.replace('Z', '+00:00'))
        
        return cls(
            id=data.get('id'),
            codigo=data.get('codigo'),
            empleado_id=data.get('empleado_id', 0),
            insumo_id=data.get('insumo_id', 0),
            cantidad=data.get('cantidad', 0),
            observaciones=data.get('observaciones', ''),
            entregado_por=data.get('entregado_por', ''),
            fecha_entrega=fecha_entrega,
            
            # Campos de información relacionada
            empleado_nombre=data.get('empleado_nombre', ''),
            empleado_cargo=data.get('empleado_cargo', ''),
            empleado_departamento=data.get('empleado_departamento', ''),
            empleado_cedula=data.get('empleado_cedula', ''),
            insumo_nombre=data.get('insumo_nombre', ''),
            insumo_categoria=data.get('insumo_categoria', ''),
            insumo_unidad=data.get('insumo_unidad', ''),
            insumo_precio=Decimal(str(data.get('insumo_precio', '0.00'))) if data.get('insumo_precio') else None,
            valor_total=Decimal(str(data.get('valor_total', '0.00'))) if data.get('valor_total') else None
        )
    
    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """
        Convierte la instancia a diccionario.
        
        Args:
            include_relations: Si incluir información relacionada
            
        Returns:
            Diccionario con datos de la entrega
        """
        result = {
            'id': self.id,
            'codigo': self.codigo,
            'empleado_id': self.empleado_id,
            'insumo_id': self.insumo_id,
            'cantidad': self.cantidad,
            'observaciones': self.observaciones,
            'entregado_por': self.entregado_por,
            'fecha_entrega': self.fecha_entrega.isoformat() if self.fecha_entrega else None
        }
        
        if include_relations:
            result.update({
                'empleado_nombre': self.empleado_nombre,
                'empleado_cargo': self.empleado_cargo,
                'empleado_departamento': self.empleado_departamento,
                'empleado_cedula': self.empleado_cedula,
                'insumo_nombre': self.insumo_nombre,
                'insumo_categoria': self.insumo_categoria,
                'insumo_unidad': self.insumo_unidad,
                'insumo_precio': float(self.insumo_precio) if self.insumo_precio else None,
                'valor_total': float(self.valor_total) if self.valor_total else None
            })
        
        return result
    
    def validate_data(self) -> None:
        """
        Valida los datos de la entrega.
        
        Raises:
            ValidationException: Si los datos no son válidos
        """
        data_dict = {
            'empleado_id': self.empleado_id,
            'insumo_id': self.insumo_id,
            'cantidad': self.cantidad,
            'observaciones': self.observaciones,
            'entregado_por': self.entregado_por
        }
        
        validate_entrega_data(data_dict)
        
        # Validaciones adicionales específicas del modelo
        if self.fecha_entrega and self.fecha_entrega > datetime.now():
            raise ValidationException('fecha_entrega', 'No puede ser una fecha futura')
    
    def is_recent(self, days_threshold: int = 7) -> bool:
        """
        Determina si la entrega es reciente.
        
        Args:
            days_threshold: Días para considerar como reciente
            
        Returns:
            True si la entrega es reciente
        """
        if not self.fecha_entrega:
            return False
        
        days_passed = (datetime.now() - self.fecha_entrega).days
        return days_passed <= days_threshold
    
    def is_high_value(self, threshold: float = 50000.0) -> bool:
        """
        Determina si la entrega es de alto valor.
        
        Args:
            threshold: Umbral de valor en pesos
            
        Returns:
            True si la entrega supera el umbral de valor
        """
        if not self.valor_total:
            return False
        
        return float(self.valor_total) >= threshold
    
    def is_high_quantity(self, threshold: int = 10) -> bool:
        """
        Determina si la entrega es de alta cantidad.
        
        Args:
            threshold: Umbral de cantidad
            
        Returns:
            True si la cantidad supera el umbral
        """
        return self.cantidad >= threshold
    
    def get_delivery_summary(self) -> str:
        """
        Obtiene un resumen de la entrega.
        
        Returns:
            String con resumen de la entrega
        """
        return (f"{self.cantidad} {self.insumo_unidad} de {self.insumo_nombre} "
                f"entregado a {self.empleado_nombre}")
    
    def get_priority_level(self) -> Dict[str, Any]:
        """
        Determina el nivel de prioridad/importancia de la entrega.
        
        Returns:
            Diccionario con información de prioridad
        """
        priority_score = 0
        factors = []
        
        # Factor: Cantidad alta
        if self.is_high_quantity():
            priority_score += 2
            factors.append("Alta cantidad")
        
        # Factor: Alto valor
        if self.is_high_value():
            priority_score += 3
            factors.append("Alto valor")
        
        # Factor: Entrega reciente
        if self.is_recent(1):  # Último día
            priority_score += 1
            factors.append("Muy reciente")
        elif self.is_recent(3):  # Últimos 3 días
            priority_score += 0.5
            factors.append("Reciente")
        
        # Factor: Observaciones especiales
        if self.observaciones and len(self.observaciones.strip()) > 50:
            priority_score += 1
            factors.append("Observaciones detalladas")
        
        # Determinar nivel
        if priority_score >= 5:
            level = "ALTA"
            color = "#F44336"  # Rojo
        elif priority_score >= 3:
            level = "MEDIA"
            color = "#FF9800"  # Naranja
        else:
            level = "BAJA" 
            color = "#4CAF50"  # Verde
        
        return {
            'level': level,
            'score': priority_score,
            'color': color,
            'factors': factors
        }
    
    def matches_search_term(self, term: str) -> bool:
        """
        Verifica si la entrega coincide con un término de búsqueda.
        
        Args:
            term: Término de búsqueda
            
        Returns:
            True si coincide con la búsqueda
        """
        search_term = term.lower().strip()
        if not search_term:
            return True
        
        # Buscar en los campos principales
        searchable_fields = [
            self.empleado_nombre,
            self.empleado_cedula,
            self.empleado_departamento,
            self.insumo_nombre,
            self.insumo_categoria,
            self.observaciones,
            self.entregado_por
        ]
        
        for field in searchable_fields:
            if field and search_term in field.lower():
                return True
        
        return False
    
    def get_display_info(self) -> Dict[str, str]:
        """
        Obtiene información formateada para mostrar en la UI.
        
        Returns:
            Diccionario con información formateada
        """
        priority = self.get_priority_level()
        
        return {
            'id': str(self.id) if self.id is not None else 'N/A',
            'codigo': self.codigo or 'N/A',
            'fecha_entrega': format_date(self.fecha_entrega, "datetime") if self.fecha_entrega else 'N/A',
            'fecha_corta': format_date(self.fecha_entrega, "short") if self.fecha_entrega else 'N/A',
            'empleado_completo': f"{self.empleado_nombre} ({self.empleado_cedula})",
            'empleado_nombre': self.empleado_nombre,
            'empleado_cargo': self.empleado_cargo or 'No especificado',
            'empleado_departamento': self.empleado_departamento or 'No especificado',
            'empleado_cedula': self.empleado_cedula,
            'insumo_completo': f"{self.insumo_nombre} ({self.insumo_categoria})",
            'insumo_nombre': self.insumo_nombre,
            'insumo_categoria': self.insumo_categoria,
            'cantidad_completa': f"{self.cantidad} {self.insumo_unidad}",
            'cantidad': str(self.cantidad),
            'unidad': self.insumo_unidad,
            'precio_unitario': 'N/A',
            'valor_total': 'N/A',
            'observaciones': self.observaciones or 'Sin observaciones',
            'entregado_por': self.entregado_por or 'No especificado',
            'es_reciente': 'Sí' if self.is_recent() else 'No',
            'es_alto_valor': 'Sí' if self.is_high_value() else 'No',
            'es_alta_cantidad': 'Sí' if self.is_high_quantity() else 'No',
            'prioridad': priority['level'],
            'color_prioridad': priority['color'],
            'factores_prioridad': ', '.join(priority['factors']),
            'resumen': self.get_delivery_summary()
        }
    
    def get_audit_info(self) -> Dict[str, str]:
        """
        Obtiene información de auditoría formateada.
        
        Returns:
            Diccionario con información de auditoría
        """
        return {
            'quien': self.entregado_por or 'Sistema',
            'cuando': format_date(self.fecha_entrega, "datetime") if self.fecha_entrega else 'N/A',
            'que': f"{self.cantidad} {self.insumo_unidad} de {self.insumo_nombre}",
            'a_quien': f"{self.empleado_nombre} ({self.empleado_cedula})",
            'valor': 'N/A',
            'notas': self.observaciones or 'Sin observaciones'
        }
    
    def __str__(self) -> str:
        """Representación string de la entrega"""
        return (f"Entrega({self.id}): {self.cantidad} {self.insumo_unidad} "
                f"de {self.insumo_nombre} → {self.empleado_nombre}")
    
    def __repr__(self) -> str:
        """Representación detallada de la entrega"""
        return (f"Entrega(id={self.id}, empleado_id={self.empleado_id}, "
                f"insumo_id={self.insumo_id}, cantidad={self.cantidad})")
    
    def __eq__(self, other) -> bool:
        """Comparación por igualdad basada en ID"""
        if not isinstance(other, Entrega):
            return False
        return self.id == other.id if self.id and other.id else False
    
    def __hash__(self) -> int:
        """Hash basado en ID"""
        if self.id:
            return hash(self.id)
        return hash((self.empleado_id, self.insumo_id, self.cantidad, 
                   self.fecha_entrega.isoformat() if self.fecha_entrega else ""))


# Funciones auxiliares para trabajar con entregas

def create_entrega_from_form_data(form_data: Dict[str, Any]) -> Entrega:
    """
    Crea una entrega desde datos de formulario (UI).
    
    Args:
        form_data: Datos del formulario
        
    Returns:
        Instancia de Entrega validada
        
    Raises:
        ValidationException: Si los datos son inválidos
    """
    # Validar y limpiar datos
    validated_data = validate_entrega_data(form_data)
    
    # Agregar fecha actual si no se especifica
    if 'fecha_entrega' not in validated_data:
        validated_data['fecha_entrega'] = datetime.now()
    
    # Crear instancia
    entrega = Entrega.from_dict(validated_data)
    
    # Validar modelo completo
    entrega.validate_data()
    
    return entrega


def group_entregas_by_date(entregas: List[Entrega]) -> Dict[str, List[Entrega]]:
    """
    Agrupa entregas por fecha.
    
    Args:
        entregas: Lista de entregas
        
    Returns:
        Diccionario agrupando entregas por fecha
    """
    grouped = {}
    
    for entrega in entregas:
        if entrega.fecha_entrega:
            date_key = entrega.fecha_entrega.strftime('%Y-%m-%d')
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(entrega)
    
    # Ordenar cada grupo por hora
    for date_key in grouped:
        grouped[date_key].sort(key=lambda e: e.fecha_entrega or datetime.min)
    
    return grouped


def group_entregas_by_employee(entregas: List[Entrega]) -> Dict[str, List[Entrega]]:
    """
    Agrupa entregas por empleado.
    
    Args:
        entregas: Lista de entregas
        
    Returns:
        Diccionario agrupando entregas por empleado
    """
    grouped = {}
    
    for entrega in entregas:
        employee_key = f"{entrega.empleado_nombre} ({entrega.empleado_cedula})"
        if employee_key not in grouped:
            grouped[employee_key] = []
        grouped[employee_key].append(entrega)
    
    # Ordenar cada grupo por fecha descendente
    for employee_key in grouped:
        grouped[employee_key].sort(key=lambda e: e.fecha_entrega or datetime.min, reverse=True)
    
    return grouped


def group_entregas_by_insumo(entregas: List[Entrega]) -> Dict[str, List[Entrega]]:
    """
    Agrupa entregas por insumo.
    
    Args:
        entregas: Lista de entregas
        
    Returns:
        Diccionario agrupando entregas por insumo
    """
    grouped = {}
    
    for entrega in entregas:
        insumo_key = f"{entrega.insumo_nombre} ({entrega.insumo_categoria})"
        if insumo_key not in grouped:
            grouped[insumo_key] = []
        grouped[insumo_key].append(entrega)
    
    # Ordenar cada grupo por fecha descendente
    for insumo_key in grouped:
        grouped[insumo_key].sort(key=lambda e: e.fecha_entrega or datetime.min, reverse=True)
    
    return grouped


def calculate_delivery_statistics(entregas: List[Entrega]) -> Dict[str, Any]:
    """
    Calcula estadísticas de las entregas.
    
    Args:
        entregas: Lista de entregas
        
    Returns:
        Diccionario con estadísticas
    """
    if not entregas:
        return {
            'total_entregas': 0,
            'total_cantidad': 0,
            'valor_total': Decimal('0.00'),
            'entregas_recientes': 0,
            'entregas_alto_valor': 0,
            'entregas_alta_cantidad': 0,
            'empleados_unicos': 0,
            'insumos_unicos': 0,
            'promedio_cantidad': 0,
            'promedio_valor': Decimal('0.00')
        }
    
    total_entregas = len(entregas)
    total_cantidad = sum(e.cantidad for e in entregas)
    valor_total = Decimal('0.00')
    
    entregas_recientes = sum(1 for e in entregas if e.is_recent())
    entregas_alto_valor = sum(1 for e in entregas if e.is_high_value())
    entregas_alta_cantidad = sum(1 for e in entregas if e.is_high_quantity())
    
    empleados_unicos = len(set(e.empleado_id for e in entregas if e.empleado_id))
    insumos_unicos = len(set(e.insumo_id for e in entregas if e.insumo_id))
    
    promedio_cantidad = total_cantidad / total_entregas
    promedio_valor = Decimal('0.00')
    
    # Top 5 empleados con más entregas
    employee_counts = {}
    for entrega in entregas:
        key = f"{entrega.empleado_nombre} ({entrega.empleado_cedula})"
        employee_counts[key] = employee_counts.get(key, 0) + 1
    
    top_employees = sorted(employee_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top 5 insumos más entregados
    insumo_counts = {}
    for entrega in entregas:
        key = entrega.insumo_nombre
        insumo_counts[key] = insumo_counts.get(key, 0) + entrega.cantidad
    
    top_insumos = sorted(insumo_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'total_entregas': total_entregas,
        'total_cantidad': total_cantidad,
        'valor_total': valor_total,
        'valor_total_formatted': 'N/A',
        'entregas_recientes': entregas_recientes,
        'entregas_alto_valor': entregas_alto_valor,
        'entregas_alta_cantidad': entregas_alta_cantidad,
        'empleados_unicos': empleados_unicos,
        'insumos_unicos': insumos_unicos,
        'promedio_cantidad': round(promedio_cantidad, 2),
        'promedio_valor': promedio_valor,
        'promedio_valor_formatted': 'N/A',
        'top_empleados': top_employees,
        'top_insumos': top_insumos
    }


def get_recent_deliveries(entregas: List[Entrega], days: int = 7) -> List[Entrega]:
    """
    Obtiene entregas recientes.
    
    Args:
        entregas: Lista de entregas
        days: Número de días para considerar como reciente
        
    Returns:
        Lista de entregas recientes
    """
    return [entrega for entrega in entregas if entrega.is_recent(days)]


def get_high_value_deliveries(entregas: List[Entrega], threshold: float = 50000.0) -> List[Entrega]:
    """
    Obtiene entregas de alto valor.
    
    Args:
        entregas: Lista de entregas
        threshold: Umbral de valor
        
    Returns:
        Lista de entregas de alto valor
    """
    return [entrega for entrega in entregas if entrega.is_high_value(threshold)]