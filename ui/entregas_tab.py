"""
DelegInsumos - Tab de Entregas
Interfaz para registro y gestión de entregas de insumos a empleados
"""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.widgets import DateEntry
    from ttkbootstrap.scrolled import ScrolledFrame
except ImportError:
    print("Error: ttkbootstrap requerido")

from services.micro_entregas import micro_entregas
from services.micro_empleados import micro_empleados
from services.micro_insumos import micro_insumos
from models.entrega import Entrega
from utils.logger import LoggerMixin, log_user_action
from utils.helpers import (
    format_date, show_error_message, show_info_message,
    ask_yes_no
)
from utils.validators import validate_entrega_data
from exceptions.custom_exceptions import ValidationException, BusinessLogicException, InsufficientStockException


class EntregasTab(LoggerMixin):
    """
    Tab para gestión de entregas de insumos
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
        self.entregas_list = []
        self.empleados_disponibles = []
        self.insumos_disponibles = []
        self.selected_entrega = None
        # Mapeo interno para almacenar datos completos por item del Treeview
        self._item_data = {}

        # Variables de formulario
        self._init_form_variables()

        # Crear interfaz
        self._create_interface()

        # Cargar datos inicial
        self.refresh_data()

        self.logger.info("EntregasTab inicializado")
    
    def _init_form_variables(self):
        """Inicializa las variables del formulario"""
        self.form_id = tk.StringVar()
        self.form_empleado_id = tk.IntVar()
        self.form_empleado_display = tk.StringVar()
        self.form_insumo_id = tk.IntVar()
        self.form_insumo_display = tk.StringVar()
        self.form_cantidad = tk.IntVar(value=1)
        self.form_observaciones = tk.StringVar()
        self.form_entregado_por = tk.StringVar()
        
        # Variables de filtros
        self.filter_empleado = tk.StringVar()
        self.filter_insumo = tk.StringVar()
        self.filter_periodo = tk.StringVar()
        
        # Variables de estado
        self.stock_disponible = tk.StringVar()
        self.stock_warning = tk.StringVar()
    
    def _create_interface(self):
        """Crea la interfaz del tab de entregas"""
        
        # Título del tab
        title_frame = ttk.Frame(self.container)
        title_frame.pack(fill=X, pady=(0, 20))

        ttk.Label(
            title_frame,
            text="📋 Registro de Entregas",
            font=("Helvetica", 16, "bold"),
            bootstyle="primary"
        ).pack(side=LEFT)

        ttk.Button(
            title_frame,
            text="🔄 Actualizar",
            command=lambda: self.refresh_data(quick=True),
            bootstyle="outline-primary"
        ).pack(side=RIGHT, padx=(5, 0))

        ttk.Button(
            title_frame,
            text="➕ Nueva Entrega",
            command=self.show_add_form,
            bootstyle="success"
        ).pack(side=RIGHT)

        # Panel principal dividido
        main_paned = ttk.Panedwindow(self.container, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True)
        
        # Panel izquierdo: Lista de entregas
        self._create_list_panel(main_paned)
        
        # Panel derecho: Formulario
        self._create_form_panel(main_paned)
        
        self.logger.debug("Interfaz del tab de entregas creada")
    
    def _create_list_panel(self, parent):
        """Crea el panel de lista de entregas"""
        
        list_frame = ttk.Labelframe(
            parent,
            text="📋 Historial de Entregas",
            padding="15"
        )
        parent.add(list_frame, weight=2)
        
        # Panel de filtros
        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill=X, pady=(0, 15))
        
        # Filtros en dos filas
        filter_row1 = ttk.Frame(filter_frame)
        filter_row1.pack(fill=X, pady=(0, 5))
        
        # Filtro por empleado
        ttk.Label(filter_row1, text="Empleado:").pack(side=LEFT)
        self.filter_empleado_combo = ttk.Combobox(
            filter_row1,
            textvariable=self.filter_empleado,
            values=["Todos"],
            state="readonly",
            width=25,
            bootstyle="primary"
        )
        self.filter_empleado_combo.pack(side=LEFT, padx=(5, 10))
        self.filter_empleado_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        
        # Filtro por insumo
        ttk.Label(filter_row1, text="Insumo:").pack(side=LEFT)
        self.filter_insumo_combo = ttk.Combobox(
            filter_row1,
            textvariable=self.filter_insumo,
            values=["Todos"],
            state="readonly",
            width=25,
            bootstyle="primary"
        )
        self.filter_insumo_combo.pack(side=LEFT, padx=(5, 10))
        self.filter_insumo_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        
        # Segunda fila de filtros
        filter_row2 = ttk.Frame(filter_frame)
        filter_row2.pack(fill=X)
        
        # Filtro por período
        ttk.Label(filter_row2, text="Período:").pack(side=LEFT)
        periodo_combo = ttk.Combobox(
            filter_row2,
            textvariable=self.filter_periodo,
            values=["Todas", "Hoy", "Últimos 7 días", "Últimos 30 días", "Este mes"],
            state="readonly",
            width=15,
            bootstyle="primary"
        )
        periodo_combo.pack(side=LEFT, padx=(5, 10))
        periodo_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        periodo_combo.current(0)
        
        # Botón limpiar filtros
        ttk.Button(
            filter_row2,
            text="🧹 Limpiar Filtros",
            command=self._clear_filters,
            bootstyle="outline-secondary",
            width=15
        ).pack(side=RIGHT)
        
        # Treeview para lista de entregas
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=BOTH, expand=True)
        
        columns = ["Fecha", "Empleado", "Insumo", "Cantidad", "Entregado Por"]
        self.entregas_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            bootstyle="primary"
        )
        
        # Configurar columnas
        self.entregas_tree.heading("#0", text="Código", anchor="center")
        self.entregas_tree.column("#0", width=120, stretch=False)
        
        column_configs = [
            ("Fecha", 120, False),
            ("Empleado", 180, True),
            ("Insumo", 180, True),
            ("Cantidad", 80, False),
            ("Entregado Por", 120, True)
        ]
        
        for col, (title, width, stretch) in zip(columns, column_configs):
            self.entregas_tree.heading(col, text=title, anchor="center")
            self.entregas_tree.column(col, width=width, stretch=stretch)
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.entregas_tree.yview)
        x_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.entregas_tree.xview)
        self.entregas_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid layout
        self.entregas_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Eventos del tree
        self.entregas_tree.bind("<<TreeviewSelect>>", self._on_entrega_selected)
        self.entregas_tree.bind("<Double-1>", lambda e: self._view_entrega_details())
        
        # Frame de estadísticas
        stats_frame = ttk.Frame(list_frame)
        stats_frame.pack(fill=X, pady=(10, 0))
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="Cargando estadísticas...",
            font=("Helvetica", 9),
            bootstyle="info"
        )
        self.stats_label.pack(side=LEFT)
        
        # Botón para eliminar la entrega seleccionada del historial
        ttk.Button(
            stats_frame,
            text="🗑️ Eliminar Seleccionada",
            command=self._delete_selected_entrega,
            bootstyle="danger-outline",
            width=22
        ).pack(side=RIGHT, padx=(5, 5))
        
        self.period_stats_label = ttk.Label(
            stats_frame,
            text="",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        self.period_stats_label.pack(side=RIGHT)
    
    def _create_form_panel(self, parent):
        """Crea el panel del formulario de entregas"""
        
        form_frame = ttk.Labelframe(
            parent,
            text="📝 Nueva Entrega",
            padding="15"
        )
        parent.add(form_frame, weight=1)
        
        # Modo del formulario
        mode_frame = ttk.Frame(form_frame)
        mode_frame.pack(fill=X, pady=(0, 15))
        
        self.form_mode_label = ttk.Label(
            mode_frame,
            text="Nueva Entrega",
            font=("Helvetica", 12, "bold"),
            bootstyle="success"
        )
        self.form_mode_label.pack(side=LEFT)
        
        # Botones de control
        self.form_clear_btn = ttk.Button(
            mode_frame,
            text="🗑️ Limpiar",
            command=self._clear_form,
            bootstyle="outline-secondary",
            width=12
        )
        self.form_clear_btn.pack(side=RIGHT, padx=(5, 0))
        
        self.form_cancel_btn = ttk.Button(
            mode_frame,
            text="❌ Cancelar",
            command=self._cancel_form,
            bootstyle="outline-danger",
            width=12
        )
        self.form_cancel_btn.pack(side=RIGHT)
        
        # Campos del formulario
        self._create_delivery_form_fields(form_frame)
        
        # Panel de validación
        self._create_validation_panel(form_frame)
        
        # Botones de acción
        self._create_delivery_form_actions(form_frame)
    
    def _create_delivery_form_fields(self, parent):
        """Crea los campos del formulario de entrega"""
        
        fields_frame = ttk.Frame(parent)
        fields_frame.pack(fill=X, pady=(0, 15))
        
        # Selección de empleado
        ttk.Label(fields_frame, text="* Empleado:").grid(row=0, column=0, sticky="w", pady=2)
        
        empleado_frame = ttk.Frame(fields_frame)
        empleado_frame.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        self.form_empleado_combo = ttk.Combobox(
            empleado_frame,
            textvariable=self.form_empleado_display,
            values=[],
            state="normal",
            bootstyle="primary"
        )
        self.form_empleado_combo.pack(side=LEFT, fill=X, expand=True)
        self.form_empleado_combo.bind("<<ComboboxSelected>>", self._on_empleado_selected)
        
        # Filtro dinámico al escribir para sugerir empleados
        self.form_empleado_combo.bind("<KeyRelease>", self._on_empleado_text_changed)
        
        # Selección de insumo
        ttk.Label(fields_frame, text="* Insumo:").grid(row=1, column=0, sticky="w", pady=2)
        
        insumo_frame = ttk.Frame(fields_frame)
        insumo_frame.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        self.form_insumo_combo = ttk.Combobox(
            insumo_frame,
            textvariable=self.form_insumo_display,
            values=[],
            state="normal",
            bootstyle="primary"
        )
        self.form_insumo_combo.pack(side=LEFT, fill=X, expand=True)
        self.form_insumo_combo.bind("<<ComboboxSelected>>", self._on_insumo_selected)
        
        # Filtro dinámico al escribir para sugerir insumos
        self.form_insumo_combo.bind("<KeyRelease>", self._on_insumo_text_changed)
        
        # Información de stock disponible
        self.stock_info_label = ttk.Label(
            insumo_frame,
            textvariable=self.stock_disponible,
            font=("Helvetica", 8),
            bootstyle="info"
        )
        self.stock_info_label.pack(side=RIGHT, padx=(5, 0))
        
        # Cantidad a entregar
        ttk.Label(fields_frame, text="* Cantidad:").grid(row=2, column=0, sticky="w", pady=2)
        
        cantidad_frame = ttk.Frame(fields_frame)
        cantidad_frame.grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        self.form_cantidad_spinbox = ttk.Spinbox(
            cantidad_frame,
            from_=1,
            to=9999,
            textvariable=self.form_cantidad,
            bootstyle="success",
            width=10
        )
        self.form_cantidad_spinbox.pack(side=LEFT)
        self.form_cantidad_spinbox.bind("<KeyRelease>", self._validate_stock_availability)
        self.form_cantidad_spinbox.bind("<<Modified>>", self._validate_stock_availability)
        
        # Warning de stock
        self.stock_warning_label = ttk.Label(
            cantidad_frame,
            textvariable=self.stock_warning,
            font=("Helvetica", 8),
            bootstyle="warning"
        )
        self.stock_warning_label.pack(side=LEFT, padx=(10, 0))
        
        # Observaciones
        ttk.Label(fields_frame, text="Observaciones:").grid(row=3, column=0, sticky="nw", pady=2)
        
        obs_frame = ttk.Frame(fields_frame)
        obs_frame.grid(row=3, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        self.form_observaciones_text = tk.Text(
            obs_frame,
            height=3,
            wrap=tk.WORD,
            font=("Helvetica", 9)
        )
        self.form_observaciones_text.pack(fill=BOTH, expand=True)
        
        # Bind para actualizar variable
        self.form_observaciones_text.bind("<KeyRelease>", self._update_observaciones_var)
        
        # Entregado por
        ttk.Label(fields_frame, text="Entregado por:").grid(row=4, column=0, sticky="w", pady=2)
        self.form_entregado_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_entregado_por,
            bootstyle="secondary"
        )
        self.form_entregado_entry.grid(row=4, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Configurar grid
        fields_frame.columnconfigure(1, weight=1)
        obs_frame.columnconfigure(0, weight=1)
        
        # Campos obligatorios
        ttk.Label(
            fields_frame,
            text="* Campos obligatorios",
            font=("Helvetica", 8),
            bootstyle="danger"
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
    
    def _create_validation_panel(self, parent):
        """""Crea panel de validación de la entrega"""
        
        validation_frame = ttk.Labelframe(
            parent,
            text="✅ Validación de Entrega",
            padding="10"
        )
        validation_frame.pack(fill=X, pady=(10, 15))
        
        self.validation_text = tk.Text(
            validation_frame,
            height=4,
            wrap=tk.WORD,
            font=("Helvetica", 9),
            bg="#F5F5F5"
        )
        self.validation_text.pack(fill=BOTH, expand=True)
        self.validation_text.config(state="disabled")
        
        # Inicialmente mostrar mensaje de ayuda
        self._show_validation_help()
    
    def _create_delivery_form_actions(self, parent):
        """Crea los botones de acción del formulario"""
        
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=X)
        
        # Botón guardar entrega
        self.save_delivery_btn = ttk.Button(
            actions_frame,
            text="💾 Registrar Entrega",
            command=self._save_entrega,
            bootstyle="success",
            width=20
        )
        self.save_delivery_btn.pack(side=LEFT, padx=(0, 5))
        
        # Botón validar antes de guardar
        self.validate_btn = ttk.Button(
            actions_frame,
            text="✅ Validar Datos",
            command=self._validate_form_data,
            bootstyle="info-outline",
            width=15
        )
        self.validate_btn.pack(side=LEFT, padx=(0, 5))
        
        # Estado de validación
        self.validation_status_label = ttk.Label(
            actions_frame,
            text="",
            font=("Helvetica", 9)
        )
        self.validation_status_label.pack(side=RIGHT)
    
    def refresh_data(self, quick: bool = False):
        """Actualiza la lista de entregas y datos relacionados.
        
        Args:
            quick: Si True, recarga solo la lista de entregas y estadísticas (sin recargar combos).
        """
        try:
            self.logger.debug(f"Actualizando datos de entregas (quick={quick})")
            
            # Obtener entregas con límite para rendimiento
            result = micro_entregas.listar_entregas(limit=200, include_stats=True)
            self.entregas_list = result.get('entregas', [])
            
            # Cargar empleados e insumos solo cuando no es actualización rápida
            if not quick:
                self._load_available_employees()
                self._load_available_insumos()
            
            # Aplicar filtros actuales
            self._apply_filters()
            
            # Actualizar estadísticas
            self._update_statistics(result)
            
            if hasattr(self.app, 'update_status'):
                msg = "Lista de entregas actualizada (rápida)" if quick else "Lista de entregas actualizada"
                self.app.update_status(msg, "success")
            
            self.logger.info(f"Lista de entregas actualizada: {len(self.entregas_list)} entregas (quick={quick})")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de entregas: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error cargando entregas", "danger")
            show_error_message("Error", f"Error cargando entregas: {str(e)}", self.container)
    
    def _load_available_employees(self):
        """Carga la lista de empleados disponibles para entregas"""
        try:
            self.empleados_disponibles = micro_empleados.obtener_empleados_activos_para_entrega()
            
            # Actualizar combo de empleados en formulario
            empleado_values = ["Seleccione empleado..."] + [
                emp['display_name'] for emp in self.empleados_disponibles
            ]
            self.form_empleado_combo['values'] = empleado_values
            
            # Actualizar combo de filtros
            filter_empleado_values = ["Todos"] + [
                emp['display_name'] for emp in self.empleados_disponibles
            ]
            self.filter_empleado_combo['values'] = filter_empleado_values
            
        except Exception as e:
            self.logger.error(f"Error cargando empleados disponibles: {e}")
    
    def _load_available_insumos(self):
        """Carga la lista de insumos disponibles"""
        try:
            insumos_data = micro_insumos.listar_insumos(active_only=True)
            self.insumos_disponibles = insumos_data.get('insumos', [])
            
            # Actualizar combo de insumos en formulario
            insumo_values = ["Seleccione insumo..."] + [
                f"{insumo['nombre']} ({insumo['categoria']})"
                for insumo in self.insumos_disponibles
            ]
            self.form_insumo_combo['values'] = insumo_values
            
            # Actualizar combo de filtros
            filter_insumo_values = ["Todos"] + [
                f"{insumo['nombre']} ({insumo['categoria']})"
                for insumo in self.insumos_disponibles
            ]
            self.filter_insumo_combo['values'] = filter_insumo_values
            
        except Exception as e:
            self.logger.error(f"Error cargando insumos disponibles: {e}")
    
    def _apply_filters(self):
        """Aplica filtros a la lista de entregas"""
        try:
            # Obtener valores de filtros
            empleado_filter = self.filter_empleado.get()
            insumo_filter = self.filter_insumo.get()
            periodo_filter = self.filter_periodo.get()
            
            # Filtrar lista original
            filtered_entregas = self.entregas_list.copy()
            
            # Filtro por empleado
            if empleado_filter and empleado_filter != "Todos":
                empleado_name = empleado_filter.split(" (")[0]  # Remover cédula del display
                filtered_entregas = [
                    e for e in filtered_entregas 
                    if empleado_name.lower() in e.get('empleado_nombre', '').lower()
                ]
            
            # Filtro por insumo
            if insumo_filter and insumo_filter != "Todos":
                insumo_name = insumo_filter.split(" (")[0]  # Remover categoría del display
                filtered_entregas = [
                    e for e in filtered_entregas 
                    if insumo_name.lower() in e.get('insumo_nombre', '').lower()
                ]
            
            # Filtro por período
            if periodo_filter and periodo_filter != "Todas":
                now = datetime.now()
                
                if periodo_filter == "Hoy":
                    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
                elif periodo_filter == "Últimos 7 días":
                    cutoff = now - timedelta(days=7)
                elif periodo_filter == "Últimos 30 días":
                    cutoff = now - timedelta(days=30)
                elif periodo_filter == "Este mes":
                    cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    cutoff = None
                
                if cutoff:
                    filtered_entregas = [
                        e for e in filtered_entregas
                        if datetime.fromisoformat(e['fecha_entrega'].replace('Z', '+00:00')) >= cutoff
                    ]
            
            # Actualizar tree con entregas filtradas
            self._update_tree_display(filtered_entregas)
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtros de entregas: {e}")
    
    def _update_tree_display(self, entregas: List[Dict[str, Any]]):
        """Actualiza la visualización del tree con entregas"""
        try:
            # Limpiar tree y almacenamiento auxiliar
            for item in self.entregas_tree.get_children():
                self.entregas_tree.delete(item)
            # Resetear mapa de datos completos por item
            self._item_data = {}
            
            # Agregar entregas (con zebra por estado reciente/antiguo)
            for idx, entrega in enumerate(entregas):
                # Formatear datos
                fecha = datetime.fromisoformat(entrega['fecha_entrega'].replace('Z', '+00:00'))
                fecha_display = fecha.strftime('%d/%m/%Y %H:%M')
                
                empleado_display = entrega.get('empleado_nombre', 'N/A')
                if len(empleado_display) > 25:
                    empleado_display = empleado_display[:22] + "..."
                
                insumo_display = entrega.get('insumo_nombre', 'N/A')
                if len(insumo_display) > 25:
                    insumo_display = insumo_display[:22] + "..."
                
                cantidad_display = f"{entrega['cantidad']} {entrega.get('insumo_unidad', '')}"
                entregado_por = entrega.get('entregado_por', 'Sistema')[:15]
                
                # Determinar tag basado en fecha (reciente vs antigua) y zebra
                tag_base = "recent" if fecha >= datetime.now() - timedelta(days=7) else "old"
                zebra_tag = "even" if idx % 2 == 0 else "odd"
                row_tag = f"{tag_base}_{zebra_tag}"
                
                # Insertar en tree
                item_id = self.entregas_tree.insert(
                    "", "end",
                    text=str(entrega.get('codigo', '')),
                    values=(
                        fecha_display,
                        empleado_display,
                        insumo_display,
                        cantidad_display,
                        entregado_por
                    ),
                    tags=(row_tag,)
                )
                
                # Guardar datos completos en un mapa auxiliar
                self._item_data[item_id] = entrega.copy()
            
            # Configurar colores zebra por estado
            try:
                self.entregas_tree.tag_configure("recent_even", background="#E8F5E8", foreground="#2E7D32")  # Verde claro (par)
                self.entregas_tree.tag_configure("recent_odd", background="#F1FAF1", foreground="#2E7D32")   # Verde más claro (impar)
                self.entregas_tree.tag_configure("old_even", background="#F5F5F5", foreground="#616161")      # Gris claro (par)
                self.entregas_tree.tag_configure("old_odd", background="#EEEEEE", foreground="#616161")       # Gris más claro (impar)
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"Error actualizando visualización de entregas: {e}")
    
    def _update_statistics(self, data: Dict[str, Any]):
        """Actualiza las estadísticas mostradas"""
        try:
            total_returned = data.get('total_returned', 0)
            total_count = data.get('total_count', 0)
            general_stats = data.get('general_statistics', {})
            
            # Estadísticas principales
            stats_text = f"Mostrando: {total_returned}"
            if total_count != total_returned:
                stats_text += f" de {total_count} total"
            
            # Estadísticas del día
            entregas_hoy = general_stats.get('entregas_hoy', 0)
            if entregas_hoy > 0:
                stats_text += f" | Hoy: {entregas_hoy}"
            
            self.stats_label.config(text=stats_text)
            
            # Estadísticas del período filtrado
            current_stats = data.get('current_page_statistics', {})
            if current_stats:
                empleados_unicos = current_stats.get('empleados_unicos', 0)
                
                period_text = f"{empleados_unicos} empleados únicos" if empleados_unicos > 0 else ""
                self.period_stats_label.config(text=period_text)
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas de entregas: {e}")
    
    def _on_empleado_selected(self, event=None):
        """Maneja la selección de empleado"""
        try:
            selected = self.form_empleado_display.get()
            
            if selected and selected != "Seleccione empleado...":
                # Encontrar empleado en la lista
                for emp in self.empleados_disponibles:
                    if emp['display_name'] == selected:
                        self.form_empleado_id.set(emp['id'])
                        break
                
                # Validar formulario
                self._validate_form_data()
                
        except Exception as e:
            self.logger.error(f"Error seleccionando empleado: {e}")
    
    def _on_insumo_selected(self, event=None):
        """Maneja la selección de insumo"""
        try:
            selected = self.form_insumo_display.get()
            
            if selected and selected != "Seleccione insumo...":
                # Encontrar insumo en la lista (parsear del display)
                insumo_name = selected.split(" (")[0]
                
                for insumo in self.insumos_disponibles:
                    if insumo['nombre'] == insumo_name:
                        self.form_insumo_id.set(insumo['id'])
                        
                        # Actualizar información de stock
                        self.stock_disponible.set(f"Disponible: {insumo['cantidad_actual']} {insumo['unidad_medida']}")
                        
                        # Configurar límite máximo en spinbox
                        self.form_cantidad_spinbox.config(to=insumo['cantidad_actual'])
                        
                        break
                
                # Validar stock
                self._validate_stock_availability()
                
                # Validar formulario
                self._validate_form_data()
                
        except Exception as e:
            self.logger.error(f"Error seleccionando insumo: {e}")
    
    def _on_empleado_text_changed(self, event=None):
        """Filtra dinámicamente la lista de empleados según el texto escrito en el combobox."""
        try:
            # Ignorar teclas de navegación para no interferir con la selección
            if event and event.keysym in ("Up", "Down", "Left", "Right", "Return", "Tab", "Escape"):
                return
            
            typed = self.form_empleado_display.get().strip().lower()
            base_values = ["Seleccione empleado..."] + [
                emp['display_name'] for emp in self.empleados_disponibles
            ]
            
            if not typed:
                filtered = base_values
            else:
                filtered = ["Seleccione empleado..."] + [
                    v for v in base_values[1:] if typed in v.lower()
                ]
            
            self.form_empleado_combo['values'] = filtered
            
            # Desplegar el combobox para mostrar coincidencias
            try:
                self.form_empleado_combo.event_generate("<Down>")
            except Exception:
                pass
        except Exception as e:
            self.logger.debug(f"Error filtrando empleados en combobox: {e}")
    
    def _on_insumo_text_changed(self, event=None):
        """Filtra dinámicamente la lista de insumos según el texto escrito en el combobox."""
        try:
            if event and event.keysym in ("Up", "Down", "Left", "Right", "Return", "Tab", "Escape"):
                return
            
            typed = self.form_insumo_display.get().strip().lower()
            base_values = ["Seleccione insumo..."] + [
                f"{insumo['nombre']} ({insumo['categoria']})"
                for insumo in self.insumos_disponibles
            ]
            
            if not typed:
                filtered = base_values
            else:
                filtered = ["Seleccione insumo..."] + [
                    v for v in base_values[1:] if typed in v.lower()
                ]
            
            self.form_insumo_combo['values'] = filtered
            
            # Desplegar el combobox para mostrar coincidencias
            try:
                self.form_insumo_combo.event_generate("<Down>")
            except Exception:
                pass
        except Exception as e:
            self.logger.debug(f"Error filtrando insumos en combobox: {e}")
     
    def _validate_stock_availability(self, event=None):
        """Valida la disponibilidad de stock para la cantidad solicitada"""
        try:
            if not self.form_insumo_id.get():
                return
            
            # Encontrar insumo seleccionado
            insumo_seleccionado = None
            for insumo in self.insumos_disponibles:
                if insumo['id'] == self.form_insumo_id.get():
                    insumo_seleccionado = insumo
                    break
            
            if not insumo_seleccionado:
                return
            
            cantidad_solicitada = self.form_cantidad.get()
            stock_actual = insumo_seleccionado['cantidad_actual']
            
            # Validar stock
            if cantidad_solicitada > stock_actual:
                warning_text = f"⚠️ Stock insuficiente (solicita: {cantidad_solicitada}, disponible: {stock_actual})"
                self.stock_warning.set(warning_text)
                self.stock_warning_label.config(bootstyle="danger")
            elif cantidad_solicitada == stock_actual:
                warning_text = f"⚡ Agotará el stock completo"
                self.stock_warning.set(warning_text)
                self.stock_warning_label.config(bootstyle="warning")
            elif cantidad_solicitada >= stock_actual * 0.8:
                warning_text = f"⚠️ Usará el 80%+ del stock"
                self.stock_warning.set(warning_text)
                self.stock_warning_label.config(bootstyle="warning")
            else:
                warning_text = "✅ Stock suficiente"
                self.stock_warning.set(warning_text)
                self.stock_warning_label.config(bootstyle="success")
            
        except Exception as e:
            self.logger.debug(f"Error validando stock: {e}")
    
    def _update_observaciones_var(self, event=None):
        """Actualiza la variable de observaciones desde el widget Text"""
        try:
            content = self.form_observaciones_text.get("1.0", tk.END).strip()
            self.form_observaciones.set(content)
        except Exception as e:
            self.logger.debug(f"Error actualizando observaciones: {e}")
    
    def _validate_form_data(self):
        """Valida los datos del formulario de entrega"""
        try:
            validation_messages = []
            is_valid = True
            
            # Validar empleado
            if not self.form_empleado_id.get():
                validation_messages.append("❌ Debe seleccionar un empleado")
                is_valid = False
            else:
                validation_messages.append("✅ Empleado seleccionado")
            
            # Validar insumo
            if not self.form_insumo_id.get():
                validation_messages.append("❌ Debe seleccionar un insumo")
                is_valid = False
            else:
                validation_messages.append("✅ Insumo seleccionado")
            
            # Validar cantidad
            cantidad = self.form_cantidad.get()
            if cantidad <= 0:
                validation_messages.append("❌ La cantidad debe ser mayor a cero")
                is_valid = False
            else:
                validation_messages.append(f"✅ Cantidad: {cantidad}")
            
            # Validar stock si ambos están seleccionados
            if self.form_empleado_id.get() and self.form_insumo_id.get():
                try:
                    stock_validation = micro_insumos.validar_stock_para_entrega(
                        self.form_insumo_id.get(),
                        cantidad
                    )
                    
                    if stock_validation['can_fulfill']:
                        validation_messages.append("✅ Stock suficiente para la entrega")
                    else:
                        validation_messages.append(f"❌ {stock_validation['message']}")
                        is_valid = False
                        
                except Exception as e:
                    validation_messages.append(f"❌ Error validando stock: {str(e)}")
                    is_valid = False
            
            # Mostrar resultado de validación
            self._show_validation_result(validation_messages, is_valid)
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Error validando formulario: {e}")
            self._show_validation_error(str(e))
            return False
    
    def _show_validation_result(self, messages: List[str], is_valid: bool):
        """Muestra el resultado de la validación"""
        try:
            # Actualizar texto de validación
            self.validation_text.config(state="normal")
            self.validation_text.delete("1.0", tk.END)
            
            validation_content = "VALIDACIÓN DE ENTREGA\n"
            validation_content += "=" * 25 + "\n\n"
            validation_content += "\n".join(messages)
            
            self.validation_text.insert("1.0", validation_content)
            self.validation_text.config(state="disabled")
            
            # Actualizar estado
            if is_valid:
                self.validation_status_label.config(
                    text="✅ Listo para registrar",
                    bootstyle="success"
                )
                self.save_delivery_btn.config(state="normal")
            else:
                self.validation_status_label.config(
                    text="❌ Faltan datos o hay errores",
                    bootstyle="danger"
                )
                self.save_delivery_btn.config(state="disabled")
                
        except Exception as e:
            self.logger.error(f"Error mostrando resultado de validación: {e}")
    
    def _show_validation_help(self):
        """Muestra mensaje de ayuda en el panel de validación"""
        self.validation_text.config(state="normal")
        self.validation_text.delete("1.0", tk.END)

        help_text = """INSTRUCCIONES PARA NUEVA ENTREGA
=============================

1. Seleccione el empleado que recibira el insumo
2. Seleccione el insumo a entregar
3. Especifique la cantidad (se validara contra stock)
4. Agregue observaciones si es necesario
5. Especifique quien entrega (opcional)

El sistema validara automaticamente que:
• El empleado este activo
• Hay stock suficiente del insumo
• Los datos sean correctos"""

        self.validation_text.insert("1.0", help_text)
        self.validation_text.config(state="disabled")

        if hasattr(self, 'validation_status_label'):
            self.validation_status_label.config(text="")
    
    def _show_validation_error(self, error: str):
        """Muestra un error en el panel de validación"""
        self.validation_text.config(state="normal")
        self.validation_text.delete("1.0", tk.END)
        self.validation_text.insert("1.0", f"ERROR DE VALIDACIÓN\n{'='*20}\n\n{error}")
        self.validation_text.config(state="disabled")
        
        self.validation_status_label.config(
            text="❌ Error en validación",
            bootstyle="danger"
        )
    
    def _on_filter_changed(self, event=None):
        """Maneja cambio en los filtros"""
        self._apply_filters()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        log_user_action("CLICK", "clear_filters", "EntregasTab")
        
        self.filter_empleado.set("Todos")
        self.filter_insumo.set("Todos")
        self.filter_periodo.set("Todas")
        
        self._apply_filters()
    
    def _on_entrega_selected(self, event=None):
        """Maneja la selección de una entrega"""
        selection = self.entregas_tree.selection()
        
        if selection:
            selected_item = selection[0]
            
            # Guardar referencia completa desde almacenamiento auxiliar
            self.selected_entrega = self._item_data.get(selected_item, {}).copy()
        else:
            self.selected_entrega = None
    
    def show_add_form(self):
        """Muestra el formulario para nueva entrega"""
        log_user_action("SHOW_ADD_FORM", "nueva_entrega", "EntregasTab")
        
        # Limpiar formulario
        self._clear_form()
        
        # Enfocar combo de empleado
        self.form_empleado_combo.focus_set()
    
    def filter_by_employee(self, empleado_id: int, empleado_nombre: str):
        """Filtra entregas por un empleado específico (llamado desde otros tabs)"""
        try:
            # Buscar en combo de filtros
            for emp in self.empleados_disponibles:
                if emp['id'] == empleado_id:
                    self.filter_empleado.set(emp['display_name'])
                    break
            
            # Aplicar filtro
            self._apply_filters()
            
            # Mostrar mensaje informativo
            show_info_message(
                "Filtro Aplicado",
                f"Mostrando entregas del empleado: {empleado_nombre}",
                self.frame
            )
            
            log_user_action("FILTER_BY_EMPLOYEE", "employee_filter_applied", f"ID: {empleado_id}")
            
        except Exception as e:
            self.logger.error(f"Error filtrando por empleado: {e}")
    
    def _clear_form(self):
        """Limpia el formulario"""
        log_user_action("CLEAR_FORM", "form_cleared", "EntregasTab")
        
        self.form_id.set("")
        self.form_empleado_id.set(0)
        self.form_empleado_display.set("Seleccione empleado...")
        self.form_insumo_id.set(0)
        self.form_insumo_display.set("Seleccione insumo...")
        self.form_cantidad.set(1)
        self.form_observaciones_text.delete("1.0", tk.END)
        self.form_observaciones.set("")
        self.form_entregado_por.set("")
        
        # Limpiar variables de estado
        self.stock_disponible.set("")
        self.stock_warning.set("")
        
        self.selected_entrega = None
        
        # Mostrar ayuda
        self._show_validation_help()
    
    def _cancel_form(self):
        """Cancela la operación actual"""
        log_user_action("CANCEL_FORM", "form_cancelled", "EntregasTab")
        self._clear_form()
    
    
    def _save_entrega(self):
        """Guarda la nueva entrega"""
        try:
            # Actualizar observaciones desde Text widget
            self._update_observaciones_var()
            
            # Validar formulario primero
            if not self._validate_form_data():
                show_error_message("Error de Validación", "Por favor corrija los errores antes de continuar", self.frame)
                return
            
            # Preparar datos
            form_data = {
                'empleado_id': self.form_empleado_id.get(),
                'insumo_id': self.form_insumo_id.get(),
                'cantidad': self.form_cantidad.get(),
                'observaciones': self.form_observaciones.get(),
                'entregado_por': self.form_entregado_por.get().strip() or "Sistema",
                'fecha_entrega': datetime.now()
            }
            
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Registrando entrega...")
            
            # Crear entrega
            result = micro_entregas.crear_entrega(form_data)
            
            if result['success']:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Entrega registrada exitosamente", "success")
                
                # Obtener información para mostrar
                entrega = result['entrega']
                
                show_info_message(
                    "Entrega Registrada",
                    f"Entrega registrada exitosamente:\n\n"
                    f"📋 ID: {result['entrega_id']}\n"
                    f"👤 Empleado: {entrega['empleado_nombre']}\n"
                    f"📦 Insumo: {entrega['insumo_nombre']}\n"
                    f"📊 Cantidad: {form_data['cantidad']} {entrega['insumo_unidad']}\n\n"
                    f"Stock anterior: {result['stock_anterior']}\n"
                    f"Stock actual: {result['stock_nuevo']}",
                    self.frame
                )
                
                # Actualizar datos y limpiar formulario
                self.refresh_data()
                self._clear_form()
                
                # Actualizar dashboard si está disponible
                if hasattr(self.app, 'dashboard_tab'):
                    self.app.dashboard_tab.refresh_data()
                
                log_user_action("CREATE_ENTREGA", "entrega_created", 
                              f"ID: {result['entrega_id']}, "
                              f"Empleado: {entrega['empleado_nombre']}, "
                              f"Insumo: {entrega['insumo_nombre']}")
                
            else:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Error registrando entrega", "danger")
                show_error_message("Error", "No se pudo registrar la entrega", self.frame)
                
        except ValidationException as e:
            show_error_message("Error de Validación", f"Error en el campo '{e.field}': {e.message}", self.frame)
            
        except InsufficientStockException as e:
            show_error_message(
                "Stock Insuficiente", 
                f"No hay stock suficiente para realizar la entrega:\n\n"
                f"Insumo: {e.insumo_nombre}\n"
                f"Stock disponible: {e.stock_actual}\n"
                f"Cantidad solicitada: {e.cantidad_solicitada}",
                self.frame
            )
            
        except BusinessLogicException as e:
            show_error_message("Error de Negocio", str(e), self.frame)
            
        except Exception as e:
            self.logger.error(f"Error registrando entrega: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error registrando entrega", "danger")
            show_error_message("Error", f"Error registrando entrega: {str(e)}", self.frame)
    
    def _view_entrega_details(self):
        """Muestra detalles de la entrega seleccionada"""
        if not self.selected_entrega:
            return
        
        log_user_action("DOUBLE_CLICK", "view_entrega_details", "EntregasTab")
        
        try:
            entrega_id = int(self.selected_entrega['id'])
            
            # Obtener detalles completos
            entrega = micro_entregas.obtener_entrega(entrega_id, include_details=True)
            
            # Crear ventana de detalles
            details_window = ttk.Toplevel(self.app.root)
            details_window.title(f"Detalles de Entrega #{entrega_id}")
            details_window.geometry("600x500")
            
            # Contenido
            content = ttk.Frame(details_window, padding="20")
            content.pack(fill=BOTH, expand=True)
            
            # Título
            heading_label = ttk.Label(
                content,
                text=f"📋 Entrega #{entrega_id}",
                font=("Helvetica", 14, "bold"),
                bootstyle="primary"
            )
            heading_label.pack(pady=(0, 15))
            
            # Información en texto
            details_text = tk.Text(content, height=20, wrap=tk.WORD)
            details_text.pack(fill=BOTH, expand=True)
            
            # Formatear información
            display_info = entrega['display_info']
            audit_info = entrega['audit_info']
            # Determinar código público y actualizar títulos
            codigo = display_info.get('codigo') or self.selected_entrega.get('codigo') or f"#{entrega_id}"
            try:
                details_window.title(f"Detalles de Entrega {codigo}")
                heading_label.config(text=f"📋 Entrega {codigo}")
            except Exception:
                pass
            
            details_content = f"""INFORMACIÓN DE LA ENTREGA
 {'='*40}
 
 Fecha: {display_info['fecha_entrega']}
 Código: {codigo}
 ID interno: {display_info['id']}
 
 EMPLEADO
 --------
 Nombre: {display_info['empleado_nombre']}
 Cédula: {display_info['empleado_cedula']}
 Cargo: {display_info['empleado_cargo']}
 Departamento: {display_info['empleado_departamento']}
 
 INSUMO
 ------
 Nombre: {display_info['insumo_nombre']}
 Categoría: {display_info['insumo_categoria']}
 Cantidad entregada: {display_info['cantidad_completa']}
 
 DETALLES ADICIONALES
 -------------------
 Entregado por: {display_info['entregado_por']}
 Observaciones: {display_info['observaciones']}
 Prioridad: {display_info['prioridad']}
 Es reciente: {display_info['es_reciente']}
 Alta cantidad: {display_info['es_alta_cantidad']}
 
 RESUMEN
 -------
 {display_info['resumen']}"""
            
            details_text.insert("1.0", details_content)
            details_text.config(state="disabled")
            
        except Exception as e:
            self.logger.error(f"Error mostrando detalles de entrega: {e}")
            show_error_message("Error", f"Error cargando detalles: {str(e)}", self.frame)
    
    def _delete_selected_entrega(self):
        """Elimina la entrega seleccionada del historial."""
        if not self.selected_entrega:
            show_error_message(
                "Sin selección",
                "Seleccione una entrega de la lista para poder eliminarla.",
                self.frame
            )
            return
        
        try:
            entrega_id = int(self.selected_entrega.get('id'))
            codigo = self.selected_entrega.get('codigo') or f"#{entrega_id}"
            empleado = self.selected_entrega.get('empleado_nombre', 'N/A')
            insumo = self.selected_entrega.get('insumo_nombre', 'N/A')
            
            if not ask_yes_no(
                "Confirmar Eliminación",
                (
                    f"¿Está seguro que desea eliminar la entrega {codigo}?\n\n"
                    f"Empleado: {empleado}\n"
                    f"Insumo: {insumo}\n\n"
                    "Nota: Esta acción no ajusta automáticamente el stock del insumo.\n"
                    "Si fue un registro errado, recuerde corregir el stock manualmente "
                    "desde la pestaña de Insumos."
                ),
                self.frame
            ):
                return
            
            result = micro_entregas.eliminar_entrega(entrega_id)
            
            if result.get('success'):
                show_info_message(
                    "Entrega Eliminada",
                    result.get('message', "La entrega fue eliminada correctamente."),
                    self.frame
                )
                
                # Refrescar lista y formulario
                self.refresh_data(quick=True)
                self._clear_form()
                
                # Actualizar dashboard si está disponible
                if hasattr(self.app, 'dashboard_tab'):
                    self.app.dashboard_tab.refresh_data(quick=True)
                
                log_user_action(
                    "DELETE_ENTREGA",
                    "entrega_deleted",
                    f"ID: {entrega_id}, Código: {codigo}"
                )
            else:
                show_error_message(
                    "Error",
                    "No se pudo eliminar la entrega seleccionada.",
                    self.frame
                )
        
        except Exception as e:
            self.logger.error(f"Error eliminando entrega: {e}")
            show_error_message("Error", f"Error eliminando entrega: {str(e)}", self.frame)