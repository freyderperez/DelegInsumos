"""
DelegInsumos - Microservicio de Alertas
Sistema inteligente de notificaciones y alertas del sistema
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from enum import Enum

from services.micro_insumos import micro_insumos
from services.micro_empleados import micro_empleados
from services.micro_entregas import micro_entregas
from config.config_manager import config
from utils.logger import LoggerMixin, log_operation
from exceptions.custom_exceptions import service_exception_handler, BusinessLogicException


class AlertType(Enum):
    """Tipos de alertas del sistema"""
    STOCK_CRITICO = "STOCK_CRITICO"
    STOCK_BAJO = "STOCK_BAJO"
    STOCK_EXCESO = "STOCK_EXCESO"
    ENTREGAS_FRECUENTES = "ENTREGAS_FRECUENTES"
    SISTEMA_ERROR = "SISTEMA_ERROR"
    BACKUP_FAILED = "BACKUP_FAILED"
    DATA_INCONSISTENCY = "DATA_INCONSISTENCY"


class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Alert:
    """Clase para representar una alerta del sistema"""
    
    def __init__(self, alert_type: AlertType, severity: AlertSeverity, 
                 title: str, message: str, entity_id: Optional[int] = None, 
                 entity_type: Optional[str] = None, data: Optional[Dict] = None):
        self.id = f"{alert_type.value}_{entity_id or 'SYS'}_{int(datetime.now().timestamp())}"
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.message = message
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.data = data or {}
        self.created_at = datetime.now()
        self.resolved = False
        self.resolved_at = None
        self.resolved_by = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la alerta a diccionario"""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'severity_label': self.get_severity_label(),
            'title': self.title,
            'message': self.message,
            'entity_id': self.entity_id,
            'entity_type': self.entity_type,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'color': self.get_color(),
            'icon': self.get_icon(),
            'action_required': self.requires_action()
        }
    
    def get_color(self) -> str:
        """Obtiene el color asociado con la severidad"""
        color_map = {
            AlertSeverity.LOW: "#4CAF50",      # Verde
            AlertSeverity.MEDIUM: "#FF9800",   # Naranja
            AlertSeverity.HIGH: "#F44336",     # Rojo
            AlertSeverity.CRITICAL: "#9C27B0"  # Púrpura
        }
        return color_map.get(self.severity, "#757575")
    
    def get_icon(self) -> str:
        """Obtiene el ícono asociado con el tipo de alerta"""
        icon_map = {
            AlertType.STOCK_CRITICO: "⚠️",
            AlertType.STOCK_BAJO: "📉",
            AlertType.STOCK_EXCESO: "📈",
            AlertType.ENTREGAS_FRECUENTES: "🔄",
            AlertType.SISTEMA_ERROR: "🔧",
            AlertType.BACKUP_FAILED: "💾",
            AlertType.DATA_INCONSISTENCY: "🔍"
        }
        return icon_map.get(self.alert_type, "📋")

    def get_severity_label(self) -> str:
        """Etiqueta de severidad en español para UI/Reportes"""
        mapping = {
            AlertSeverity.CRITICAL: "Crítica",
            AlertSeverity.HIGH: "Alta",
            AlertSeverity.MEDIUM: "Media",
            AlertSeverity.LOW: "Baja",
        }
        return mapping.get(self.severity, "Desconocida")
    
    def requires_action(self) -> bool:
        """Determina si la alerta requiere acción del usuario"""
        action_required_types = [
            AlertType.STOCK_CRITICO,
            AlertType.SISTEMA_ERROR,
            AlertType.BACKUP_FAILED,
            AlertType.DATA_INCONSISTENCY
        ]
        return self.alert_type in action_required_types and not self.resolved
    
    def resolve(self, resolved_by: Optional[str] = None):
        """Marca la alerta como resuelta"""
        self.resolved = True
        self.resolved_at = datetime.now()
        self.resolved_by = resolved_by or "Sistema"


class MicroAlertasService(LoggerMixin):
    """
    Microservicio para gestión inteligente de alertas del sistema
    """
    
    def __init__(self):
        super().__init__()
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_config = config.get_alerts_config()
        self.logger.info("MicroAlertasService inicializado")
    
    @service_exception_handler("MicroAlertasService")
    def verificar_todas_las_alertas(self) -> Dict[str, Any]:
        """
        Ejecuta verificación completa de todas las alertas del sistema.
        
        Returns:
            Diccionario con resumen de alertas encontradas
        """
        self.logger.info("Iniciando verificación completa de alertas")
        
        alerts_found = {
            'stock_alerts': self._verificar_alertas_stock(),
            'delivery_alerts': self._verificar_alertas_entregas(),
            'system_alerts': self._verificar_alertas_sistema()
        }
        
        # Consolidar resultados
        total_new_alerts = sum(len(alerts) for alerts in alerts_found.values())
        
        log_operation("VERIFICACION_ALERTAS_COMPLETA", 
                     f"Nuevas alertas encontradas: {total_new_alerts}")
        
        return {
            'verification_time': datetime.now().isoformat(),
            'alerts_found': alerts_found,
            'total_new_alerts': total_new_alerts,
            'active_alerts_count': len(self.active_alerts),
            'summary': self.obtener_resumen_alertas()
        }
    
    def _verificar_alertas_stock(self) -> List[Alert]:
        """Verifica alertas relacionadas con el inventario"""
        self.logger.debug("Verificando alertas de stock")
        
        new_alerts = []
        
        try:
            # Obtener alertas de stock desde el microservicio de insumos
            stock_alerts = micro_insumos.obtener_alertas_stock()
            
            # Procesar alertas críticas
            for insumo in stock_alerts['criticas']:
                key = self._make_alert_key(AlertType.STOCK_CRITICO, insumo['id'])
                if key not in self.active_alerts:
                    alert = Alert(
                        alert_type=AlertType.STOCK_CRITICO,
                        severity=AlertSeverity.CRITICAL,
                        title=f"Stock agotado: {insumo['nombre']}",
                        message=f"El insumo '{insumo['nombre']}' está completamente agotado. "
                               f"Cantidad actual: {insumo['cantidad_actual']} {insumo['unidad_medida']}",
                        entity_id=insumo['id'],
                        entity_type='insumo',
                        data={
                            'categoria': insumo['categoria'],
                            'cantidad_actual': insumo['cantidad_actual'],
                            'cantidad_minima': insumo['cantidad_minima'],
                            'unidad_medida': insumo['unidad_medida']
                        }
                    )
                    self._add_alert(alert, key)
                    new_alerts.append(alert)
            
            # Procesar alertas de stock bajo
            for insumo in stock_alerts['bajas']:
                key = self._make_alert_key(AlertType.STOCK_BAJO, insumo['id'])
                if key not in self.active_alerts:
                    alert = Alert(
                        alert_type=AlertType.STOCK_BAJO,
                        severity=AlertSeverity.HIGH,
                        title=f"Stock bajo: {insumo['nombre']}",
                        message=f"El insumo '{insumo['nombre']}' tiene stock por debajo del mínimo. "
                               f"Cantidad actual: {insumo['cantidad_actual']} {insumo['unidad_medida']}, "
                               f"Mínimo requerido: {insumo['cantidad_minima']} {insumo['unidad_medida']}",
                        entity_id=insumo['id'],
                        entity_type='insumo',
                        data={
                            'categoria': insumo['categoria'],
                            'cantidad_actual': insumo['cantidad_actual'],
                            'cantidad_minima': insumo['cantidad_minima'],
                            'unidad_medida': insumo['unidad_medida']
                        }
                    )
                    self._add_alert(alert, key)
                    new_alerts.append(alert)
            
        
        except Exception as e:
            self.logger.error(f"Error verificando alertas de stock: {e}")
            # Crear alerta de error del sistema
            error_alert = Alert(
                alert_type=AlertType.SISTEMA_ERROR,
                severity=AlertSeverity.HIGH,
                title="Error en verificación de stock",
                message=f"Error al verificar alertas de inventario: {str(e)}",
                data={'error': str(e), 'component': 'stock_verification'}
            )
            self._add_alert(error_alert)
            new_alerts.append(error_alert)
        
        return new_alerts
    
    def _verificar_alertas_entregas(self) -> List[Alert]:
        """Verifica alertas relacionadas con entregas"""
        self.logger.debug("Verificando alertas de entregas")
        
        new_alerts = []
        
        try:
            # Configuración de umbrales
            umbral_entregas_dia = self.alert_config.get('umbral_entregas_frecuentes_dia', 5)
            
            # Obtener entregas de hoy
            entregas_hoy = micro_entregas.obtener_entregas_hoy()
            
            # Analizar entregas frecuentes por insumo
            insumo_counts = {}
            for entrega in entregas_hoy['entregas']:
                insumo_id = entrega['insumo_id']
                if insumo_id not in insumo_counts:
                    insumo_counts[insumo_id] = {
                        'count': 0,
                        'nombre': entrega['insumo_nombre'],
                        'categoria': entrega['insumo_categoria'],
                        'total_cantidad': 0
                    }
                
                insumo_counts[insumo_id]['count'] += 1
                insumo_counts[insumo_id]['total_cantidad'] += entrega['cantidad']
            
            # Crear alertas para entregas frecuentes
            for insumo_id, info in insumo_counts.items():
                if info['count'] >= umbral_entregas_dia:
                    # Evitar duplicados por día e insumo
                    today_iso = date.today().isoformat()
                    key = self._make_alert_key(AlertType.ENTREGAS_FRECUENTES, insumo_id, today_iso)
                    if key not in self.active_alerts:
                        alert = Alert(
                            alert_type=AlertType.ENTREGAS_FRECUENTES,
                            severity=AlertSeverity.MEDIUM,
                            title=f"Entregas frecuentes: {info['nombre']}",
                            message=f"El insumo '{info['nombre']}' ha tenido {info['count']} entregas hoy. "
                                   f"Esto podría indicar alta demanda o problemas de stock.",
                            entity_id=insumo_id,
                            entity_type='insumo',
                            data={
                                'entregas_hoy': info['count'],
                                'cantidad_total': info['total_cantidad'],
                                'categoria': info['categoria'],
                                'umbral': umbral_entregas_dia,
                                'fecha': today_iso
                            }
                        )
                        self._add_alert(alert, key)
                        new_alerts.append(alert)
        
        except Exception as e:
            self.logger.error(f"Error verificando alertas de entregas: {e}")
            error_alert = Alert(
                alert_type=AlertType.SISTEMA_ERROR,
                severity=AlertSeverity.MEDIUM,
                title="Error en verificación de entregas",
                message=f"Error al verificar alertas de entregas: {str(e)}",
                data={'error': str(e), 'component': 'delivery_verification'}
            )
            self._add_alert(error_alert)
            new_alerts.append(error_alert)
        
        return new_alerts
    
    def _verificar_alertas_sistema(self) -> List[Alert]:
        """Verifica alertas del sistema general"""
        self.logger.debug("Verificando alertas del sistema")
        
        new_alerts = []
        
        try:
            # Verificar consistencia de datos
            inconsistencies = self._verificar_consistencia_datos()
            
            for inconsistency in inconsistencies:
                alert = Alert(
                    alert_type=AlertType.DATA_INCONSISTENCY,
                    severity=AlertSeverity.HIGH,
                    title=f"Inconsistencia de datos: {inconsistency['type']}",
                    message=inconsistency['message'],
                    data=inconsistency['data']
                )
                self._add_alert(alert)
                new_alerts.append(alert)
        
        except Exception as e:
            self.logger.error(f"Error verificando alertas del sistema: {e}")
            error_alert = Alert(
                alert_type=AlertType.SISTEMA_ERROR,
                severity=AlertSeverity.HIGH,
                title="Error en verificación del sistema",
                message=f"Error al verificar alertas del sistema: {str(e)}",
                data={'error': str(e), 'component': 'system_verification'}
            )
            self._add_alert(error_alert)
            new_alerts.append(error_alert)
        
        return new_alerts
    
    def _verificar_consistencia_datos(self) -> List[Dict[str, Any]]:
        """Verifica la consistencia de los datos del sistema"""
        inconsistencies = []
        
        try:
            # Verificar insumos con stock negativo (no debería pasar por los constraints)
            insumos_data = micro_insumos.listar_insumos(active_only=True)
            for insumo in insumos_data['insumos']:
                if insumo['cantidad_actual'] < 0:
                    inconsistencies.append({
                        'type': 'stock_negativo',
                        'message': f"Insumo '{insumo['nombre']}' tiene stock negativo: {insumo['cantidad_actual']}",
                        'data': {'insumo_id': insumo['id'], 'cantidad': insumo['cantidad_actual']}
                    })
                
                if insumo['cantidad_minima'] > insumo['cantidad_maxima']:
                    inconsistencies.append({
                        'type': 'rangos_invalidos',
                        'message': f"Insumo '{insumo['nombre']}' tiene mínimo mayor que máximo",
                        'data': {
                            'insumo_id': insumo['id'],
                            'minimo': insumo['cantidad_minima'],
                            'maximo': insumo['cantidad_maxima']
                        }
                    })
            
            # Verificar empleados sin cédula (requerida)
            empleados_data = micro_empleados.listar_empleados(active_only=True)
            for empleado in empleados_data['empleados']:
                if not empleado.get('cedula', '').strip():
                    inconsistencies.append({
                        'type': 'empleado_sin_cedula',
                        'message': f"Empleado '{empleado['nombre_completo']}' no tiene cédula registrada",
                        'data': {'empleado_id': empleado['id']}
                    })
        
        except Exception as e:
            self.logger.error(f"Error verificando consistencia de datos: {e}")
        
        return inconsistencies
    
    def _make_alert_key(self, alert_type: AlertType, entity_id: Optional[int] = None, extra: Optional[str] = None) -> str:
        """Crea una llave determinística para deduplicar alertas"""
        return f"{alert_type.value}:{entity_id or 'SYS'}:{extra or ''}"

    def _add_alert(self, alert: Alert, key: Optional[str] = None):
        """Añade una alerta al sistema usando una llave estable para evitar duplicados"""
        if key is None:
            key = self._make_alert_key(alert.alert_type, alert.entity_id)
        self.active_alerts[key] = alert
        self.alert_history.append(alert)
        self.logger.info(f"Nueva alerta añadida: {alert.title} (KEY: {key})")
    
    @service_exception_handler("MicroAlertasService")
    def obtener_alertas_activas(self, severity_filter: Optional[str] = None,
                              type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene todas las alertas activas del sistema.
        
        Args:
            severity_filter: Filtrar por severidad (LOW, MEDIUM, HIGH, CRITICAL)
            type_filter: Filtrar por tipo de alerta
            
        Returns:
            Lista de alertas activas
        """
        alerts = []
        
        for alert in self.active_alerts.values():
            if alert.resolved:
                continue
            
            # Aplicar filtros
            if severity_filter and alert.severity.value != severity_filter:
                continue
            
            if type_filter and alert.alert_type.value != type_filter:
                continue
            
            alerts.append(alert.to_dict())
        
        # Ordenar por severidad y fecha
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3
        }
        
        alerts.sort(key=lambda x: (
            severity_order.get(AlertSeverity(x['severity']), 99),
            x['created_at']
        ))
        
        return alerts
    
    @service_exception_handler("MicroAlertasService")
    def obtener_resumen_alertas(self) -> Dict[str, Any]:
        """
        Obtiene un resumen estadístico de las alertas.
        
        Returns:
            Diccionario con estadísticas de alertas
        """
        active_alerts = [alert for alert in self.active_alerts.values() if not alert.resolved]
        
        # Contar por severidad
        severity_counts = {
            'CRITICAL': 0,
            'HIGH': 0,
            'MEDIUM': 0,
            'LOW': 0
        }
        
        # Contar por tipo
        type_counts = {
            'STOCK_CRITICO': 0,
            'STOCK_BAJO': 0,
            'STOCK_EXCESO': 0,
            'ENTREGAS_FRECUENTES': 0,
            'SISTEMA_ERROR': 0,
            'BACKUP_FAILED': 0,
            'DATA_INCONSISTENCY': 0
        }
        
        for alert in active_alerts:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
            type_counts[alert.alert_type.value] = type_counts.get(alert.alert_type.value, 0) + 1
        
        # Alertas que requieren acción
        action_required = sum(1 for alert in active_alerts if alert.requires_action())
        
        return {
            'total_active': len(active_alerts),
            'total_resolved': len([a for a in self.active_alerts.values() if a.resolved]),
            'total_history': len(self.alert_history),
            'action_required': action_required,
            'by_severity': severity_counts,
            'by_type': type_counts,
            'last_verification': datetime.now().isoformat()
        }
    
    @service_exception_handler("MicroAlertasService")
    def resolver_alerta(self, alert_id: str, resolved_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Marca una alerta como resuelta.
        
        Args:
            alert_id: ID de la alerta a resolver
            resolved_by: Usuario que resuelve la alerta
            
        Returns:
            Diccionario con resultado de la operación
        """
        if alert_id not in self.active_alerts:
            raise BusinessLogicException(f"No se encontró la alerta con ID: {alert_id}")
        
        alert = self.active_alerts[alert_id]
        if alert.resolved:
            return {
                'success': True,
                'message': 'La alerta ya estaba resuelta',
                'resolved_at': alert.resolved_at.isoformat()
            }
        
        alert.resolve(resolved_by)
        
        log_operation("ALERTA_RESUELTA", 
                     f"ID: {alert_id}, Tipo: {alert.alert_type.value}, "
                     f"Resuelto por: {resolved_by or 'Sistema'}")
        
        self.logger.info(f"Alerta resuelta: {alert.title} (ID: {alert_id})")
        
        return {
            'success': True,
            'message': 'Alerta marcada como resuelta',
            'resolved_at': alert.resolved_at.isoformat(),
            'resolved_by': alert.resolved_by
        }
    
    @service_exception_handler("MicroAlertasService")
    def resolver_alertas_por_tipo(self, alert_type: str, resolved_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Resuelve todas las alertas de un tipo específico.
        
        Args:
            alert_type: Tipo de alerta a resolver
            resolved_by: Usuario que resuelve las alertas
            
        Returns:
            Diccionario con resultado de la operación
        """
        resolved_count = 0
        
        for alert in self.active_alerts.values():
            if alert.alert_type.value == alert_type and not alert.resolved:
                alert.resolve(resolved_by)
                resolved_count += 1
        
        log_operation("ALERTAS_RESUELTAS_POR_TIPO", 
                     f"Tipo: {alert_type}, Cantidad: {resolved_count}")
        
        return {
            'success': True,
            'message': f'Se resolvieron {resolved_count} alertas de tipo {alert_type}',
            'resolved_count': resolved_count
        }
    
    @service_exception_handler("MicroAlertasService")
    def limpiar_alertas_antiguas(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Limpia alertas resueltas antiguas del historial.
        
        Args:
            days_old: Días de antigüedad para considerar alertas como antiguas
            
        Returns:
            Diccionario con resultado de la limpieza
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Filtrar historial
        old_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history
            if not alert.resolved or alert.resolved_at > cutoff_date
        ]
        
        # Filtrar alertas activas resueltas
        resolved_to_remove = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.resolved and alert.resolved_at < cutoff_date
        ]
        
        for alert_id in resolved_to_remove:
            del self.active_alerts[alert_id]
        
        cleaned_count = old_count - len(self.alert_history) + len(resolved_to_remove)
        
        log_operation("ALERTAS_LIMPIADAS", f"Eliminadas: {cleaned_count}, Antigüedad: {days_old} días")
        
        return {
            'success': True,
            'message': f'Se limpiaron {cleaned_count} alertas antiguas',
            'cleaned_count': cleaned_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    @service_exception_handler("MicroAlertasService")
    def crear_alerta_personalizada(self, alert_type: str, severity: str, title: str, 
                                 message: str, entity_id: Optional[int] = None,
                                 entity_type: Optional[str] = None, 
                                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Crea una alerta personalizada.
        
        Args:
            alert_type: Tipo de alerta
            severity: Severidad (LOW, MEDIUM, HIGH, CRITICAL)
            title: Título de la alerta
            message: Mensaje descriptivo
            entity_id: ID de entidad relacionada (opcional)
            entity_type: Tipo de entidad (opcional)
            data: Datos adicionales (opcional)
            
        Returns:
            Diccionario con información de la alerta creada
        """
        try:
            alert_type_enum = AlertType(alert_type)
            severity_enum = AlertSeverity(severity)
        except ValueError as e:
            raise BusinessLogicException(f"Tipo o severidad de alerta inválida: {e}")
        
        alert = Alert(
            alert_type=alert_type_enum,
            severity=severity_enum,
            title=title,
            message=message,
            entity_id=entity_id,
            entity_type=entity_type,
            data=data
        )
        
        self._add_alert(alert)
        
        log_operation("ALERTA_PERSONALIZADA_CREADA", 
                     f"Tipo: {alert_type}, Título: {title}")
        
        return {
            'success': True,
            'alert_id': alert.id,
            'alert': alert.to_dict(),
            'message': 'Alerta personalizada creada exitosamente'
        }
    
    @service_exception_handler("MicroAlertasService")
    def obtener_alertas_dashboard(self) -> Dict[str, Any]:
        """
        Obtiene alertas formatadas para mostrar en el dashboard.
        
        Returns:
            Diccionario con alertas organizadas para el dashboard
        """
        active_alerts = self.obtener_alertas_activas()
        
        # Separar por prioridad para el dashboard
        critical_alerts = [a for a in active_alerts if a['severity'] == 'CRITICAL']
        high_alerts = [a for a in active_alerts if a['severity'] == 'HIGH']
        other_alerts = [a for a in active_alerts if a['severity'] in ['MEDIUM', 'LOW']]
        
        # Limitar número de alertas mostradas
        max_per_category = 5
        
        return {
            'critical': critical_alerts[:max_per_category],
            'high': high_alerts[:max_per_category],
            'others': other_alerts[:max_per_category],
            'total_critical': len(critical_alerts),
            'total_high': len(high_alerts),
            'total_others': len(other_alerts),
            'total_active': len(active_alerts),
            'has_critical': len(critical_alerts) > 0,
            'has_high': len(high_alerts) > 0,
            'summary': self.obtener_resumen_alertas()
        }


# Instancia global del microservicio de alertas
micro_alertas = MicroAlertasService()

# Funciones de conveniencia para uso directo
def verificar_todas_las_alertas() -> Dict[str, Any]:
    """Función de conveniencia para verificar todas las alertas"""
    return micro_alertas.verificar_todas_las_alertas()

def obtener_alertas_activas() -> List[Dict[str, Any]]:
    """Función de conveniencia para obtener alertas activas"""
    return micro_alertas.obtener_alertas_activas()

def obtener_alertas_dashboard() -> Dict[str, Any]:
    """Función de conveniencia para obtener alertas del dashboard"""
    return micro_alertas.obtener_alertas_dashboard()

def resolver_alerta(alert_id: str, resolved_by: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para resolver una alerta"""
    return micro_alertas.resolver_alerta(alert_id, resolved_by)