"""
DelegInsumos - Dashboard Principal
Tab de dashboard con resumen general del sistema, alertas y estadísticas
"""

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.widgets import DateEntry
    from ttkbootstrap.scrolled import ScrolledFrame
except ImportError:
    print("Error: ttkbootstrap requerido. Ejecute: pip install ttkbootstrap")

from services.micro_insumos import micro_insumos
from services.micro_empleados import micro_empleados
from services.micro_entregas import micro_entregas
from services.micro_alertas import micro_alertas
from services.reportes_service import reportes_service
from services.backup_service import backup_service
from utils.logger import LoggerMixin, log_user_action
from utils.helpers import show_error_message, show_info_message


class DashboardTab(LoggerMixin):
    """
    Tab del dashboard principal con resumen del sistema
    """
    
    def __init__(self, parent, app_instance):
        super().__init__()
        self.parent = parent
        self.app = app_instance

        # Crear frame principal
        self.frame = ttk.Frame(parent, padding="15")

        # Crear contenedor con scroll
        self.container = ScrolledFrame(self.frame, autohide=True)
        self.container.pack(fill=BOTH, expand=True)

        # Variables de datos
        self.dashboard_data = {}

        # Crear interfaz
        self._create_interface()

        # Cargar datos inicial
        self.refresh_data()

        self.logger.info("DashboardTab inicializado")
    
    def _create_interface(self):
        """Crea la interfaz del dashboard"""

        # Título de bienvenida
        welcome_frame = ttk.Frame(self.container)
        welcome_frame.pack(fill=X, pady=(0, 20))

        welcome_label = ttk.Label(
            welcome_frame,
            text=f"🏢 Bienvenido a DelegInsumos",
            font=("Helvetica", 16, "bold"),
            bootstyle="primary"
        )
        welcome_label.pack(side=LEFT)

        # Botón de actualización
        refresh_btn = ttk.Button(
            welcome_frame,
            text="🔄 Actualizar",
            command=lambda: self.refresh_data(quick=True),
            bootstyle="outline-primary"
        )
        refresh_btn.pack(side=RIGHT)

        # Panel de métricas principales
        self._create_metrics_section()

        # Panel de alertas
        self._create_alerts_section()

        # Panel de estadísticas
        self._create_statistics_section()

        # Panel de acciones rápidas
        self._create_quick_actions_section()

        self.logger.debug("Interfaz del dashboard creada")
    
    def _create_metrics_section(self):
        """Crea la sección de métricas principales"""

        # Frame contenedor con título
        metrics_labelframe = ttk.Labelframe(
            self.container,
            text="📊 Métricas Principales",
            padding="15",
            bootstyle="primary"
        )
        metrics_labelframe.pack(fill=X, pady=(0, 15))
        
        # Grid para métricas
        metrics_inner_frame = ttk.Frame(metrics_labelframe)
        metrics_inner_frame.pack(fill=X)
        
        # Configurar grid
        for i in range(4):
            metrics_inner_frame.columnconfigure(i, weight=1)
        
        # Métricas individuales
        self._create_metric_card(metrics_inner_frame, "total_insumos", "📦", "Total Insumos", "0", 0, 0)
        self._create_metric_card(metrics_inner_frame, "empleados_activos", "👥", "Empleados Activos", "0", 0, 1)
        self._create_metric_card(metrics_inner_frame, "entregas_hoy", "📋", "Entregas Hoy", "0", 0, 2)
        self._create_metric_card(metrics_inner_frame, "alertas_activas", "⚠️", "Alertas Activas", "0", 0, 3)
        
        self.logger.debug("Sección de métricas creada")
    
    def _create_metric_card(self, parent, metric_id: str, icon: str, title: str, 
                           default_value: str, row: int, col: int):
        """
        Crea una tarjeta de métrica individual.
        
        Args:
            parent: Widget padre
            metric_id: ID de la métrica
            icon: Icono de la métrica
            title: Título de la métrica
            default_value: Valor por defecto
            row: Fila en el grid
            col: Columna en el grid
        """
        
        # Frame de la métrica
        metric_frame = ttk.Frame(parent, bootstyle="info", padding="10")
        metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
        
        # Icono
        icon_label = ttk.Label(
            metric_frame,
            text=icon,
            font=("Segoe UI Emoji", 20)
        )
        icon_label.pack()
        
        # Valor (se actualizará dinámicamente)
        value_var = tk.StringVar(value=default_value)
        setattr(self, f"{metric_id}_var", value_var)
        
        value_label = ttk.Label(
            metric_frame,
            textvariable=value_var,
            font=("Helvetica", 14, "bold"),
            bootstyle="primary"
        )
        value_label.pack()
        
        # Título
        title_label = ttk.Label(
            metric_frame,
            text=title,
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        title_label.pack()
    
    def _create_alerts_section(self):
        """Crea la sección de alertas del sistema"""

        # Frame contenedor
        alerts_labelframe = ttk.Labelframe(
            self.container,
            text="🚨 Alertas del Sistema",
            padding="15",
            bootstyle="warning"
        )
        alerts_labelframe.pack(fill=X, pady=(0, 15))
        
        # Frame para contenido de alertas
        alerts_content = ttk.Frame(alerts_labelframe)
        alerts_content.pack(fill=BOTH, expand=True)
        
        # Treeview para mostrar alertas
        columns = ["Tipo", "Título", "Mensaje", "Fecha"]
        self.alerts_tree = ttk.Treeview(
            alerts_content,
            columns=columns,
            show="tree headings",
            bootstyle="warning"
        )
        
        # Configurar columnas
        self.alerts_tree.heading("#0", text="", anchor="w")
        self.alerts_tree.column("#0", width=30, stretch=False)
        
        for col in columns:
            self.alerts_tree.heading(col, text=col, anchor="center")
        
        self.alerts_tree.column("Tipo", width=100, stretch=False)
        self.alerts_tree.column("Título", width=200, stretch=True)
        self.alerts_tree.column("Mensaje", width=300, stretch=True)
        self.alerts_tree.column("Fecha", width=120, stretch=False)
        
        # Estilos por severidad (resaltado visual)
        try:
            self.alerts_tree.tag_configure('CRITICAL', background='#fdecea', foreground='#b71c1c')
            self.alerts_tree.tag_configure('HIGH', background='#fff3e0', foreground='#e65100')
            self.alerts_tree.tag_configure('MEDIUM', background='#fffde7', foreground='#f57f17')
            self.alerts_tree.tag_configure('LOW', background='#e8f5e9', foreground='#1b5e20')
        except Exception:
            pass
        
        # Scrollbar para alertas
        alerts_scrollbar = ttk.Scrollbar(alerts_content, orient=VERTICAL, command=self.alerts_tree.yview)
        self.alerts_tree.configure(yscrollcommand=alerts_scrollbar.set)
        
        # Pack del treeview y scrollbar
        self.alerts_tree.pack(side=LEFT, fill=BOTH, expand=True)
        alerts_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Frame botones de alertas
        alerts_buttons = ttk.Frame(alerts_labelframe)
        alerts_buttons.pack(fill=X, pady=(10, 0))
        
        ttk.Button(
            alerts_buttons,
            text="🔍 Ver Todas las Alertas",
            command=self._show_all_alerts,
            bootstyle="outline-warning"
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            alerts_buttons,
            text="🔄 Verificar Alertas",
            command=self._check_alerts,
            bootstyle="outline-info"
        ).pack(side=LEFT)
        
        self.logger.debug("Sección de alertas creada")
    
    def _create_statistics_section(self):
        """Crea la sección de estadísticas del sistema"""

        # Frame principal dividido en dos columnas
        stats_frame = ttk.Frame(self.container)
        stats_frame.pack(fill=X, pady=(0, 15))
        
        # Columna izquierda: Stock por categorías
        left_frame = ttk.Labelframe(
            stats_frame,
            text="📈 Stock por Categorías",
            padding="15",
            bootstyle="success"
        )
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8))
        
        # Treeview para categorías (sin columna de Valor)
        self.categories_tree = ttk.Treeview(
            left_frame,
            columns=["Total Items", "Cantidad"],
            show="tree headings",
            bootstyle="success"
        )
        
        self.categories_tree.heading("#0", text="Categoría", anchor="w")
        self.categories_tree.heading("Total Items", text="Items", anchor="center")
        self.categories_tree.heading("Cantidad", text="Cantidad", anchor="center")
        
        self.categories_tree.column("#0", width=120, stretch=True)
        self.categories_tree.column("Total Items", width=60, stretch=False)
        self.categories_tree.column("Cantidad", width=80, stretch=False)
        
        self.categories_tree.pack(fill=BOTH, expand=True)
        
        # Columna derecha: Entregas recientes
        right_frame = ttk.Labelframe(
            stats_frame,
            text="🕒 Entregas Recientes (7 días)",
            padding="15",
            bootstyle="info"
        )
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(8, 0))
        
        # Treeview para entregas recientes
        self.recent_deliveries_tree = ttk.Treeview(
            right_frame,
            columns=["Empleado", "Insumo", "Cantidad", "Fecha"],
            show="tree headings",
            bootstyle="info"
        )
        
        self.recent_deliveries_tree.heading("#0", text="", anchor="w")
        self.recent_deliveries_tree.heading("Empleado", text="Empleado", anchor="center")
        self.recent_deliveries_tree.heading("Insumo", text="Insumo", anchor="center")
        self.recent_deliveries_tree.heading("Cantidad", text="Cantidad", anchor="center")
        self.recent_deliveries_tree.heading("Fecha", text="Fecha", anchor="center")
        
        self.recent_deliveries_tree.column("#0", width=0, stretch=False)
        self.recent_deliveries_tree.column("Empleado", width=120, stretch=True)
        self.recent_deliveries_tree.column("Insumo", width=120, stretch=True)
        self.recent_deliveries_tree.column("Cantidad", width=80, stretch=False)
        self.recent_deliveries_tree.column("Fecha", width=80, stretch=False)
        
        self.recent_deliveries_tree.pack(fill=BOTH, expand=True)
        
        self.logger.debug("Sección de estadísticas creada")
    
    def _create_quick_actions_section(self):
        """Crea la sección de acciones rápidas"""

        actions_labelframe = ttk.Labelframe(
            self.container,
            text="⚡ Acciones Rápidas",
            padding="15",
            bootstyle="dark"
        )
        actions_labelframe.pack(fill=X, pady=(0, 15))
        
        # Grid para botones
        actions_grid = ttk.Frame(actions_labelframe)
        actions_grid.pack(fill=X)
        
        # Configurar grid (3 columnas)
        for i in range(3):
            actions_grid.columnconfigure(i, weight=1)
        
        # Fila 1: Gestión principal
        ttk.Button(
            actions_grid,
            text="📦 Agregar Insumo",
            command=self._quick_add_insumo,
            bootstyle="success",
            width=20
        ).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            actions_grid,
            text="👤 Agregar Empleado",
            command=self._quick_add_empleado,
            bootstyle="info",
            width=20
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            actions_grid,
            text="📋 Nueva Entrega",
            command=self._quick_new_delivery,
            bootstyle="primary",
            width=20
        ).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # Fila 2: Reportes y backup
        ttk.Button(
            actions_grid,
            text="📄 Reporte de Inventario",
            command=self._quick_inventory_report,
            bootstyle="warning",
            width=20
        ).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            actions_grid,
            text="📊 Reporte de Entregas",
            command=self._quick_deliveries_report,
            bootstyle="secondary",
            width=20
        ).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            actions_grid,
            text="💾 Backup Manual",
            command=self._quick_backup,
            bootstyle="danger",
            width=20
        ).grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        self.logger.debug("Sección de acciones rápidas creada")
    
    def refresh_data(self, quick: bool = False):
        """Actualiza todos los datos del dashboard

        Args:
            quick: si True, realiza una actualización rápida de datos (sin reconstrucción de UI)
        """
        try:
            self.logger.debug(f"Refrescando datos del dashboard (quick={quick})")
            
            # Actualizar métricas principales
            self._update_main_metrics()
            
            # Actualizar alertas
            self._update_alerts_display()
            
            # Actualizar estadísticas
            self._update_statistics_display()
            
            # Actualizar timestamp
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Dashboard actualizado", "success")
            
            self.logger.info("Dashboard actualizado exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error actualizando dashboard: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error actualizando dashboard", "danger")
            show_error_message("Error", f"Error actualizando dashboard: {str(e)}", self.container)
    
    def _update_main_metrics(self):
        """Actualiza las métricas principales del dashboard"""
        try:
            # Obtener datos de insumos
            insumos_data = micro_insumos.listar_insumos(active_only=True, include_status=True)
            
            # Obtener entregas de hoy
            entregas_hoy = micro_entregas.obtener_entregas_hoy()
            
            # Obtener alertas
            alertas_data = micro_alertas.obtener_alertas_dashboard()
            
            # Actualizar variables de la UI
            self.total_insumos_var.set(str(insumos_data.get('total', 0)))

            # Obtener datos de empleados
            empleados_data = micro_empleados.listar_empleados(active_only=True, include_stats=True)
            empleados_activos = empleados_data.get('statistics', {}).get('empleados_activos', 0)
            self.empleados_activos_var.set(str(empleados_activos))

            self.entregas_hoy_var.set(str(entregas_hoy.get('total_entregas', 0)))

            total_alertas = alertas_data.get('total_active', 0)
            self.alertas_activas_var.set(str(total_alertas))
            
            # Cambiar color de alertas según cantidad
            if hasattr(self, 'alertas_activas_var'):
                if total_alertas > 0:
                    # Buscar el label de alertas para cambiar estilo (esto sería más complejo en implementación real)
                    pass
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas principales: {e}")
    
    def _update_alerts_display(self):
        """Actualiza la visualización de alertas"""
        try:
            # Limpiar tree
            for item in self.alerts_tree.get_children():
                self.alerts_tree.delete(item)
            
            # Obtener alertas activas
            alertas_activas = micro_alertas.obtener_alertas_activas()

            # Agregar alertas al tree (máximo 10 más recientes)
            for idx, alert in enumerate(alertas_activas[:10]):
                # Preparar datos
                tipo = alert['alert_type'].replace('_', ' ').title()
                titulo = alert['title'][:40] + "..." if len(alert['title']) > 40 else alert['title']
                mensaje = alert['message'][:60] + "..." if len(alert['message']) > 60 else alert['message']
                try:
                    fecha = datetime.fromisoformat(alert['created_at'].replace('Z', '+00:00')).strftime('%d/%m %H:%M')
                except Exception:
                    fecha = alert.get('created_at', '')[:16].replace('T', ' ')
                
                # Tags: severidad + zebra
                severity_tag = alert.get('severity', 'BAJO')
                zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
                
                # Insertar con ambas etiquetas
                item_id = self.alerts_tree.insert(
                    "", "end",
                    text=alert['icon'],
                    values=(tipo, titulo, mensaje, fecha),
                    tags=(severity_tag, zebra_tag)
                )
                
                # Configurar texto del tipo con emoji según severidad
                if alert['severity'] == 'CRITICAL':
                    self.alerts_tree.set(item_id, "Tipo", f"🔴 {tipo}")
                elif alert['severity'] == 'HIGH':
                    self.alerts_tree.set(item_id, "Tipo", f"🟠 {tipo}")
                elif alert['severity'] == 'MEDIUM':
                    self.alerts_tree.set(item_id, "Tipo", f"🟡 {tipo}")
                else:
                    self.alerts_tree.set(item_id, "Tipo", f"🟢 {tipo}")
                
                # Guardar ID de alerta en columna oculta
                self.alerts_tree.set(item_id, "#1", alert['id'])
            
            # Estilos zebra para alertas
            try:
                self.alerts_tree.tag_configure("zebra_even", background="#F7FAFF", foreground="#000000")
                self.alerts_tree.tag_configure("zebra_odd", background="#EDF3FF", foreground="#000000")
            except Exception:
                pass  # ID oculto en columna
            
            if not alertas_activas:
                # Agregar mensaje de "sin alertas"
                self.alerts_tree.insert("", "end", text="✅", values=("Sin Alertas", "Todo funcionando correctamente", "No hay alertas activas", ""))
            
        except Exception as e:
            self.logger.error(f"Error actualizando alertas: {e}")
    
    def _update_statistics_display(self):
        """Actualiza la visualización de estadísticas"""
        try:
            # Actualizar categorías
            self._update_categories_tree()
            
            # Actualizar entregas recientes
            self._update_recent_deliveries_tree()
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas: {e}")
    
    def _update_categories_tree(self):
        """Actualiza el árbol de categorías"""
        try:
            # Limpiar tree
            for item in self.categories_tree.get_children():
                self.categories_tree.delete(item)
            
            # Obtener resumen por categorías
            categorias = micro_insumos.obtener_resumen_por_categoria()
            
            # Insertar filas con zebra pattern
            for idx, categoria in enumerate(categorias):
                zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
                self.categories_tree.insert(
                    "", "end",
                    text=categoria['categoria'],
                    values=(
                        categoria['total_insumos'],
                        categoria['cantidad_total']
                    ),
                    tags=(zebra_tag,)
                )
            # Estilos zebra
            try:
                self.categories_tree.tag_configure("zebra_even", background="#F7FAFF", foreground="#000000")
                self.categories_tree.tag_configure("zebra_odd", background="#EDF3FF", foreground="#000000")
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error(f"Error actualizando categorías: {e}")
    
    def _update_recent_deliveries_tree(self):
        """Actualiza el árbol de entregas recientes"""
        try:
            # Limpiar tree
            for item in self.recent_deliveries_tree.get_children():
                self.recent_deliveries_tree.delete(item)
            
            # Obtener entregas recientes
            entregas_recientes = micro_entregas.obtener_entregas_recientes(dias=7, limit=10)
            
            # Insertar filas con zebra pattern
            for idx, entrega in enumerate(entregas_recientes.get('entregas', [])):
                empleado = entrega['empleado_nombre'].split()[0] if entrega['empleado_nombre'] else "N/A"  # Solo primer nombre
                insumo = entrega['insumo_nombre'][:20] + "..." if len(entrega['insumo_nombre']) > 20 else entrega['insumo_nombre']
                cantidad = f"{entrega['cantidad']} {entrega['insumo_unidad']}"
                fecha = datetime.fromisoformat(entrega['fecha_entrega'].replace('Z', '+00:00')).strftime('%d/%m')
                zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
                
                self.recent_deliveries_tree.insert(
                    "", "end",
                    text="",
                    values=(empleado, insumo, cantidad, fecha),
                    tags=(zebra_tag,)
                )
            # Estilos zebra
            try:
                self.recent_deliveries_tree.tag_configure("zebra_even", background="#F7FAFF", foreground="#000000")
                self.recent_deliveries_tree.tag_configure("zebra_odd", background="#EDF3FF", foreground="#000000")
            except Exception:
                pass
                
        except Exception as e:
            self.logger.error(f"Error actualizando entregas recientes: {e}")
    
    # Event handlers para acciones rápidas
    
    def _quick_add_insumo(self):
        """Acción rápida: Agregar insumo"""
        log_user_action("CLICK", "quick_add_insumo", "Dashboard")
        
        # Cambiar al tab de insumos y mostrar formulario
        self.app.notebook.select(1)  # Tab de insumos
        if hasattr(self.app, 'insumos_tab'):
            self.app.insumos_tab.show_add_form()
    
    def _quick_add_empleado(self):
        """Acción rápida: Agregar empleado"""
        log_user_action("CLICK", "quick_add_empleado", "Dashboard")
        
        # Cambiar al tab de empleados
        self.app.notebook.select(2)  # Tab de empleados
        if hasattr(self.app, 'empleados_tab'):
            self.app.empleados_tab.show_add_form()
    
    def _quick_new_delivery(self):
        """Acción rápida: Nueva entrega"""
        log_user_action("CLICK", "quick_new_delivery", "Dashboard")
        
        # Cambiar al tab de entregas
        self.app.notebook.select(3)  # Tab de entregas
        if hasattr(self.app, 'entregas_tab'):
            self.app.entregas_tab.show_add_form()
    
    def _quick_inventory_report(self):
        """Acción rápida: Generar reporte de inventario"""
        log_user_action("CLICK", "quick_inventory_report", "Dashboard")
        
        try:
            self.app.update_status("Generando reporte de inventario...")
            
            # Generar reporte PDF
            result = reportes_service.generar_reporte_inventario_pdf()
            
            if result['success']:
                self.app.update_status("Reporte generado exitosamente", "success")
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de inventario creado:\n{result['filename']}\n\nTamaño: {result['size_mb']} MB",
                    self.container
                )
            else:
                self.app.update_status("Error generando reporte", "danger")
                
        except Exception as e:
            self.logger.error(f"Error generando reporte rápido: {e}")
            self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.container)
    
    def _quick_deliveries_report(self):
        """Acción rápida: Generar reporte de entregas"""
        log_user_action("CLICK", "quick_deliveries_report", "Dashboard")
        
        try:
            self.app.update_status("Generando reporte de entregas...")
            
            # Generar reporte de últimos 30 días
            result = reportes_service.generar_reporte_entregas_pdf()
            
            if result['success']:
                self.app.update_status("Reporte generado exitosamente", "success")
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de entregas creado:\n{result['filename']}\n\nPeríodo: {result['periodo_inicio']} - {result['periodo_fin']}",
                    self.container
                )
            else:
                self.app.update_status("Error generando reporte", "danger")
                
        except Exception as e:
            self.logger.error(f"Error generando reporte de entregas: {e}")
            self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.container)
    
    def _quick_backup(self):
        """Acción rápida: Crear backup manual"""
        log_user_action("CLICK", "quick_backup", "Dashboard")
        
        try:
            self.app.update_status("Creando backup...")
            
            result = backup_service.crear_backup_manual("backup_desde_dashboard")
            
            if result['success']:
                self.app.update_status("Backup creado exitosamente", "success")
                show_info_message(
                    "Backup Creado",
                    f"Backup manual creado exitosamente:\n{result['backup_info']['filename']}\n\nTamaño: {result['backup_info']['size_mb']:.2f} MB",
                    self.container
                )
            else:
                self.app.update_status("Error creando backup", "danger")
                
        except Exception as e:
            self.logger.error(f"Error creando backup rápido: {e}")
            self.app.update_status("Error creando backup", "danger")
            show_error_message("Error", f"Error creando backup: {str(e)}", self.container)
    
    def _show_all_alerts(self):
        """Muestra todas las alertas en una ventana (vista tabular y coloreada por severidad)"""
        log_user_action("CLICK", "show_all_alerts", "Dashboard")
        try:
            alertas_activas = micro_alertas.obtener_alertas_activas()

            if not alertas_activas:
                show_info_message("Sin Alertas", "No hay alertas activas en el sistema", self.container)
                return

            # Ventana
            win = ttk.Toplevel(self.app.root)
            win.title("Todas las Alertas - DelegInsumos")
            win.geometry("900x500")

            container = ttk.Frame(win, padding="10")
            container.pack(fill=BOTH, expand=True)

            # Treeview
            columns = ["Severidad", "Tipo", "Título", "Mensaje", "Fecha", "Acción"]
            tree = ttk.Treeview(container, columns=columns, show="headings", bootstyle="warning")
            for col in columns:
                tree.heading(col, text=col, anchor="center")
            tree.column("Severidad", width=100, stretch=False)
            tree.column("Tipo", width=140, stretch=False)
            tree.column("Título", width=220, stretch=True)
            tree.column("Mensaje", width=280, stretch=True)
            tree.column("Fecha", width=140, stretch=False)
            tree.column("Acción", width=70, stretch=False)

            # Estilos por severidad (fondos)
            try:
                tree.tag_configure('CRITICA', background='#ffebee', foreground='#b71c1c')  # rojo claro fuerte
                tree.tag_configure('ALTA', background='#fdecea', foreground='#d84315')      # rojo claro
                tree.tag_configure('MEDIA', background='#fffde7', foreground='#f57f17')     # amarillo claro
                tree.tag_configure('BAJA', background='#e3f2fd', foreground='#0d47a1')      # azul claro
            except Exception:
                pass

            # Scrollbars
            ysb = ttk.Scrollbar(container, orient=VERTICAL, command=tree.yview)
            xsb = ttk.Scrollbar(container, orient=HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

            tree.grid(row=0, column=0, sticky="nsew")
            ysb.grid(row=0, column=1, sticky="ns")
            xsb.grid(row=1, column=0, sticky="ew")
            container.rowconfigure(0, weight=1)
            container.columnconfigure(0, weight=1)

            # Mapeo severidad -> etiqueta/tag
            def sev_to_label_and_tag(sev: str):
                m = {
                    'CRITICAL': ("Crítica", "CRITICA"),
                    'HIGH': ("Alta", "ALTA"),
                    'MEDIUM': ("Media", "MEDIA"),
                    'LOW': ("Baja", "BAJA"),
                }
                return m.get(sev, ("Desconocida", "BAJA"))

            # Insertar filas
            for a in alertas_activas:
                # Etiqueta en español si viene desde servicio; si no, traducir
                label = a.get('severity_label')
                if not label:
                    label, tag = sev_to_label_and_tag(a.get('severity', 'LOW'))
                else:
                    # Normalizar tag desde etiqueta en español
                    norm = {'Crítica': 'CRITICA', 'Alta': 'ALTA', 'Media': 'MEDIA', 'Baja': 'BAJA'}
                    tag = norm.get(label, 'BAJA')

                try:
                    fecha = datetime.fromisoformat(a['created_at'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
                except Exception:
                    fecha = a.get('created_at', '')[:19].replace('T', ' ')

                tipo_disp = a.get('alert_type', '').replace('_', ' ').title()
                titulo = a.get('title', '')
                if len(titulo) > 40:
                    titulo = titulo[:37] + "..."
                mensaje = a.get('message', '')
                if len(mensaje) > 60:
                    mensaje = mensaje[:57] + "..."
                accion = "Sí" if a.get('action_required') else "No"

                tree.insert("", "end",
                            values=(label, tipo_disp, titulo, mensaje, fecha, accion),
                            tags=(tag,))

        except Exception as e:
            self.logger.error(f"Error mostrando todas las alertas: {e}")
            show_error_message("Error", f"Error cargando alertas: {str(e)}", self.container)
    
    
    def _check_alerts(self):
        """Verifica nuevas alertas manualmente"""
        log_user_action("CLICK", "check_alerts", "Dashboard")
        
        try:
            self.app.update_status("Verificando alertas...")
            
            result = micro_alertas.verificar_todas_las_alertas()
            total_new = result.get('total_new_alerts', 0)
            
            self._update_alerts_display()
            self._update_main_metrics()
            
            if total_new > 0:
                self.app.update_status(f"{total_new} nuevas alertas encontradas", "warning")
                show_info_message(
                    "Nuevas Alertas",
                    f"Se encontraron {total_new} nuevas alertas en el sistema",
                    self.container
                )
            else:
                self.app.update_status("Sin nuevas alertas", "success")
                show_info_message(
                    "Verificación Completa",
                    "No se encontraron nuevas alertas",
                    self.container
                )
                
        except Exception as e:
            self.logger.error(f"Error verificando alertas: {e}")
            self.app.update_status("Error verificando alertas", "danger")
            show_error_message("Error", f"Error verificando alertas: {str(e)}", self.container)