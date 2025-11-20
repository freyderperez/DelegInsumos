"""
DelegInsumos - Modelo de Datos: Empleado
Define la estructura y comportamiento de la entidad Empleado
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, date

from utils.validators import validate_empleado_data, DataValidator
from utils.helpers import format_date, parse_date
from utils import generar_id
from exceptions.custom_exceptions import ValidationException


@dataclass
class Empleado:
    """
    Modelo de datos para un empleado del sistema
    """
    
    # Campos principales
    id: Optional[str] = None             # ID interno (numérico/autoincremental)
    codigo: Optional[str] = None         # Código público legible (EMP-REG-XXXX)
    nombre_completo: str = ""
    cargo: str = ""
    departamento: str = ""
    cedula: str = ""
    email: str = ""
    telefono: str = ""
    
    # Campos de auditoría
    fecha_creacion: Optional[datetime] = None
    activo: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Empleado':
        """
        Crea una instancia de Empleado desde un diccionario.
        
        Args:
            data: Diccionario con datos del empleado
            
        Returns:
            Instancia de Empleado
        """
        # Convertir fechas si están como string
        fecha_creacion = data.get('fecha_creacion')
        if isinstance(fecha_creacion, str):
            fecha_creacion = datetime.fromisoformat(fecha_creacion.replace('Z', '+00:00'))
        
        
        return cls(
            id=data.get('id'),
            codigo=data.get('codigo'),
            nombre_completo=data.get('nombre_completo', ''),
            cargo=data.get('cargo', ''),
            departamento=data.get('departamento', ''),
            cedula=data.get('cedula', ''),
            email=data.get('email', ''),
            telefono=data.get('telefono', ''),
            fecha_creacion=fecha_creacion,
            activo=bool(data.get('activo', True))
        )
    
    def to_dict(self, include_audit: bool = True) -> Dict[str, Any]:
        """
        Convierte la instancia a diccionario.
        
        Args:
            include_audit: Si incluir campos de auditoría
            
        Returns:
            Diccionario con datos del empleado
        """
        result = {
            'nombre_completo': self.nombre_completo,
            'cargo': self.cargo,
            'departamento': self.departamento,
            'cedula': self.cedula,
            'email': self.email,
            'telefono': self.telefono
        }
        
        if include_audit:
            result.update({
                'id': self.id,
                'codigo': self.codigo,
                'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
                'activo': self.activo
            })
        
        return result
    
    def validate_data(self) -> None:
        """
        Valida los datos del empleado.
        
        Raises:
            ValidationException: Si los datos no son válidos
        """
        data_dict = self.to_dict(include_audit=False)
        validate_empleado_data(data_dict)
        
        # Validaciones adicionales específicas del modelo
        # Sin validaciones de fecha_ingreso ya que se eliminó el campo
    
    def get_full_name(self) -> str:
        """
        Obtiene el nombre completo del empleado.
        
        Returns:
            Nombre completo
        """
        return self.nombre_completo.strip()
    
    def get_first_name(self) -> str:
        """
        Obtiene el primer nombre del empleado.
        
        Returns:
            Primer nombre
        """
        names = self.nombre_completo.strip().split()
        return names[0] if names else ""
    
    def get_last_name(self) -> str:
        """
        Obtiene los apellidos del empleado.
        
        Returns:
            Apellidos
        """
        names = self.nombre_completo.strip().split()
        return " ".join(names[1:]) if len(names) > 1 else ""
    
    def get_initials(self) -> str:
        """
        Obtiene las iniciales del empleado.
        
        Returns:
            Iniciales (ej: "JP" para Juan Pérez)
        """
        names = self.nombre_completo.strip().split()
        return "".join([name[0].upper() for name in names[:2] if name])
    
    def has_contact_info(self) -> bool:
        """
        Verifica si el empleado tiene información de contacto.
        
        Returns:
            True si tiene email o teléfono
        """
        return bool(self.email.strip() or self.telefono.strip())
    
    def get_employment_duration(self) -> Optional[Dict[str, int]]:
        """
        Calcula el tiempo desde que el empleado fue registrado en el sistema.
 
        Se utiliza el campo fecha_creacion como referencia, ya que no existe
        fecha de ingreso laboral explícita.
 
        Returns:
            Diccionario con años, meses y días de antigüedad en el sistema,
            o None si no hay fecha_creacion disponible.
        """
        if not self.fecha_creacion:
            return None
 
        start_date = self.fecha_creacion.date()
        today = date.today()
 
        # Proteger contra fechas futuras por errores de datos
        if start_date > today:
            start_date = today
 
        delta_days = (today - start_date).days
        years = delta_days // 365
        remaining_days = delta_days % 365
        months = remaining_days // 30
        days = remaining_days % 30
 
        return {
            'años': years,
            'meses': months,
            'días': days
        }
     
    def is_new_employee(self, threshold_months: int = 6) -> bool:
        """
        Determina si es un empleado relativamente nuevo en el sistema.
        
        Args:
            threshold_months: Meses desde su registro para considerarlo nuevo
            
        Returns:
            True si el tiempo desde su registro es menor al umbral
        """
        duration = self.get_employment_duration()
        if not duration:
            # Sin fecha de creación no se puede afirmar que sea "nuevo"
            return False
        
        total_months = duration['años'] * 12 + duration['meses']
        return total_months < threshold_months
     
    def is_long_term_employee(self, threshold_years: int = 5) -> bool:
        """
        Determina si es un empleado de larga trayectoria en el sistema.
        
        Args:
            threshold_years: Años desde su registro para considerarlo de larga trayectoria
            
        Returns:
            True si el tiempo desde su registro es mayor o igual al umbral
        """
        duration = self.get_employment_duration()
        if not duration:
            return False
        
        return duration['años'] >= threshold_years
    
    def get_display_info(self) -> Dict[str, str]:
        """
        Obtiene información formateada para mostrar en la UI.
        
        Returns:
            Diccionario con información formateada
        """
        duration = self.get_employment_duration()
        duration_text = "No disponible"
        
        if duration:
            if duration['años'] > 0:
                duration_text = f"{duration['años']} año(s)"
                if duration['meses'] > 0:
                    duration_text += f", {duration['meses']} mes(es)"
            elif duration['meses'] > 0:
                duration_text = f"{duration['meses']} mes(es)"
            else:
                duration_text = f"{duration['días']} día(s)"
        elif self.fecha_creacion:
            # Hay fecha de creación pero no se pudo calcular duración (caso muy raro)
            duration_text = "No disponible (error de cálculo)"
        else:
            duration_text = "No disponible (sin fecha de registro)"
        
        return {
            'id': str(self.id) if self.id else 'N/A',
            'nombre_completo': self.nombre_completo,
            'primer_nombre': self.get_first_name(),
            'apellidos': self.get_last_name(),
            'iniciales': self.get_initials(),
            'cargo': self.cargo or 'No especificado',
            'departamento': self.departamento or 'No especificado',
            'cedula': self.cedula,
            'email': self.email or 'No especificado',
            'telefono': self.telefono or 'No especificado',
            'fecha_ingreso': format_date(self.fecha_creacion) if self.fecha_creacion else 'No especificada',
            'tiempo_servicio': duration_text,
            'empleado_nuevo': 'Sí' if self.is_new_employee() else 'No',
            'empleado_veterano': 'Sí' if self.is_long_term_employee() else 'No',
            'tiene_contacto': 'Sí' if self.has_contact_info() else 'No',
            'fecha_creacion': format_date(self.fecha_creacion) if self.fecha_creacion else 'N/A',
            'activo': 'Sí' if self.activo else 'No'
        }
    
    def get_contact_summary(self) -> str:
        """
        Obtiene un resumen de información de contacto.
        
        Returns:
            String con información de contacto
        """
        contact_parts = []
        
        if self.email:
            contact_parts.append(f"📧 {self.email}")
        
        if self.telefono:
            contact_parts.append(f"📞 {self.telefono}")
        
        return " | ".join(contact_parts) if contact_parts else "Sin información de contacto"
    
    def matches_search_term(self, term: str) -> bool:
        """
        Verifica si el empleado coincide con un término de búsqueda.
        
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
            self.nombre_completo,
            self.cedula,
            self.cargo,
            self.departamento,
            self.email,
            self.telefono
        ]
        
        for field in searchable_fields:
            if field and search_term in field.lower():
                return True
        
        return False
    
    def can_receive_supplies(self) -> bool:
        """
        Determina si el empleado puede recibir insumos.
        
        Returns:
            True si está activo y puede recibir insumos
        """
        return self.activo and bool(self.nombre_completo.strip())
    
    def __str__(self) -> str:
        """Representación string del empleado"""
        return f"Empleado({self.id}): {self.nombre_completo} - {self.cedula}"
    
    def __repr__(self) -> str:
        """Representación detallada del empleado"""
        return (f"Empleado(id={self.id}, nombre='{self.nombre_completo}', "
                f"cedula='{self.cedula}', departamento='{self.departamento}')")
    
    def __eq__(self, other) -> bool:
        """Comparación por igualdad basada en ID o cédula"""
        if not isinstance(other, Empleado):
            return False
        
        # Comparar por ID si ambos lo tienen
        if self.id and other.id:
            return self.id == other.id
        
        # Comparar por cédula si no hay ID
        return self.cedula == other.cedula if self.cedula and other.cedula else False
    
    def __hash__(self) -> int:
        """Hash basado en ID o cédula"""
        if self.id:
            return hash(self.id)
        return hash(self.cedula) if self.cedula else hash(self.nombre_completo)


# Funciones auxiliares para trabajar con empleados

def create_empleado_from_form_data(form_data: Dict[str, Any]) -> Empleado:
    """
    Crea un empleado desde datos de formulario (UI).
    
    Args:
        form_data: Datos del formulario
        
    Returns:
        Instancia de Empleado validada
        
    Raises:
        ValidationException: Si los datos son inválidos
    """
    # Validar y limpiar datos
    validated_data = validate_empleado_data(form_data)
    
    # Crear instancia
    empleado = Empleado.from_dict(validated_data)
    
    # Validar modelo completo
    empleado.validate_data()
    
    return empleado


def group_employees_by_department(empleados: List[Empleado]) -> Dict[str, List[Empleado]]:
    """
    Agrupa empleados por departamento.
    
    Args:
        empleados: Lista de empleados
        
    Returns:
        Diccionario agrupando empleados por departamento
    """
    grouped = {}
    
    for empleado in empleados:
        if empleado.activo:
            dept = empleado.departamento or 'Sin Departamento'
            if dept not in grouped:
                grouped[dept] = []
            grouped[dept].append(empleado)
    
    # Ordenar cada grupo por nombre
    for dept in grouped:
        grouped[dept].sort(key=lambda e: e.nombre_completo)
    
    return grouped


def get_employee_statistics(empleados: List[Empleado]) -> Dict[str, Any]:
    """
    Calcula estadísticas de los empleados.
    
    Args:
        empleados: Lista de empleados
        
    Returns:
        Diccionario con estadísticas
    """
    active_employees = [e for e in empleados if e.activo]
    total_active = len(active_employees)
    
    # Estadísticas por departamento
    departments = {}
    new_employees = 0
    veteran_employees = 0
    employees_with_contact = 0
    
    for empleado in active_employees:
        # Por departamento
        dept = empleado.departamento or 'Sin Departamento'
        if dept not in departments:
            departments[dept] = 0
        departments[dept] += 1
        
        # Empleados nuevos y veteranos
        if empleado.is_new_employee():
            new_employees += 1
        elif empleado.is_long_term_employee():
            veteran_employees += 1
        
        # Con información de contacto
        if empleado.has_contact_info():
            employees_with_contact += 1
    
    return {
        'total_empleados': len(empleados),
        'empleados_activos': total_active,
        'empleados_inactivos': len(empleados) - total_active,
        'empleados_nuevos': new_employees,
        'empleados_veteranos': veteran_employees,
        'con_informacion_contacto': employees_with_contact,
        'sin_informacion_contacto': total_active - employees_with_contact,
        'departamentos': departments,
        'total_departamentos': len(departments),
        'promedio_empleados_por_departamento': total_active / max(len(departments), 1)
    }


def find_employees_by_criteria(empleados: List[Empleado], **criteria) -> List[Empleado]:
    """
    Encuentra empleados que cumplen ciertos criterios.
    
    Args:
        empleados: Lista de empleados
        **criteria: Criterios de búsqueda
        
    Returns:
        Lista de empleados filtrados
    """
    filtered = []
    
    for empleado in empleados:
        match = True
        
        if 'activo' in criteria and empleado.activo != criteria['activo']:
            match = False
        
        if 'departamento' in criteria and empleado.departamento != criteria['departamento']:
            match = False
        
        if 'nuevo' in criteria and empleado.is_new_employee() != criteria['nuevo']:
            match = False
        
        if 'veterano' in criteria and empleado.is_long_term_employee() != criteria['veterano']:
            match = False
        
        if 'con_contacto' in criteria and empleado.has_contact_info() != criteria['con_contacto']:
            match = False
        
        if 'search_term' in criteria and not empleado.matches_search_term(criteria['search_term']):
            match = False
        
        if match:
            filtered.append(empleado)
    
    return filtered