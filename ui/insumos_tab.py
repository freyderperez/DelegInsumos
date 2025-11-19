"""
DelegInsumos - Tab de Gestión de Insumos
Interfaz completa CRUD para gestión de insumos e inventario
"""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, List, Optional
from decimal import Decimal

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
except ImportError:
    print("Error: ttkbootstrap requerido")

from services.micro_insumos import micro_insumos
from models.insumo import Insumo
from utils.logger import LoggerMixin, log_user_action
from utils.helpers import (
    show_error_message, show_info_message,
    ask_yes_no, CATEGORIAS_INSUMOS, UNIDADES_MEDIDA
)
from utils.validators import validate_insumo_data
from exceptions.custom_exceptions import ValidationException, DuplicateRecordException


class InsumosTab(LoggerMixin):
    """
    Tab para gestión completa de insumos
    """
    
    def __init__(self, parent, app_instance):
        super().__init__()
        self.parent = parent
        self.app = app_instance
        
        # Crear frame principal
        self.frame = ttk.Frame(parent, padding="15")
        
        # Variables de datos
        self.insumos_list = []
        self.selected_insumo = None
        # Mapa local para guardar los datos completos de cada item del treeview
        self._item_data = {}
        
        # Variables de formulario
        self._init_form_variables()
        
        # Crear interfaz
        self._create_interface()
        
        # Cargar datos inicial
        self.refresh_data()
        
        self.logger.info("InsumosTab inicializado")
    
    def _init_form_variables(self):
        """Inicializa las variables del formulario"""
        # ID interno (numérico, oculto en UI)
        self.form_id = tk.StringVar()
        # Código público (visible en UI)
        self.form_codigo = tk.StringVar()
        self.form_nombre = tk.StringVar()
        self.form_categoria = tk.StringVar()
        self.form_cantidad_actual = tk.IntVar()
        self.form_cantidad_minima = tk.IntVar(value=5)
        self.form_cantidad_maxima = tk.IntVar(value=100)
        self.form_unidad_medida = tk.StringVar(value="unidad")
        self.form_precio_unitario = tk.StringVar()
        self.form_proveedor = tk.StringVar()
        
        # Variables de filtros
        self.filter_categoria = tk.StringVar()
        self.filter_search = tk.StringVar()
        self.filter_stock_status = tk.StringVar()
    
    def _create_interface(self):
        """Crea la interfaz del tab de insumos"""
        
        # Título del tab
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            title_frame,
            text="📦 Gestión de Insumos",
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
            text="➕ Nuevo Insumo",
            command=self.show_add_form,
            bootstyle="success"
        ).pack(side=RIGHT)
        
        # Panel principal dividido
        main_paned = ttk.Panedwindow(self.frame, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True)
        
        # Panel izquierdo: Lista e insumos
        self._create_list_panel(main_paned)
        
        # Panel derecho: Formulario
        self._create_form_panel(main_paned)
        
        self.logger.debug("Interfaz del tab de insumos creada")
    
    def _create_list_panel(self, parent):
        """Crea el panel de lista de insumos"""
        
        list_frame = ttk.Labelframe(
            parent,
            text="📋 Lista de Insumos",
            padding="15"
        )
        parent.add(list_frame, weight=2)
        
        # Panel de filtros
        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill=X, pady=(0, 15))
        
        # Búsqueda
        search_frame = ttk.Frame(filter_frame)
        search_frame.pack(fill=X, pady=(0, 5))
        
        ttk.Label(search_frame, text="🔍 Buscar:").pack(side=LEFT)
        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.filter_search,
            bootstyle="primary"
        )
        search_entry.pack(side=LEFT, fill=X, expand=True, padx=(5, 5))
        search_entry.bind("<KeyRelease>", self._on_search_changed)
        
        ttk.Button(
            search_frame,
            text="🔍",
            command=self._apply_filters,
            bootstyle="outline-primary",
            width=3
        ).pack(side=LEFT)
        
        # Filtros por categoria y estado
        filters_subframe = ttk.Frame(filter_frame)
        filters_subframe.pack(fill=X)
        
        # Filtro por categoría
        ttk.Label(filters_subframe, text="Categoría:").pack(side=LEFT)
        categoria_combo = ttk.Combobox(
            filters_subframe,
            textvariable=self.filter_categoria,
            values=["Todas"] + CATEGORIAS_INSUMOS,
            state="readonly",
            width=12,
            bootstyle="primary"
        )
        categoria_combo.pack(side=LEFT, padx=(5, 10))
        categoria_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        categoria_combo.current(0)
        
        # Filtro por estado de stock
        ttk.Label(filters_subframe, text="Estado:").pack(side=LEFT)
        status_combo = ttk.Combobox(
            filters_subframe,
            textvariable=self.filter_stock_status,
            values=["Todos", "Crítico", "Bajo", "Normal", "Exceso"],
            state="readonly",
            width=10,
            bootstyle="primary"
        )
        status_combo.pack(side=LEFT, padx=(5, 10))
        status_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        status_combo.current(0)
        
        # Botón limpiar filtros
        ttk.Button(
            filters_subframe,
            text="🧹 Limpiar",
            command=self._clear_filters,
            bootstyle="outline-secondary",
            width=10
        ).pack(side=RIGHT)
        
        # Treeview para lista de insumos
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=BOTH, expand=True)
        
        columns = ["Código", "Categoría", "Stock", "Mínimo", "Estado", "Proveedor"]
        self.insumos_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            bootstyle="primary"
        )

        # Configurar columnas
        self.insumos_tree.heading("#0", text="Nombre", anchor="w")
        self.insumos_tree.column("#0", width=200, stretch=True)

        column_configs = [
            ("Código", 120, False),
            ("Categoría", 100, False),
            ("Stock", 80, False),
            ("Mínimo", 70, False),
            ("Estado", 80, False),
            ("Proveedor", 120, True)
        ]

        for col, (title, width, stretch) in zip(columns, column_configs):
            self.insumos_tree.heading(col, text=title, anchor="center")
            self.insumos_tree.column(col, width=width, stretch=stretch)

        # Datos extra se almacenan en self._item_data; no configurar columnas ocultas no declaradas
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.insumos_tree.yview)
        x_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.insumos_tree.xview)
        self.insumos_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack del tree y scrollbars
        self.insumos_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Eventos del tree
        self.insumos_tree.bind("<<TreeviewSelect>>", self._on_insumo_selected)
        self.insumos_tree.bind("<Double-1>", lambda e: self._edit_selected_insumo())
        
        # Frame de estadísticas rápidas
        stats_frame = ttk.Frame(list_frame)
        stats_frame.pack(fill=X, pady=(10, 0))
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="Cargando estadísticas...",
            font=("Helvetica", 9),
            bootstyle="info"
        )
        self.stats_label.pack(side=LEFT)
        
        self.alerts_label = ttk.Label(
            stats_frame,
            text="",
            font=("Helvetica", 9),
            bootstyle="warning"
        )
        self.alerts_label.pack(side=RIGHT)
    
    def _create_form_panel(self, parent):
        """Crea el panel del formulario de insumos"""
        
        form_frame = ttk.Labelframe(
            parent,
            text="📝 Formulario de Insumo",
            padding="15"
        )
        parent.add(form_frame, weight=1)
        
        # Modo del formulario
        mode_frame = ttk.Frame(form_frame)
        mode_frame.pack(fill=X, pady=(0, 15))
        
        self.form_mode_label = ttk.Label(
            mode_frame,
            text="Nuevo Insumo",
            font=("Helvetica", 12, "bold"),
            bootstyle="success"
        )
        self.form_mode_label.pack(side=LEFT)
        
        # Botones de modo
        self.form_clear_btn = ttk.Button(
            mode_frame,
            text="🗑️ Limpiar",
            command=self._clear_form,
            bootstyle="outline-secondary",
            width=10
        )
        self.form_clear_btn.pack(side=RIGHT, padx=(5, 0))
        
        self.form_cancel_btn = ttk.Button(
            mode_frame,
            text="❌ Cancelar",
            command=self._cancel_form,
            bootstyle="outline-danger",
            width=10
        )
        self.form_cancel_btn.pack(side=RIGHT)
        
        # Campos del formulario
        self._create_form_fields(form_frame)
        
        # Botones de acción
        self._create_form_actions(form_frame)
    
    def _create_form_fields(self, parent):
        """Crea los campos del formulario"""
        
        fields_frame = ttk.Frame(parent)
        fields_frame.pack(fill=BOTH, expand=True, pady=(0, 15))
        
        # Código público (solo lectura)
        ttk.Label(fields_frame, text="Código:").grid(row=0, column=0, sticky="w", pady=2)
        codigo_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_codigo,
            state="readonly",
            bootstyle="secondary"
        )
        codigo_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Nombre (requerido)
        ttk.Label(fields_frame, text="* Nombre:").grid(row=1, column=0, sticky="w", pady=2)
        self.form_nombre_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_nombre,
            bootstyle="primary"
        )
        self.form_nombre_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Categoría (requerido)
        ttk.Label(fields_frame, text="* Categoría:").grid(row=2, column=0, sticky="w", pady=2)
        self.form_categoria_combo = ttk.Combobox(
            fields_frame,
            textvariable=self.form_categoria,
            values=CATEGORIAS_INSUMOS,
            bootstyle="primary"
        )
        self.form_categoria_combo.grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Cantidad actual
        ttk.Label(fields_frame, text="Stock Actual:").grid(row=3, column=0, sticky="w", pady=2)
        cantidad_frame = ttk.Frame(fields_frame)
        cantidad_frame.grid(row=3, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        self.form_cantidad_spinbox = ttk.Spinbox(
            cantidad_frame,
            from_=0,
            to=99999,
            textvariable=self.form_cantidad_actual,
            bootstyle="success",
            width=10
        )
        self.form_cantidad_spinbox.pack(side=LEFT)
        
        # Unidad de medida
        ttk.Label(cantidad_frame, text="Unidad:").pack(side=LEFT, padx=(10, 5))
        self.form_unidad_combo = ttk.Combobox(
            cantidad_frame,
            textvariable=self.form_unidad_medida,
            values=UNIDADES_MEDIDA,
            state="readonly",
            width=12,
            bootstyle="primary"
        )
        self.form_unidad_combo.pack(side=LEFT)
        
        # Límites de stock
        limits_frame = ttk.Frame(fields_frame)
        limits_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        
        ttk.Label(limits_frame, text="Límites de Stock:", font=("Helvetica", 10, "bold")).pack(anchor="w")
        
        limits_controls = ttk.Frame(limits_frame)
        limits_controls.pack(fill=X, pady=(5, 0))
        
        ttk.Label(limits_controls, text="Mínimo:").pack(side=LEFT)
        ttk.Spinbox(
            limits_controls,
            from_=0,
            to=9999,
            textvariable=self.form_cantidad_minima,
            bootstyle="warning",
            width=8
        ).pack(side=LEFT, padx=(5, 15))
        
        ttk.Label(limits_controls, text="Máximo:").pack(side=LEFT)
        ttk.Spinbox(
            limits_controls,
            from_=1,
            to=99999,
            textvariable=self.form_cantidad_maxima,
            bootstyle="info",
            width=8
        ).pack(side=LEFT, padx=(5, 0))
        
        # Proveedor
        ttk.Label(fields_frame, text="Proveedor:").grid(row=5, column=0, sticky="w", pady=2)
        self.form_proveedor_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_proveedor,
            bootstyle="secondary"
        )
        self.form_proveedor_entry.grid(row=5, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Configurar grid
        fields_frame.columnconfigure(1, weight=1)
        
        # Indicador de campos obligatorios
        ttk.Label(
            fields_frame,
            text="* Campos obligatorios",
            font=("Helvetica", 8),
            bootstyle="danger"
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))
    
    def _create_form_actions(self, parent):
        """Crea los botones de acción del formulario"""
        
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=X, pady=(15, 0))
        
        # Botón guardar
        self.save_btn = ttk.Button(
            actions_frame,
            text="💾 Guardar",
            command=self._save_insumo,
            bootstyle="success",
            width=15
        )
        self.save_btn.pack(side=LEFT, padx=(0, 5))
        
        # Botón actualizar stock
        self.update_stock_btn = ttk.Button(
            actions_frame,
            text="📊 Actualizar Stock",
            command=self._show_stock_update_dialog,
            bootstyle="info",
            width=15
        )
        self.update_stock_btn.pack(side=LEFT, padx=(0, 5))
        
        # Botón eliminar
        self.delete_btn = ttk.Button(
            actions_frame,
            text="🗑️ Eliminar",
            command=self._delete_insumo,
            bootstyle="danger-outline",
            width=15
        )
        self.delete_btn.pack(side=LEFT, padx=(0, 5))
        
        # Frame para estado del stock (info visual)
        self.stock_status_frame = ttk.Frame(actions_frame)
        self.stock_status_frame.pack(side=RIGHT, fill=X, expand=True)
        
        self.stock_status_label = ttk.Label(
            self.stock_status_frame,
            text="",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        self.stock_status_label.pack(side=RIGHT)
        
        # Inicialmente ocultar botones de edición
        self.update_stock_btn.pack_forget()
        self.delete_btn.pack_forget()
    
    def refresh_data(self, quick: bool = False):
        """Actualiza la lista de insumos.
        
        Args:
            quick: Si True, recarga rápida (solo datos y estadísticas, sin reconstruir UI).
        """
        try:
            self.logger.debug(f"Actualizando datos de insumos (quick={quick})")
            
            # Obtener lista de insumos con estado
            result = micro_insumos.listar_insumos(active_only=True, include_status=True)
            self.insumos_list = result.get('insumos', [])
            
            # Aplicar filtros actuales
            self._apply_filters()
            
            # Actualizar estadísticas
            self._update_statistics(result)
            
            if hasattr(self.app, 'update_status'):
                msg = "Lista de insumos actualizada (rápida)" if quick else "Lista de insumos actualizada"
                self.app.update_status(msg, "success")
            
            self.logger.info(f"Lista de insumos actualizada: {len(self.insumos_list)} items (quick={quick})")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de insumos: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error cargando insumos", "danger")
            show_error_message("Error", f"Error cargando insumos: {str(e)}", self.frame)
    
    def _apply_filters(self):
        """Aplica filtros a la lista de insumos"""
        try:
            # Obtener valores de filtros
            search_term = self.filter_search.get().lower().strip()
            categoria_filter = self.filter_categoria.get()
            status_filter = self.filter_stock_status.get()
            
            # Filtrar lista
            filtered_insumos = []
            
            for insumo in self.insumos_list:
                # Filtro de búsqueda
                if search_term:
                    searchable_text = f"{insumo['nombre']} {insumo['categoria']} {insumo.get('proveedor', '')}".lower()
                    if search_term not in searchable_text:
                        continue
                
                # Filtro de categoría
                if categoria_filter and categoria_filter != "Todas":
                    if insumo['categoria'] != categoria_filter:
                        continue
                
                # Filtro de estado de stock
                if status_filter and status_filter != "Todos":
                    current = insumo['cantidad_actual']
                    minimum = insumo['cantidad_minima']
                    maximum = insumo['cantidad_maxima']
                    
                    if status_filter == "Crítico" and current > 0:
                        continue
                    elif status_filter == "Bajo" and (current <= 0 or current > minimum):
                        continue
                    elif status_filter == "Normal" and (current <= 0 or current <= minimum or current >= maximum):
                        continue
                    elif status_filter == "Exceso" and current < maximum:
                        continue
                
                filtered_insumos.append(insumo)
            
            # Actualizar tree con insumos filtrados
            self._update_tree_display(filtered_insumos)
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtros: {e}")
    
    def _update_tree_display(self, insumos: List[Dict[str, Any]]):
        """Actualiza la visualización del tree con los insumos"""
        try:
            # Limpiar tree
            for item in self.insumos_tree.get_children():
                self.insumos_tree.delete(item)
            
            # Agregar insumos (con zebra para filas en estado normal)
            for idx, insumo in enumerate(insumos):
                # Determinar estado de stock y color
                current = insumo['cantidad_actual']
                minimum = insumo['cantidad_minima']
                maximum = insumo['cantidad_maxima']
                
                if current <= 0:
                    estado = "CRÍTICO"
                    tag = "critico"
                elif current <= minimum:
                    estado = "BAJO"
                    tag = "bajo"
                elif current >= maximum:
                    estado = "EXCESO"
                    tag = "exceso"
                else:
                    estado = "NORMAL"
                    tag = "normal"
                
                # Formatear valores
                stock_display = f"{current} {insumo['unidad_medida']}"
                minimo_display = f"{minimum} {insumo['unidad_medida']}"
                proveedor_display = insumo.get('proveedor', 'No especificado')[:20]

                # Zebra tag solo para filas en estado normal
                zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
                tags_to_apply = (tag,) if tag in ("critico", "bajo", "exceso") else (zebra_tag,)

                # Insertar en tree
                item_id = self.insumos_tree.insert(
                    "", "end",
                    text=insumo['nombre'],
                    values=(
                        insumo.get('codigo', ''),
                        insumo['categoria'],
                        stock_display,
                        minimo_display,
                        estado,
                        proveedor_display
                    ),
                    tags=tags_to_apply
                )
                
                # Guardar datos completos en el item (sin usar columnas ocultas)
                self._item_data[item_id] = insumo
            
            # Configurar colores por tag (estados especiales)
            # Crítico: rojo
            self.insumos_tree.tag_configure("critico", background="#FFCDD2", foreground="#B71C1C")
            # Bajo: naranja
            self.insumos_tree.tag_configure("bajo", background="#FFE0B2", foreground="#BF360C")
            # Exceso: azul (informativo, no error)
            self.insumos_tree.tag_configure("exceso", background="#E3F2FD", foreground="#0D47A1")
            # Zebra pattern para filas en estado NORMAL (verde suave)
            self.insumos_tree.tag_configure("zebra_even", background="#E8F5E9", foreground="#1B5E20")
            self.insumos_tree.tag_configure("zebra_odd", background="#C8E6C9", foreground="#1B5E20")
            
        except Exception as e:
            self.logger.error(f"Error actualizando visualización del tree: {e}")
    
    def _update_statistics(self, data: Dict[str, Any]):
        """Actualiza las estadísticas mostradas"""
        try:
            total = data.get('total', 0)
            by_status = data.get('by_status', {})
            statistics = data.get('statistics', {})
            
            # Estadísticas básicas (sin valor monetario)
            stats_text = f"Total: {total} insumos"
            self.stats_label.config(text=stats_text)
            
            # Alertas
            criticos = by_status.get('criticos', 0)
            bajos = by_status.get('bajo_stock', 0)
            total_alerts = criticos + bajos
            
            if total_alerts > 0:
                alerts_text = f"⚠️ {total_alerts} alertas"
                if criticos > 0:
                    alerts_text += f" (🔴 {criticos} críticas)"
                self.alerts_label.config(text=alerts_text, bootstyle="danger")
            else:
                self.alerts_label.config(text="✅ Sin alertas de stock", bootstyle="success")
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas: {e}")
    
    def _on_search_changed(self, event=None):
        """Maneja cambio en el campo de búsqueda"""
        # Aplicar filtros con pequeño delay para evitar filtrado excesivo
        if hasattr(self, '_search_timer'):
            self.frame.after_cancel(self._search_timer)
        
        self._search_timer = self.frame.after(500, self._apply_filters)
    
    def _on_filter_changed(self, event=None):
        """Maneja cambio en los filtros"""
        self._apply_filters()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        log_user_action("CLICK", "clear_filters", "InsumosTab")
        
        self.filter_search.set("")
        self.filter_categoria.set("Todas")
        self.filter_stock_status.set("Todos")
        
        self._apply_filters()
    
    def _on_insumo_selected(self, event=None):
        """Maneja la selección de un insumo"""
        selection = self.insumos_tree.selection()
        
        if selection:
            selected_item = selection[0]
            
            # Cargar datos en formulario
            self._load_insumo_to_form(selected_item)
            
            # Mostrar botones de edición (evitar 'before' si aún no está empacado)
            if not self.update_stock_btn.winfo_ismapped():
                self.update_stock_btn.pack(side=LEFT, padx=(0, 5))
            if not self.delete_btn.winfo_ismapped():
                self.delete_btn.pack(side=LEFT, padx=(0, 5))
            
            # Cambiar modo del formulario
            self.form_mode_label.config(text="Editar Insumo", bootstyle="warning")
            
        else:
            # Ocultar botones de edición
            self.update_stock_btn.pack_forget()
            self.delete_btn.pack_forget()
            
            # Cambiar a modo agregar
            self.form_mode_label.config(text="Nuevo Insumo", bootstyle="success")
    
    def _load_insumo_to_form(self, tree_item):
        """Carga datos de un insumo en el formulario"""
        try:
            # Obtener datos del tree item
            self.selected_insumo = {}
            
            # Cargar valores principales
            data = self._item_data.get(tree_item, {})
            # IDs
            self.form_id.set(str(data.get("id", "")))              # interno
            self.form_codigo.set(data.get("codigo", ""))           # público

            # Campos visibles
            self.form_nombre.set(data.get("nombre", ""))
            self.form_categoria.set(data.get("categoria", ""))
            self.form_cantidad_actual.set(int(data.get("cantidad_actual", 0)))
            self.form_cantidad_minima.set(int(data.get("cantidad_minima", 0)))
            self.form_cantidad_maxima.set(int(data.get("cantidad_maxima", 0)))
            self.form_unidad_medida.set(data.get("unidad_medida", ""))
            self.form_proveedor.set(data.get("proveedor", ""))

            # Guardar referencia completa
            self.selected_insumo = {
                key: data.get(key)
                for key in ["id", "nombre", "categoria", "cantidad_actual",
                            "cantidad_minima", "cantidad_maxima", "unidad_medida",
                            "proveedor"]
            }
            
            # Actualizar estado visual del stock
            self._update_stock_status_display()
            
        except Exception as e:
            self.logger.error(f"Error cargando insumo al formulario: {e}")
    
    def _update_stock_status_display(self):
        """Actualiza la visualización del estado del stock"""
        try:
            current = self.form_cantidad_actual.get()
            minimum = self.form_cantidad_minima.get()
            maximum = self.form_cantidad_maxima.get()
            
            # Determinar estado
            if current <= 0:
                status_text = "🔴 Stock CRÍTICO"
                style = "danger"
            elif current <= minimum:
                status_text = f"🟠 Stock BAJO (min: {minimum})"
                style = "warning"
            elif current >= maximum:
                status_text = f"🔵 Stock EXCESO (max: {maximum})"
                style = "info"
            else:
                status_text = f"🟢 Stock NORMAL ({current}/{maximum})"
                style = "success"
            
            self.stock_status_label.config(text=status_text, bootstyle=style)
            
        except Exception as e:
            self.logger.debug(f"Error actualizando estado de stock: {e}")
    
    def show_add_form(self):
        """Muestra el formulario para agregar nuevo insumo"""
        log_user_action("SHOW_ADD_FORM", "new_insumo", "InsumosTab")
        
        # Limpiar selección tree
        self.insumos_tree.selection_remove(self.insumos_tree.selection())
        
        # Limpiar formulario
        self._clear_form()
        
        # Enfocar campo de nombre
        self.form_nombre_entry.focus_set()
    
    def _clear_form(self):
        """Limpia el formulario"""
        log_user_action("CLEAR_FORM", "form_cleared", "InsumosTab")
        
        self.form_id.set("")
        self.form_codigo.set("")
        self.form_nombre.set("")
        self.form_categoria.set("")
        self.form_cantidad_actual.set(0)
        self.form_cantidad_minima.set(5)
        self.form_cantidad_maxima.set(100)
        self.form_unidad_medida.set("unidad")
        # No hay precio unitario
        self.form_proveedor.set("")
        
        self.selected_insumo = None
        
        # Ocultar botones de edición
        self.update_stock_btn.pack_forget()
        self.delete_btn.pack_forget()
        
        # Cambiar modo
        self.form_mode_label.config(text="Nuevo Insumo", bootstyle="success")
        
        # Limpiar estado de stock
        self.stock_status_label.config(text="")
    
    def _cancel_form(self):
        """Cancela la edición actual"""
        log_user_action("CANCEL_FORM", "form_cancelled", "InsumosTab")
        
        # Limpiar selección
        self.insumos_tree.selection_remove(self.insumos_tree.selection())
        
        # Limpiar formulario
        self._clear_form()
    
    def _save_insumo(self):
        """Guarda el insumo (nuevo o editado)"""
        try:
            # Preparar datos del formulario
            form_data = {
                'nombre': self.form_nombre.get().strip(),
                'categoria': self.form_categoria.get().strip(),
                'cantidad_actual': self.form_cantidad_actual.get(),
                'cantidad_minima': self.form_cantidad_minima.get(),
                'cantidad_maxima': self.form_cantidad_maxima.get(),
                'unidad_medida': self.form_unidad_medida.get(),
                'proveedor': self.form_proveedor.get().strip()
            }
            
            # Validar datos básicos
            if not form_data['nombre']:
                show_error_message("Error", "El nombre del insumo es obligatorio", self.frame)
                self.form_nombre_entry.focus_set()
                return
            
            if not form_data['categoria']:
                show_error_message("Error", "La categoría es obligatoria", self.frame)
                self.form_categoria_combo.focus_set()
                return
            
            # Determinar si es creación o actualización
            is_update = bool(self.selected_insumo and self.form_id.get())
            
            if hasattr(self.app, 'update_status'):
                action = "Actualizando" if is_update else "Creando"
                self.app.update_status(f"{action} insumo...")
            
            if is_update:
                # Actualizar insumo existente
                insumo_id = int(self.form_id.get())
                result = micro_insumos.actualizar_insumo(insumo_id, form_data)
                
                log_user_action("UPDATE_INSUMO", "insumo_updated", f"ID: {insumo_id}")
            else:
                # Crear nuevo insumo
                result = micro_insumos.crear_insumo(form_data)
                
                log_user_action("CREATE_INSUMO", "insumo_created", f"Nombre: {form_data['nombre']}")
            
            if result['success']:
                action_text = "actualizado" if is_update else "creado"
                
                if hasattr(self.app, 'update_status'):
                    self.app.update_status(f"Insumo {action_text} exitosamente", "success")
                
                show_info_message(
                    "Operación Exitosa",
                    result['message'],
                    self.frame
                )
                
                # Actualizar lista y limpiar formulario
                self.refresh_data()
                self._clear_form()
                
            else:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Error guardando insumo", "danger")
                show_error_message("Error", "No se pudo guardar el insumo", self.frame)
                
        except ValidationException as e:
            show_error_message("Error de Validación", f"Error en el campo '{e.field}': {e.message}", self.frame)
            
        except DuplicateRecordException as e:
            show_error_message("Insumo Duplicado", e.message, self.frame)
            self.form_nombre_entry.focus_set()
            
        except Exception as e:
            self.logger.error(f"Error guardando insumo: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error guardando insumo", "danger")
            show_error_message("Error", f"Error guardando insumo: {str(e)}", self.frame)
    
    def _edit_selected_insumo(self):
        """Edita el insumo seleccionado (doble click)"""
        log_user_action("DOUBLE_CLICK", "edit_insumo", "InsumosTab")
        
        if self.selected_insumo:
            self.form_nombre_entry.focus_set()
    
    def _show_stock_update_dialog(self):
        """Muestra diálogo para actualización rápida de stock"""
        log_user_action("CLICK", "show_stock_update", "InsumosTab")
        
        if not self.selected_insumo:
            return
        
        try:
            # Crear ventana de diálogo
            dialog = ttk.Toplevel(self.app.root)
            dialog.title("Actualizar Stock")
            dialog.geometry("400x300")
            dialog.resizable(False, False)
            
            # Centrar diálogo
            dialog.transient(self.app.root)
            dialog.grab_set()
            
            # Contenido del diálogo
            content = ttk.Frame(dialog, padding="20")
            content.pack(fill=BOTH, expand=True)
            
            # Información actual
            ttk.Label(
                content,
                text=f"Actualizar Stock: {self.form_nombre.get()}",
                font=("Helvetica", 12, "bold"),
                bootstyle="primary"
            ).pack(pady=(0, 15))
            
            # Stock actual
            current_frame = ttk.Frame(content)
            current_frame.pack(fill=X, pady=(0, 10))
            
            ttk.Label(current_frame, text="Stock actual:").pack(side=LEFT)
            ttk.Label(
                current_frame,
                text=f"{self.form_cantidad_actual.get()} {self.form_unidad_medida.get()}",
                font=("Helvetica", 10, "bold"),
                bootstyle="info"
            ).pack(side=RIGHT)
            
            # Nuevo stock
            new_stock_frame = ttk.Frame(content)
            new_stock_frame.pack(fill=X, pady=(0, 10))
            
            ttk.Label(new_stock_frame, text="Nuevo stock:").pack(side=LEFT)
            new_stock_var = tk.IntVar(value=self.form_cantidad_actual.get())
            new_stock_spinbox = ttk.Spinbox(
                new_stock_frame,
                from_=0,
                to=99999,
                textvariable=new_stock_var,
                bootstyle="success",
                width=10
            )
            new_stock_spinbox.pack(side=RIGHT)
            new_stock_spinbox.focus_set()
            new_stock_spinbox.select_range(0, tk.END)
            
            # Motivo del cambio
            ttk.Label(content, text="Motivo del cambio:").pack(anchor="w", pady=(10, 5))
            motivo_var = tk.StringVar()
            motivo_combo = ttk.Combobox(
                content,
                textvariable=motivo_var,
                values=[
                    "Recepción de mercancía",
                    "Corrección de inventario", 
                    "Devolución de insumos",
                    "Ajuste por auditoría",
                    "Otros"
                ],
                bootstyle="secondary"
            )
            motivo_combo.pack(fill=X, pady=(0, 15))
            
            # Botones
            buttons_frame = ttk.Frame(content)
            buttons_frame.pack(fill=X, pady=(15, 0))
            
            def save_stock_update():
                try:
                    nueva_cantidad = new_stock_var.get()
                    motivo = motivo_var.get() or "Actualización manual"
                    
                    if nueva_cantidad < 0:
                        show_error_message("Error", "La cantidad no puede ser negativa", dialog)
                        return
                    
                    insumo_id = int(self.form_id.get())
                    result = micro_insumos.actualizar_stock(insumo_id, nueva_cantidad, motivo)
                    
                    if result['success']:
                        # Actualizar formulario
                        self.form_cantidad_actual.set(nueva_cantidad)
                        self._update_stock_status_display()
                        
                        # Actualizar lista
                        self.refresh_data()
                        
                        # Cerrar diálogo
                        dialog.destroy()
                        
                        show_info_message(
                            "Stock Actualizado",
                            f"Stock actualizado de {result['cantidad_anterior']} a {result['cantidad_nueva']}",
                            self.frame
                        )
                        
                        log_user_action("UPDATE_STOCK", "stock_updated", 
                                      f"ID: {insumo_id}, Cantidad: {nueva_cantidad}")
                    
                except Exception as e:
                    self.logger.error(f"Error actualizando stock: {e}")
                    show_error_message("Error", f"Error actualizando stock: {str(e)}", dialog)
            
            ttk.Button(
                buttons_frame,
                text="💾 Actualizar Stock",
                command=save_stock_update,
                bootstyle="success"
            ).pack(side=LEFT, padx=(0, 5))
            
            ttk.Button(
                buttons_frame,
                text="❌ Cancelar",
                command=dialog.destroy,
                bootstyle="danger-outline"
            ).pack(side=RIGHT)
            
            # Bind Enter key
            dialog.bind("<Return>", lambda e: save_stock_update())
            dialog.bind("<Escape>", lambda e: dialog.destroy())
            
        except Exception as e:
            self.logger.error(f"Error mostrando diálogo de stock: {e}")
            show_error_message("Error", f"Error abriendo diálogo: {str(e)}", self.frame)
    
    def _delete_insumo(self):
        """Elimina el insumo seleccionado"""
        if not self.selected_insumo:
            return
        
        try:
            insumo_nombre = self.form_nombre.get()
            
            # Confirmar eliminación
            if ask_yes_no(
                "Confirmar Eliminación",
                f"¿Está seguro que desea eliminar el insumo?\n\n{insumo_nombre}\n\n"
                f"El insumo será marcado como inactivo pero se mantendrá en el historial.",
                self.frame
            ):
                insumo_id = int(self.form_id.get())
                result = micro_insumos.eliminar_insumo(insumo_id, soft_delete=True)
                
                if result['success']:
                    show_info_message("Insumo Eliminado", result['message'], self.frame)
                    
                    # Actualizar lista y limpiar formulario
                    self.refresh_data()
                    self._clear_form()
                    
                    log_user_action("DELETE_INSUMO", "insumo_deleted", f"ID: {insumo_id}")
                    
                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Insumo eliminado", "success")
                else:
                    show_error_message("Error", "No se pudo eliminar el insumo", self.frame)
            
        except Exception as e:
            self.logger.error(f"Error eliminando insumo: {e}")
            show_error_message("Error", f"Error eliminando insumo: {str(e)}", self.frame)