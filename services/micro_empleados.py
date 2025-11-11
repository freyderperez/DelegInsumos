"""
DelegInsumos - Microservicio de Empleados
Maneja toda la lógica de negocio para la gestión de empleados
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date

from database.operations import empleado_repo
from models.empleado import Empleado, create_empleado_from_form_data, group_employees_by_department, get_employee_statistics
from utils.logger import LoggerMixin, log_operation
from utils.validators import validate_empleado_data
from exceptions.custom_exceptions import (
    service_exception_handler,
    BusinessLogicException,
    RecordNotFoundException,
    DuplicateRecordException
)


class MicroEmpleadosService(LoggerMixin):
    """
    Microservicio para gestión completa de empleados
    """
    
    def __init__(self):
        super().__init__()
        self._repository = empleado_repo
        self.logger.info("MicroEmpleadosService inicializado")
    
    @service_exception_handler("MicroEmpleadosService")
    def crear_empleado(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo empleado en el sistema.
        
        Args:
            form_data: Datos del formulario de empleado
            
        Returns:
            Diccionario con información del empleado creado
            
        Raises:
            ValidationException: Si los datos no son válidos
            DuplicateRecordException: Si ya existe un empleado con la misma cédula
        """
        self.logger.info(f"Creando nuevo empleado: {form_data.get('nombre_completo', 'N/A')}")
        
        # Crear y validar modelo
        empleado = create_empleado_from_form_data(form_data)
        
        # Verificar duplicados por cédula
        existing = self._repository.get_by_cedula(empleado.cedula)
        if existing:
            raise DuplicateRecordException("empleado", "cédula", empleado.cedula)
        
        # Crear en base de datos
        empleado_id = self._repository.create(empleado.to_dict(include_audit=False))
        empleado.id = empleado_id
        
        log_operation("EMPLEADO_CREADO", 
                     f"ID: {empleado_id}, Nombre: {empleado.nombre_completo}, "
                     f"Cédula: {empleado.cedula}")
        self.logger.info(f"Empleado creado exitosamente con ID: {empleado_id}")
        
        return {
            'success': True,
            'empleado_id': empleado_id,
            'empleado': empleado.to_dict(),
            'message': f"Empleado '{empleado.nombre_completo}' creado exitosamente"
        }
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_empleado(self, empleado_id: int, include_stats: bool = True) -> Dict[str, Any]:
        """
        Obtiene un empleado específico por su ID.
        
        Args:
            empleado_id: ID del empleado
            include_stats: Si incluir estadísticas del empleado
            
        Returns:
            Diccionario con información del empleado
            
        Raises:
            RecordNotFoundException: Si el empleado no existe
        """
        self.logger.debug(f"Obteniendo empleado ID: {empleado_id}")
        
        # Obtener de base de datos
        empleado_data = self._repository.get_by_id(empleado_id)
        if not empleado_data:
            raise RecordNotFoundException("empleado", str(empleado_id))
        
        # Crear modelo
        empleado = Empleado.from_dict(empleado_data)
        result = empleado.to_dict()
        
        if include_stats:
            result.update({
                'display_info': empleado.get_display_info(),
                'employment_duration': empleado.get_employment_duration(),
                'is_new_employee': empleado.is_new_employee(),
                'is_veteran': empleado.is_long_term_employee(),
                'has_contact_info': empleado.has_contact_info(),
                'contact_summary': empleado.get_contact_summary(),
                'can_receive_supplies': empleado.can_receive_supplies()
            })
        
        return result
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_empleado_por_cedula(self, cedula: str, include_stats: bool = True) -> Optional[Dict[str, Any]]:
        """
        Obtiene un empleado por su number de cédula.
        
        Args:
            cedula: Número de cédula
            include_stats: Si incluir estadísticas del empleado
            
        Returns:
            Diccionario con información del empleado o None si no existe
        """
        self.logger.debug(f"Obteniendo empleado por cédula: {cedula}")
        
        # Obtener de base de datos
        empleado_data = self._repository.get_by_cedula(cedula)
        if not empleado_data:
            return None
        
        # Crear modelo
        empleado = Empleado.from_dict(empleado_data)
        result = empleado.to_dict()
        
        if include_stats:
            result.update({
                'display_info': empleado.get_display_info(),
                'employment_duration': empleado.get_employment_duration(),
                'can_receive_supplies': empleado.can_receive_supplies()
            })
        
        return result
    
    @service_exception_handler("MicroEmpleadosService")  
    def listar_empleados(self, active_only: bool = True, include_stats: bool = True) -> Dict[str, Any]:
        """
        Lista todos los empleados del sistema.
        
        Args:
            active_only: Si solo mostrar empleados activos
            include_stats: Si incluir estadísticas generales
            
        Returns:
            Diccionario con lista de empleados y estadísticas
        """
        self.logger.debug(f"Listando empleados (activos: {active_only})")
        
        # Obtener de base de datos
        empleados_data = self._repository.get_all(active_only=active_only)
        
        # Crear modelos
        empleados = [Empleado.from_dict(data) for data in empleados_data]
        
        result = {
            'empleados': [empleado.to_dict() for empleado in empleados],
            'total': len(empleados)
        }
        
        if include_stats:
            # Estadísticas generales
            stats = get_employee_statistics(empleados)
            
            # Agrupar por departamento
            by_department = group_employees_by_department(empleados)
            
            result.update({
                'statistics': stats,
                'by_department': {dept: len(emps) for dept, emps in by_department.items()},
                'department_names': list(by_department.keys())
            })
        
        log_operation("EMPLEADOS_LISTADOS", f"Total: {len(empleados)}, Activos: {active_only}")
        return result
    
    @service_exception_handler("MicroEmpleadosService")
    def actualizar_empleado(self, empleado_id: int, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un empleado existente.
        
        Args:
            empleado_id: ID del empleado
            form_data: Datos actualizados del formulario
            
        Returns:
            Diccionario con información del empleado actualizado
            
        Raises:
            RecordNotFoundException: Si el empleado no existe
            ValidationException: Si los datos no son válidos
        """
        self.logger.info(f"Actualizando empleado ID: {empleado_id}")
        
        # Verificar que existe
        existing_data = self._repository.get_by_id(empleado_id)
        if not existing_data:
            raise RecordNotFoundException("empleado", str(empleado_id))
        
        # Validar los nuevos datos
        validated_data = validate_empleado_data(form_data)
        
        # Verificar duplicados por cédula (excluyendo el mismo registro)
        if 'cedula' in validated_data:
            existing_same_cedula = self._repository.get_by_cedula(validated_data['cedula'])
            if existing_same_cedula and existing_same_cedula['id'] != empleado_id:
                raise DuplicateRecordException("empleado", "cédula", validated_data['cedula'])
        
        # Actualizar en base de datos
        success = self._repository.update(empleado_id, validated_data)
        
        if not success:
            raise BusinessLogicException("No se pudo actualizar el empleado")
        
        # Obtener datos actualizados
        updated_empleado = self.obtener_empleado(empleado_id)
        
        log_operation("EMPLEADO_ACTUALIZADO", f"ID: {empleado_id}")
        self.logger.info(f"Empleado {empleado_id} actualizado exitosamente")
        
        return {
            'success': True,
            'empleado': updated_empleado,
            'message': f"Empleado actualizado exitosamente"
        }
    
    @service_exception_handler("MicroEmpleadosService")
    def eliminar_empleado(self, empleado_id: int, soft_delete: bool = True) -> Dict[str, Any]:
        """
        Elimina un empleado del sistema.
        
        Args:
            empleado_id: ID del empleado
            soft_delete: Si usar eliminación suave
            
        Returns:
            Diccionario con resultado de la eliminación
            
        Raises:
            RecordNotFoundException: Si el empleado no existe
        """
        self.logger.info(f"Eliminando empleado ID: {empleado_id} (soft: {soft_delete})")
        
        # Verificar que existe
        existing_data = self._repository.get_by_id(empleado_id)
        if not existing_data:
            raise RecordNotFoundException("empleado", str(empleado_id))
        
        empleado_nombre = existing_data.get('nombre_completo', 'N/A')
        
        # Eliminar
        success = self._repository.delete(empleado_id, soft_delete=soft_delete)
        
        if not success:
            raise BusinessLogicException("No se pudo eliminar el empleado")
        
        delete_type = "eliminado" if not soft_delete else "desactivado"
        log_operation("EMPLEADO_ELIMINADO", f"ID: {empleado_id}, Tipo: {delete_type}")
        self.logger.info(f"Empleado {empleado_id} {delete_type} exitosamente")
        
        return {
            'success': True,
            'message': f"Empleado '{empleado_nombre}' {delete_type} exitosamente"
        }
    
    @service_exception_handler("MicroEmpleadosService")
    def buscar_empleados(self, termino: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Busca empleados por término de búsqueda.
        
        Args:
            termino: Término de búsqueda
            active_only: Si solo buscar empleados activos
            
        Returns:
            Lista de empleados que coinciden
        """
        self.logger.debug(f"Buscando empleados: '{termino}' (activos: {active_only})")
        
        # Búsqueda en base de datos
        matching = self._repository.search(termino, active_only=active_only)
        
        # Crear modelos y agregar información adicional
        results = []
        for data in matching:
            empleado = Empleado.from_dict(data)
            empleado_dict = empleado.to_dict()
            empleado_dict['display_info'] = empleado.get_display_info()
            empleado_dict['can_receive_supplies'] = empleado.can_receive_supplies()
            results.append(empleado_dict)
        
        log_operation("EMPLEADOS_BUSCADOS", f"Término: '{termino}', Encontrados: {len(results)}")
        return results
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_por_departamento(self, departamento: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene empleados de un departamento específico.
        
        Args:
            departamento: Departamento a filtrar
            active_only: Si solo empleados activos
            
        Returns:
            Lista de empleados del departamento
        """
        self.logger.debug(f"Obteniendo empleados de departamento: {departamento}")
        
        empleados_data = self._repository.get_by_departamento(departamento, active_only=active_only)
        
        results = []
        for data in empleados_data:
            empleado = Empleado.from_dict(data)
            empleado_dict = empleado.to_dict()
            empleado_dict['display_info'] = empleado.get_display_info()
            results.append(empleado_dict)
        
        return results
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_departamentos(self) -> List[str]:
        """
        Obtiene todos los departamentos disponibles.
        
        Returns:
            Lista de departamentos
        """
        return self._repository.get_departments()
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_estadisticas_empleados(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas de los empleados.
        
        Returns:
            Diccionario con estadísticas completas
        """
        self.logger.debug("Obteniendo estadísticas de empleados")
        
        # Obtener todos los empleados
        empleados_data = self._repository.get_all(active_only=False)  # Incluir inactivos para stats completas
        empleados = [Empleado.from_dict(data) for data in empleados_data]
        
        # Calcular estadísticas básicas
        basic_stats = get_employee_statistics(empleados)
        
        # Estadísticas adicionales
        active_employees = [e for e in empleados if e.activo]
        
        # Tiempo de servicio
        employment_duration_stats = {
            'less_than_6_months': 0,
            '6_months_to_1_year': 0,
            '1_to_5_years': 0,
            'more_than_5_years': 0,
            'no_date': 0
        }
        
        for empleado in active_employees:
            duration = empleado.get_employment_duration()
            if not duration:
                employment_duration_stats['no_date'] += 1
            else:
                total_months = duration['años'] * 12 + duration['meses']
                if total_months < 6:
                    employment_duration_stats['less_than_6_months'] += 1
                elif total_months < 12:
                    employment_duration_stats['6_months_to_1_year'] += 1
                elif duration['años'] < 5:
                    employment_duration_stats['1_to_5_years'] += 1
                else:
                    employment_duration_stats['more_than_5_years'] += 1
        
        # Combinar todas las estadísticas
        complete_stats = {
            **basic_stats,
            'employment_duration': employment_duration_stats,
            'last_updated': datetime.now().isoformat()
        }
        
        log_operation("ESTADISTICAS_EMPLEADOS_OBTENIDAS", f"Total empleados: {len(empleados)}")
        return complete_stats
    
    @service_exception_handler("MicroEmpleadosService")
    def validar_empleado_para_entrega(self, empleado_id: int) -> Dict[str, Any]:
        """
        Valida si un empleado puede recibir insumos.
        
        Args:
            empleado_id: ID del empleado
            
        Returns:
            Diccionario con resultado de la validación
            
        Raises:
            RecordNotFoundException: Si el empleado no existe
        """
        # Obtener empleado
        empleado_data = self._repository.get_by_id(empleado_id)
        if not empleado_data:
            raise RecordNotFoundException("empleado", str(empleado_id))
        
        empleado = Empleado.from_dict(empleado_data)
        
        can_receive = empleado.can_receive_supplies()
        
        # Motivos por los que no puede recibir
        issues = []
        if not empleado.activo:
            issues.append("Empleado inactivo")
        if not empleado.nombre_completo.strip():
            issues.append("Nombre incompleto")
        
        return {
            'can_receive': can_receive,
            'empleado_id': empleado_id,
            'empleado_nombre': empleado.nombre_completo,
            'empleado_cedula': empleado.cedula,
            'empleado_departamento': empleado.departamento,
            'empleado_cargo': empleado.cargo,
            'is_active': empleado.activo,
            'issues': issues,
            'message': 'Empleado válido para entregas' if can_receive else f"No puede recibir entregas: {', '.join(issues)}"
        }
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_empleados_activos_para_entrega(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de empleados que pueden recibir insumos.
        
        Returns:
            Lista de empleados válidos para entregas
        """
        self.logger.debug("Obteniendo empleados válidos para entregas")
        
        # Obtener empleados activos
        empleados_data = self._repository.get_all(active_only=True)
        
        valid_employees = []
        for data in empleados_data:
            empleado = Empleado.from_dict(data)
            if empleado.can_receive_supplies():
                employee_info = {
                    'id': empleado.id,
                    'nombre_completo': empleado.nombre_completo,
                    'cedula': empleado.cedula,
                    'cargo': empleado.cargo,
                    'departamento': empleado.departamento,
                    'display_name': f"{empleado.nombre_completo} ({empleado.cedula})",
                    'display_info': empleado.get_display_info()
                }
                valid_employees.append(employee_info)
        
        # Ordenar por nombre
        valid_employees.sort(key=lambda x: x['nombre_completo'])
        
        log_operation("EMPLEADOS_VALIDOS_ENTREGAS", f"Total válidos: {len(valid_employees)}")
        return valid_employees
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_empleados_nuevos(self, threshold_months: int = 6) -> List[Dict[str, Any]]:
        """
        Obtiene lista de empleados nuevos.
        
        Args:
            threshold_months: Meses para considerar como nuevo empleado
            
        Returns:
            Lista de empleados nuevos
        """
        empleados_data = self._repository.get_all(active_only=True)
        empleados_nuevos = []
        
        for data in empleados_data:
            empleado = Empleado.from_dict(data)
            if empleado.is_new_employee(threshold_months):
                employee_info = empleado.to_dict()
                employee_info['display_info'] = empleado.get_display_info()
                employee_info['employment_duration'] = empleado.get_employment_duration()
                empleados_nuevos.append(employee_info)
        
        return empleados_nuevos
    
    @service_exception_handler("MicroEmpleadosService")
    def obtener_empleados_veteranos(self, threshold_years: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene lista de empleados veteranos.
        
        Args:
            threshold_years: Años para considerar como empleado veterano
            
        Returns:
            Lista de empleados veteranos
        """
        empleados_data = self._repository.get_all(active_only=True)
        empleados_veteranos = []
        
        for data in empleados_data:
            empleado = Empleado.from_dict(data)
            if empleado.is_long_term_employee(threshold_years):
                employee_info = empleado.to_dict()
                employee_info['display_info'] = empleado.get_display_info()
                employee_info['employment_duration'] = empleado.get_employment_duration()
                empleados_veteranos.append(employee_info)
        
        return empleados_veteranos


# Instancia global del microservicio
micro_empleados = MicroEmpleadosService()

# Funciones de conveniencia para uso directo
def crear_empleado(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Función de conveniencia para crear empleado"""
    return micro_empleados.crear_empleado(form_data)

def obtener_empleado(empleado_id: int) -> Dict[str, Any]:
    """Función de conveniencia para obtener empleado"""
    return micro_empleados.obtener_empleado(empleado_id)

def obtener_empleado_por_cedula(cedula: str) -> Optional[Dict[str, Any]]:
    """Función de conveniencia para obtener empleado por cédula"""
    return micro_empleados.obtener_empleado_por_cedula(cedula)

def listar_empleados(active_only: bool = True) -> Dict[str, Any]:
    """Función de conveniencia para listar empleados"""
    return micro_empleados.listar_empleados(active_only)

def obtener_empleados_activos_para_entrega() -> List[Dict[str, Any]]:
    """Función de conveniencia para obtener empleados válidos para entregas"""
    return micro_empleados.obtener_empleados_activos_para_entrega()