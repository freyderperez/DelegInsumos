"""
DelegInsumos - Tab de Reportes
Interfaz para generar, visualizar y gestionar reportes del sistema
"""

import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path
import os
import subprocess

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.widgets import DateEntry
except ImportError:
    print("Error: ttkbootstrap requerido")

from services.reportes_service import reportes_service
from utils.logger import LoggerMixin, log_user_action
from utils.helpers import (
    format_date, show_error_message, show_info_message, 
    ask_yes_no, select_save_file
)


class ReportesTab(LoggerMixin):
    """
    Tab para gestión completa de reportes del sistema
    """
    
    def __init__(self, parent, app_instance):
        super().__init__()
        self.parent = parent
        self.app = app_instance
        
        # Crear frame principal
        self.frame = ttk.Frame(parent, padding="15")
        
        # Variables de control
        self.reportes_list = []
        # Mapeo interno para almacenar datos completos por item del Treeview
        self._item_data = {}
        
        # Crear interfaz
        self._create_interface()
        
        # Cargar datos inicial
        self.refresh_data()
        
        self.logger.info("ReportesTab inicializado")
    
    def _create_interface(self):
        """Crea la interfaz del tab de reportes"""
        
        # Título del tab
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            title_frame,
            text="📄 Gestión de Reportes",
            font=("Helvetica", 16, "bold"),
            bootstyle="primary"
        ).pack(side=LEFT)
        
        ttk.Button(
            title_frame,
            text="🔄 Actualizar Lista",
            command=self.refresh_data,
            bootstyle="outline-primary"
        ).pack(side=RIGHT)
        
        # Panel principal dividido verticalmente
        main_paned = ttk.Panedwindow(self.frame, orient=VERTICAL)
        main_paned.pack(fill=BOTH, expand=True)
        
        # Panel superior: Generación de reportes
        self._create_generation_panel(main_paned)
        
        # Panel inferior: Lista de reportes existentes
        self._create_reports_list_panel(main_paned)
        
        self.logger.debug("Interfaz del tab de reportes creada")
    
    def _create_generation_panel(self, parent):
        """Crea el panel de generación de reportes"""
        
        generation_frame = ttk.Labelframe(
            parent,
            text="🎯 Generar Nuevos Reportes",
            padding="15",
            bootstyle="success"
        )
        parent.add(generation_frame, weight=1)
        
        # Grid para tipos de reportes
        reports_grid = ttk.Frame(generation_frame)
        reports_grid.pack(fill=X, pady=(0, 15))
        
        # Configurar grid
        for i in range(2):
            reports_grid.columnconfigure(i, weight=1)
        
        # Reportes de Inventario
        self._create_inventory_reports_section(reports_grid, 0, 0)
        
        # Reportes de Entregas
        self._create_deliveries_reports_section(reports_grid, 0, 1)
        
        # Reportes de Sistema
        self._create_system_reports_section(reports_grid, 1, 0)
        
        # Panel de configuración global
        self._create_global_config_section(reports_grid, 1, 1)
    
    def _create_inventory_reports_section(self, parent, row, col):
        """Crea sección de reportes de inventario"""
        
        inv_frame = ttk.Labelframe(
            parent,
            text="📦 Reportes de Inventario",
            padding="10"
        )
        inv_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Opciones
        self.include_charts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            inv_frame,
            text="Incluir gráficos",
            variable=self.include_charts_var,
            bootstyle="success-round-toggle"
        ).pack(anchor="w", pady=2)
        
        # Botones
        ttk.Button(
            inv_frame,
            text="📄 Generar PDF",
            command=self._generate_inventory_pdf,
            bootstyle="success",
            width=20
        ).pack(fill=X, pady=2)
        
        ttk.Button(
            inv_frame,
            text="📊 Generar Excel",
            command=self._generate_inventory_excel,
            bootstyle="success-outline",
            width=20
        ).pack(fill=X, pady=2)
    
    def _create_deliveries_reports_section(self, parent, row, col):
        """Crea sección de reportes de entregas"""
        
        del_frame = ttk.Labelframe(
            parent,
            text="📋 Reportes de Entregas",
            padding="10"
        )
        del_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Rango de fechas
        ttk.Label(del_frame, text="Fecha de Inicio:").pack(anchor="w")
        self.start_date = DateEntry(
            del_frame,
            bootstyle="primary",
            startdate=date.today() - timedelta(days=30)
        )
        self.start_date.pack(fill=X, pady=(2, 5))
        
        ttk.Label(del_frame, text="Fecha de Fin:").pack(anchor="w")
        self.end_date = DateEntry(
            del_frame,
            bootstyle="primary",
            startdate=date.today()
        )
        self.end_date.pack(fill=X, pady=(2, 10))
        
        # Botones
        ttk.Button(
            del_frame,
            text="📄 Reporte del Período",
            command=self._generate_deliveries_pdf,
            bootstyle="info",
            width=20
        ).pack(fill=X, pady=2)
    
    def _create_system_reports_section(self, parent, row, col):
        """Crea sección de reportes del sistema"""
        
        sys_frame = ttk.Labelframe(
            parent,
            text="🛠️ Reportes del Sistema",
            padding="10"
        )
        sys_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Botones de reportes del sistema
        ttk.Button(
            sys_frame,
            text="⚠️ Reporte de Alertas",
            command=self._generate_alerts_pdf,
            bootstyle="warning",
            width=20
        ).pack(fill=X, pady=2)
        
        ttk.Button(
            sys_frame,
            text="👥 Reporte de Empleados",
            command=self._generate_employees_pdf,
            bootstyle="secondary",
            width=20
        ).pack(fill=X, pady=2)
        
    
    def _create_global_config_section(self, parent, row, col):
        """Crea sección de configuración global"""
        
        config_frame = ttk.Labelframe(
            parent,
            text="⚙️ Configuración",
            padding="10"
        )
        config_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Formato de salida por defecto
        ttk.Label(config_frame, text="Formato por defecto:").pack(anchor="w")
        
        self.format_var = tk.StringVar(value="PDF")
        format_combo = ttk.Combobox(
            config_frame,
            textvariable=self.format_var,
            values=["PDF", "Excel"],
            state="readonly",
            bootstyle="primary"
        )
        format_combo.pack(fill=X, pady=(2, 10))
        
        # Botones de gestión
        ttk.Button(
            config_frame,
            text="🧹 Limpiar Reportes Antiguos",
            command=self._cleanup_old_reports,
            bootstyle="danger-outline",
            width=20
        ).pack(fill=X, pady=2)
        
        ttk.Button(
            config_frame,
            text="📁 Abrir Directorio",
            command=self._open_reports_directory,
            bootstyle="secondary-outline",
            width=20
        ).pack(fill=X, pady=2)
    
    def _create_reports_list_panel(self, parent):
        """Crea el panel de lista de reportes existentes"""
        
        list_frame = ttk.Labelframe(
            parent,
            text="📚 Reportes Generados",
            padding="15",
            bootstyle="info"
        )
        parent.add(list_frame, weight=2)
        
        # Toolbar
        toolbar_frame = ttk.Frame(list_frame)
        toolbar_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(
            toolbar_frame,
            text="Reportes disponibles:",
            font=("Helvetica", 10, "bold")
        ).pack(side=LEFT)
        
        # Estadísticas rápidas
        self.reports_stats_label = ttk.Label(
            toolbar_frame,
            text="Cargando...",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        self.reports_stats_label.pack(side=RIGHT)
        
        # Treeview para lista de reportes
        list_content = ttk.Frame(list_frame)
        list_content.pack(fill=BOTH, expand=True)
        
        columns = ["Tipo", "Formato", "Tamaño", "Fecha Creación", "Fecha Modificación"]
        self.reports_tree = ttk.Treeview(
            list_content,
            columns=columns,
            show="tree headings",
            bootstyle="info"
        )
        
        # Configurar columnas
        self.reports_tree.heading("#0", text="Nombre Archivo", anchor="w")
        self.reports_tree.column("#0", width=200, stretch=True)
        
        for col in columns:
            self.reports_tree.heading(col, text=col, anchor="center")
        
        self.reports_tree.column("Tipo", width=80, stretch=False)
        self.reports_tree.column("Formato", width=60, stretch=False)
        self.reports_tree.column("Tamaño", width=70, stretch=False)
        self.reports_tree.column("Fecha Creación", width=120, stretch=False)
        self.reports_tree.column("Fecha Modificación", width=120, stretch=False)
        
        # Scrollbar
        reports_scrollbar = ttk.Scrollbar(list_content, orient=VERTICAL, command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=reports_scrollbar.set)
        
        # Pack
        self.reports_tree.pack(side=LEFT, fill=BOTH, expand=True)
        reports_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Menú contextual para reportes
        self._create_context_menu()
        
        # Botones de acción
        actions_frame = ttk.Frame(list_frame)
        actions_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Button(
            actions_frame,
            text="👁️ Abrir Reporte",
            command=self._open_selected_report,
            bootstyle="primary"
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            actions_frame,
            text="💾 Guardar Como...",
            command=self._save_report_as,
            bootstyle="secondary"
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            actions_frame,
            text="🗑️ Eliminar",
            command=self._delete_selected_report,
            bootstyle="danger-outline"
        ).pack(side=LEFT, padx=(0, 5))
        
        # Estadísticas de reportes
        self.stats_text = tk.Text(
            actions_frame,
            height=3,
            width=40,
            wrap=tk.WORD
        )
        self.stats_text.pack(side=RIGHT, fill=X, expand=True, padx=(10, 0))
    
    def _create_context_menu(self):
        """Crea menú contextual para la lista de reportes"""
        
        self.context_menu = tk.Menu(self.reports_tree, tearoff=0)
        self.context_menu.add_command(label="👁️ Abrir", command=self._open_selected_report)
        self.context_menu.add_command(label="💾 Guardar como...", command=self._save_report_as)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Eliminar", command=self._delete_selected_report)
        
        # Bind del menú contextual
        self.reports_tree.bind("<Button-3>", self._show_context_menu)  # Click derecho
        self.reports_tree.bind("<Double-1>", lambda e: self._open_selected_report())  # Doble click
    
    def _show_context_menu(self, event):
        """Muestra el menú contextual"""
        # Seleccionar item bajo el cursor
        item_id = self.reports_tree.identify_row(event.y)
        if item_id:
            self.reports_tree.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)
    
    def refresh_data(self):
        """Actualiza la lista de reportes y estadísticas"""
        try:
            self.logger.debug("Actualizando datos de reportes")
            
            # Obtener lista de reportes
            self.reportes_list = reportes_service.listar_reportes_disponibles()
            
            # Obtener estadísticas
            stats = reportes_service.obtener_estadisticas_reportes()
            
            # Actualizar UI
            self._update_reports_tree()
            self._update_stats_display(stats)
            
            self.logger.info("Datos de reportes actualizados")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de reportes: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error cargando reportes", "danger")
    
    def _update_reports_tree(self):
        """Actualiza el árbol de reportes"""
        try:
            # Limpiar tree
            for item in self.reports_tree.get_children():
                self.reports_tree.delete(item)
            
            # Resetear almacenamiento auxiliar
            self._item_data = {}
            
            # Agregar reportes al tree (con zebra)
            for idx, reporte in enumerate(self.reportes_list):
                # Formatear fechas
                fecha_creacion = datetime.fromisoformat(reporte['created_at']).strftime('%d/%m/%Y %H:%M')
                fecha_modificacion = datetime.fromisoformat(reporte['modified_at']).strftime('%d/%m/%Y %H:%M')
                
                # Tag zebra
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                
                # Agregar item
                item_id = self.reports_tree.insert(
                    "", "end",
                    text=f"{reporte['icon']} {reporte['filename']}",
                    values=(
                        reporte['type'],
                        reporte['format'],
                        f"{reporte['size_mb']:.2f} MB",
                        fecha_creacion,
                        fecha_modificacion
                    ),
                    tags=(zebra_tag,)
                )
                
                # Guardar datos completos en un mapa auxiliar
                self._item_data[item_id] = reporte
            
            # Estilos zebra
            try:
                self.reports_tree.tag_configure("even", background="#F7FAFF")
                self.reports_tree.tag_configure("odd", background="#EDF3FF")
            except Exception:
                pass
            
            # Actualizar conteo
            total_reportes = len(self.reportes_list)
            self.reports_stats_label.config(text=f"Total: {total_reportes} reportes")
            
        except Exception as e:
            self.logger.error(f"Error actualizando tree de reportes: {e}")
    
    def _update_stats_display(self, stats: Dict[str, Any]):
        """Actualiza la visualización de estadísticas"""
        try:
            # Limpiar texto
            self.stats_text.delete("1.0", tk.END)
            
            # Formatear estadísticas
            stats_content = f"ESTADÍSTICAS DE REPORTES\n"
            stats_content += f"{'=' * 30}\n\n"
            stats_content += f"Total reportes: {stats.get('total_reportes', 0)}\n"
            stats_content += f"Tamaño total: {stats.get('total_size_mb', 0):.2f} MB\n\n"
            
            # Por tipo
            if 'by_type' in stats and stats['by_type']:
                stats_content += "Por tipo:\n"
                for tipo, cantidad in stats['by_type'].items():
                    stats_content += f"  • {tipo}: {cantidad}\n"
                stats_content += "\n"
            
            # Por formato
            if 'by_format' in stats and stats['by_format']:
                stats_content += "Por formato:\n"
                for formato, cantidad in stats['by_format'].items():
                    stats_content += f"  • {formato}: {cantidad}\n"
            
            # Insertar contenido
            self.stats_text.insert("1.0", stats_content)
            self.stats_text.config(state="disabled")
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas: {e}")
    
    def _get_date_from_dateentry(self, widget) -> date:
        """
        Obtiene un objeto date desde un DateEntry de ttkbootstrap de forma segura.
        Soporta múltiples APIs (dateobj, get_date) y realiza parseo de texto como respaldo.
        """
        # 1) API típica de ttkbootstrap: propiedad dateobj
        try:
            val = getattr(widget, "dateobj", None)
            if isinstance(val, date):
                return val
        except Exception:
            pass

        # 2) Algunos builds exponen get_date()
        try:
            return widget.get_date()
        except Exception:
            pass

        # 3) Respaldo: leer texto y parsear
        text = ""
        try:
            if hasattr(widget, "entry"):
                text = widget.entry.get().strip()
            else:
                # Fallback para widgets con interfaz tipo Combobox
                text = widget.get().strip()
        except Exception:
            text = ""

        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except Exception:
                continue

        # 4) Último recurso: fecha actual
        return date.today()
    # Manejadores de eventos para generación de reportes
    
    def _generate_inventory_pdf(self):
        """Genera reporte de inventario en PDF"""
        log_user_action("CLICK", "generate_inventory_pdf", "ReportesTab")
        
        try:
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Generando reporte de inventario PDF...")
            
            # Generar reporte
            result = reportes_service.generar_reporte_inventario_pdf(
                incluir_graficos=self.include_charts_var.get()
            )
            
            if result['success']:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Reporte PDF generado", "success")
                
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de inventario creado:\n\n"
                    f"📄 {result['filename']}\n"
                    f"📁 Tamaño: {result['size_mb']} MB\n"
                    f"📦 Insumos incluidos: {result['total_insumos']}\n\n"
                    f"¿Desea abrir el reporte?",
                    self.frame
                )
                
                # Preguntar si abrir el archivo
                if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                    self._open_file(result['filepath'])
                
                # Actualizar lista
                self.refresh_data()
                
            else:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Error generando reporte", "danger")
                show_error_message("Error", "No se pudo generar el reporte PDF", self.frame)
            
        except Exception as e:
            self.logger.error(f"Error generando reporte inventario PDF: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.frame)
    
    def _generate_inventory_excel(self):
        """Genera reporte de inventario en Excel"""
        log_user_action("CLICK", "generate_inventory_excel", "ReportesTab")
        
        try:
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Generando reporte de inventario Excel...")
            
            result = reportes_service.generar_reporte_inventario_excel()
            
            if result['success']:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Reporte Excel generado", "success")
                
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de inventario Excel creado:\n\n"
                    f"📊 {result['filename']}\n"
                    f"📁 Tamaño: {result['size_mb']} MB\n"
                    f"📄 Hojas: {', '.join(result['sheets_created'])}\n\n"
                    f"¿Desea abrir el reporte?",
                    self.frame
                )
                
                if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                    self._open_file(result['filepath'])
                
                self.refresh_data()
                
        except Exception as e:
            self.logger.error(f"Error generando reporte inventario Excel: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.frame)
    
    def _generate_deliveries_pdf(self):
        """Genera reporte de entregas en PDF"""
        log_user_action("CLICK", "generate_deliveries_pdf", "ReportesTab")
        
        try:
            # Obtener fechas seleccionadas
            fecha_inicio = self._get_date_from_dateentry(self.start_date)
            fecha_fin = self._get_date_from_dateentry(self.end_date)
            
            # Validar rango de fechas
            if fecha_inicio > fecha_fin:
                show_error_message(
                    "Error de Fechas",
                    "La fecha de inicio no puede ser mayor a la fecha de fin",
                    self.frame
                )
                return
            
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Generando reporte de entregas...")
            
            result = reportes_service.generar_reporte_entregas_pdf(fecha_inicio, fecha_fin)
            
            if result['success']:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Reporte de entregas generado", "success")
                
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de entregas creado:\n\n"
                    f"📋 {result['filename']}\n"
                    f"📅 Período: {fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}\n"
                    f"📄 Entregas incluidas: {result['total_entregas']}\n\n"
                    f"¿Desea abrir el reporte?",
                    self.frame
                )
                
                if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                    self._open_file(result['filepath'])
                
                self.refresh_data()
                
        except Exception as e:
            self.logger.error(f"Error generando reporte entregas: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.frame)
    
    def _generate_alerts_pdf(self):
        """Genera reporte de alertas en PDF"""
        log_user_action("CLICK", "generate_alerts_pdf", "ReportesTab")
        
        try:
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Generando reporte de alertas...")
            
            result = reportes_service.generar_reporte_alertas_pdf()
            
            if result['success']:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Reporte de alertas generado", "success")
                
                show_info_message(
                    "Reporte Generado",
                    f"Reporte de alertas creado:\n\n"
                    f"⚠️ {result['filename']}\n"
                    f"📊 Alertas incluidas: {result['total_alertas']}\n"
                    f"🔴 Críticas: {result['alertas_criticas']}\n\n"
                    f"¿Desea abrir el reporte?",
                    self.frame
                )
                
                if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                    self._open_file(result['filepath'])
                
                self.refresh_data()
                
        except Exception as e:
            self.logger.error(f"Error generando reporte alertas: {e}")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.frame)
    
    def _generate_employees_pdf(self):
        """Genera reporte de empleados en PDF o Excel según formato seleccionado"""
        log_user_action("CLICK", "generate_employees_report", "ReportesTab")
        try:
            fmt = (self.format_var.get() or "PDF").upper()
            if hasattr(self.app, 'update_status'):
                self.app.update_status(f"Generando reporte de empleados {fmt}...")
            if fmt == "EXCEL":
                result = reportes_service.generar_reporte_empleados_excel()
                if result.get('success'):
                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Reporte de empleados Excel generado", "success")
                    show_info_message(
                        "Reporte de Empleados",
                        f"Reporte generado:\n\n"
                        f"📊 {result['filename']}\n"
                        f"📁 Tamaño: {result['size_mb']} MB\n"
                        f"👥 Empleados: {result.get('total_empleados', 0)}\n\n"
                        f"¿Desea abrir el reporte?",
                        self.frame
                    )
                    if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                        self._open_file(result['filepath'])
                    self.refresh_data()
                else:
                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Error generando reporte", "danger")
                    show_error_message("Error", "No se pudo generar el reporte de empleados en Excel", self.frame)
            else:
                result = reportes_service.generar_reporte_empleados_pdf()
                if result.get('success'):
                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Reporte de empleados PDF generado", "success")
                    show_info_message(
                        "Reporte de Empleados",
                        f"Reporte generado:\n\n"
                        f"📄 {result['filename']}\n"
                        f"📁 Tamaño: {result['size_mb']} MB\n"
                        f"👥 Empleados: {result.get('total_empleados', 0)}\n\n"
                        f"¿Desea abrir el reporte?",
                        self.frame
                    )
                    if ask_yes_no("Abrir Reporte", "¿Desea abrir el reporte generado?", self.frame):
                        self._open_file(result['filepath'])
                    self.refresh_data()
                else:
                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Error generando reporte", "danger")
                    show_error_message("Error", "No se pudo generar el reporte de empleados en PDF", self.frame)
        except Exception as e:
            self.logger.error(f"Error generando reporte de empleados: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error generando reporte", "danger")
            show_error_message("Error", f"Error generando reporte: {str(e)}", self.frame)
    
    
    def _open_selected_report(self):
        """Abre el reporte seleccionado"""
        selection = self.reports_tree.selection()
        
        if not selection:
            show_info_message("Sin Selección", "Por favor seleccione un reporte para abrir", self.frame)
            return
        
        try:
            # Obtener ruta del archivo desde almacenamiento auxiliar
            selected_item = selection[0]
            data = self._item_data.get(selected_item, {})
            filepath = data.get("filepath")
            
            if not filepath:
                show_error_message("Error", "No se pudo obtener la ruta del archivo", self.frame)
                return
            
            log_user_action("OPEN_REPORT", "open_selected", f"Archivo: {Path(filepath).name}")
            
            self._open_file(filepath)
            
        except Exception as e:
            self.logger.error(f"Error abriendo reporte: {e}")
            show_error_message("Error", f"Error abriendo reporte: {str(e)}", self.frame)
    
    def _open_file(self, filepath: str):
        """Abre un archivo con la aplicación por defecto del sistema"""
        try:
            if not Path(filepath).exists():
                show_error_message("Error", "El archivo no existe", self.frame)
                return
            
            # Abrir con aplicación por defecto según el SO
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
            elif os.name == 'posix':  # macOS y Linux
                subprocess.run(['open', filepath] if sys.platform == 'darwin' else ['xdg-open', filepath])
            
            self.logger.info(f"Archivo abierto: {Path(filepath).name}")
            
        except Exception as e:
            self.logger.error(f"Error abriendo archivo {filepath}: {e}")
            show_error_message("Error", f"Error abriendo archivo: {str(e)}", self.frame)
    
    def _save_report_as(self):
        """Guarda una copia del reporte seleccionado"""
        selection = self.reports_tree.selection()
        
        if not selection:
            show_info_message("Sin Selección", "Por favor seleccione un reporte para guardar", self.frame)
            return
        
        try:
            # Obtener información del archivo seleccionado
            selected_item = selection[0]
            data = self._item_data.get(selected_item, {})
            filepath = data.get("filepath")
            filename = self.reports_tree.item(selected_item, "text").split(" ", 1)[1]  # Remover emoji
            
            # Obtener extensión
            file_ext = Path(filepath).suffix
            
            # Tipos de archivo para el diálogo
            if file_ext == '.pdf':
                file_types = [("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
            elif file_ext == '.xlsx':
                file_types = [("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
            else:
                file_types = [("Todos los archivos", "*.*")]
            
            # Diálogo para guardar
            destination = select_save_file(
                "Guardar Reporte Como",
                filename,
                file_types,
                self.frame
            )
            
            if destination:
                # Copiar archivo
                import shutil
                shutil.copy2(filepath, destination)
                
                log_user_action("SAVE_REPORT_AS", "copy_report", f"Destino: {Path(destination).name}")
                
                show_info_message(
                    "Reporte Guardado",
                    f"Reporte guardado exitosamente en:\n{destination}",
                    self.frame
                )
            
        except Exception as e:
            self.logger.error(f"Error guardando reporte como: {e}")
            show_error_message("Error", f"Error guardando archivo: {str(e)}", self.frame)
    
    def _delete_selected_report(self):
        """Elimina el reporte seleccionado"""
        selection = self.reports_tree.selection()
        
        if not selection:
            show_info_message("Sin Selección", "Por favor seleccione un reporte para eliminar", self.frame)
            return
        
        try:
            # Obtener información del archivo
            selected_item = selection[0]
            filename = self.reports_tree.item(selected_item, "text").split(" ", 1)[1]  # Remover emoji
            
            # Confirmar eliminación
            if ask_yes_no(
                "Confirmar Eliminación",
                f"¿Está seguro que desea eliminar el reporte?\n\n{filename}\n\nEsta acción no se puede deshacer.",
                self.frame
            ):
                # Eliminar archivo
                result = reportes_service.eliminar_reporte(filename)
                
                if result['success']:
                    show_info_message("Reporte Eliminado", result['message'], self.frame)
                    self.refresh_data()  # Actualizar lista
                    
                    log_user_action("DELETE_REPORT", "file_deleted", f"Archivo: {filename}")
                else:
                    show_error_message("Error", result['message'], self.frame)
            
        except Exception as e:
            self.logger.error(f"Error eliminando reporte: {e}")
            show_error_message("Error", f"Error eliminando reporte: {str(e)}", self.frame)
    
    def _cleanup_old_reports(self):
        """Limpia reportes antiguos"""
        log_user_action("CLICK", "cleanup_old_reports", "ReportesTab")
        
        if ask_yes_no(
            "Confirmar Limpieza",
            "¿Desea eliminar reportes anteriores a 30 días?\n\nEsta acción no se puede deshacer.",
            self.frame
        ):
            try:
                result = reportes_service.limpiar_reportes_antiguos(30)
                
                if result['success']:
                    show_info_message(
                        "Limpieza Completada",
                        f"Se eliminaron {result['deleted_count']} reportes antiguos",
                        self.frame
                    )
                    self.refresh_data()
                else:
                    show_error_message("Error", result['message'], self.frame)
                
            except Exception as e:
                self.logger.error(f"Error limpiando reportes: {e}")
                show_error_message("Error", f"Error limpiando reportes: {str(e)}", self.frame)
    
    def _open_reports_directory(self):
        """Abre el directorio de reportes en el explorador"""
        log_user_action("CLICK", "open_reports_directory", "ReportesTab")
        
        try:
            reports_dir = reportes_service.output_dir
            
            if not reports_dir.exists():
                reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Abrir directorio según el SO
            if os.name == 'nt':  # Windows
                os.startfile(str(reports_dir))
            elif os.name == 'posix':  # macOS y Linux
                subprocess.run(['open', str(reports_dir)] if sys.platform == 'darwin' else ['xdg-open', str(reports_dir)])
            
            self.logger.info(f"Directorio de reportes abierto: {reports_dir}")
            
        except Exception as e:
            self.logger.error(f"Error abriendo directorio de reportes: {e}")
            show_error_message("Error", f"Error abriendo directorio: {str(e)}", self.frame)