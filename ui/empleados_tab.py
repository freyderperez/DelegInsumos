"""
DelegInsumos - Tab de Gestión de Empleados
Interfaz completa CRUD para gestión de empleados
"""

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Any, List, Optional
from datetime import datetime, date

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.widgets import DateEntry
except ImportError:
    print("Error: ttkbootstrap requerido")

from services.micro_empleados import micro_empleados
from models.empleado import Empleado
from utils.logger import LoggerMixin, log_user_action
from utils.helpers import (
    format_date, show_error_message, show_info_message, 
    ask_yes_no, DEPARTAMENTOS
)
from utils.validators import validate_empleado_data, DataValidator
from exceptions.custom_exceptions import ValidationException, DuplicateRecordException


class EmpleadosTab(LoggerMixin):
    """
    Tab para gestión completa de empleados
    """
    
    def __init__(self, parent, app_instance):
        super().__init__()
        self.parent = parent
        self.app = app_instance
        
        # Crear frame principal
        self.frame = ttk.Frame(parent, padding="10")
        
        # Variables de datos
        self.empleados_list = []
        self.selected_empleado = None
        # Mapeo interno para almacenar datos completos por item del Treeview
        self._item_data = {}
        
        # Variables de formulario
        self._init_form_variables()
        
        # Crear interfaz
        self._create_interface()
        
        # Cargar datos inicial
        self.refresh_data()
        
        self.logger.info("EmpleadosTab inicializado")
    
    def _init_form_variables(self):
        """Inicializa las variables del formulario"""
        # Interno (no visible)
        self.form_id = tk.StringVar()
        # Código público visible
        self.form_codigo = tk.StringVar()

        self.form_nombre_completo = tk.StringVar()
        self.form_cargo = tk.StringVar()
        self.form_departamento = tk.StringVar()
        self.form_cedula = tk.StringVar()
        self.form_email = tk.StringVar()
        self.form_telefono = tk.StringVar()
        # Nuevos campos
        self.form_activo = tk.BooleanVar(value=True)
        self.form_nota = tk.StringVar()
        # fecha_ingreso eliminada
        
        # Variables de filtros
        self.filter_departamento = tk.StringVar()
        self.filter_search = tk.StringVar()
        self.filter_status = tk.StringVar()
    
    def _create_interface(self):
        """Crea la interfaz del tab de empleados"""
        
        # Título del tab
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            title_frame,
            text="👥 Gestión de Empleados",
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
            text="➕ Nuevo Empleado",
            command=self.show_add_form,
            bootstyle="success"
        ).pack(side=RIGHT)
        
        # Panel principal dividido
        main_paned = ttk.Panedwindow(self.frame, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True)
        
        # Panel izquierdo: Lista de empleados
        self._create_list_panel(main_paned)
        
        # Panel derecho: Formulario
        self._create_form_panel(main_paned)
        
        self.logger.debug("Interfaz del tab de empleados creada")
    
    def _create_list_panel(self, parent):
        """Crea el panel de lista de empleados"""
        
        list_frame = ttk.Labelframe(
            parent,
            text="📋 Lista de Empleados",
            padding="10"
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
        
        # Filtros por departamento y estado
        filters_subframe = ttk.Frame(filter_frame)
        filters_subframe.pack(fill=X)
        
        # Filtro por departamento
        ttk.Label(filters_subframe, text="Departamento:").pack(side=LEFT)
        departamento_combo = ttk.Combobox(
            filters_subframe,
            textvariable=self.filter_departamento,
            values=["Todos"] + DEPARTAMENTOS,
            state="readonly",
            bootstyle="primary"
        )
        departamento_combo.pack(side=LEFT, padx=(5, 10))
        departamento_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)
        departamento_combo.current(0)

        # Filtro por estado
        ttk.Label(filters_subframe, text="Estado:").pack(side=LEFT)
        status_combo = ttk.Combobox(
            filters_subframe,
            textvariable=self.filter_status,
            values=["Todos", "Activos", "Inactivos"],
            state="readonly",
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
            bootstyle="outline-secondary"
        ).pack(side=RIGHT)
        
        # Treeview para lista de empleados
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=BOTH, expand=True)
        
        columns = ["Código", "Cédula", "Cargo", "Departamento", "Email", "Teléfono"]
        self.empleados_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            bootstyle="primary"
        )
        
        # Configurar columnas
        self.empleados_tree.heading("#0", text="Nombre Completo", anchor="w")
        self.empleados_tree.column("#0", width=200, stretch=True)
        
        column_configs = [
            ("Código", 80, False),
            ("Cédula", 90, False),
            ("Cargo", 100, True),
            ("Departamento", 120, True),
            ("Email", 140, True),
            ("Teléfono", 90, False)
        ]
        
        for col, (title, width, stretch) in zip(columns, column_configs):
            self.empleados_tree.heading(col, text=title, anchor="center")
            self.empleados_tree.column(col, width=width, stretch=stretch)
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.empleados_tree.yview)
        x_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.empleados_tree.xview)
        self.empleados_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Grid layout
        self.empleados_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Eventos del tree
        self.empleados_tree.bind("<<TreeviewSelect>>", self._on_empleado_selected)
        self.empleados_tree.bind("<Double-1>", lambda e: self._edit_selected_empleado())
        
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
        
        self.department_stats_label = ttk.Label(
            stats_frame,
            text="",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        self.department_stats_label.pack(side=RIGHT)
    
    def _create_form_panel(self, parent):
        """Crea el panel del formulario de empleados"""
        
        form_frame = ttk.Labelframe(
            parent,
            text="📝 Formulario de Empleado",
            padding="10"
        )
        parent.add(form_frame, weight=1)
        
        # Modo del formulario
        mode_frame = ttk.Frame(form_frame)
        mode_frame.pack(fill=X, pady=(0, 15))
        
        self.form_mode_label = ttk.Label(
            mode_frame,
            text="Nuevo Empleado",
            font=("Helvetica", 12, "bold"),
            bootstyle="success"
        )
        self.form_mode_label.pack(side=LEFT)
        
        # Botones de control
        self.form_clear_btn = ttk.Button(
            mode_frame,
            text="🗑️ Limpiar",
            command=self._clear_form,
            bootstyle="outline-secondary"
        )
        self.form_clear_btn.pack(side=RIGHT, padx=(5, 0))

        self.form_cancel_btn = ttk.Button(
            mode_frame,
            text="❌ Cancelar",
            command=self._cancel_form,
            bootstyle="outline-danger"
        )
        self.form_cancel_btn.pack(side=RIGHT)
        
        # Campos del formulario
        self._create_employee_form_fields(form_frame)
        
        # Botones de acción
        self._create_employee_form_actions(form_frame)
    
    def _create_employee_form_fields(self, parent):
        """Crea los campos del formulario de empleado"""
        
        fields_frame = ttk.Frame(parent)
        fields_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Código (solo lectura)
        ttk.Label(fields_frame, text="Código:").grid(row=0, column=0, sticky="w", pady=2)
        codigo_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_codigo,
            state="readonly",
            bootstyle="secondary"
        )
        codigo_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Nombre completo (requerido)
        ttk.Label(fields_frame, text="* Nombre Completo:").grid(row=1, column=0, sticky="w", pady=2)
        self.form_nombre_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_nombre_completo,
            bootstyle="primary"
        )
        self.form_nombre_entry.grid(row=1, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Cédula (requerido)
        ttk.Label(fields_frame, text="* Cédula:").grid(row=2, column=0, sticky="w", pady=2)
        self.form_cedula_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_cedula,
            bootstyle="primary"
        )
        self.form_cedula_entry.grid(row=2, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Cargo
        ttk.Label(fields_frame, text="Cargo:").grid(row=3, column=0, sticky="w", pady=2)
        self.form_cargo_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_cargo,
            bootstyle="secondary"
        )
        self.form_cargo_entry.grid(row=3, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Departamento
        ttk.Label(fields_frame, text="Departamento:").grid(row=4, column=0, sticky="w", pady=2)
        self.form_departamento_combo = ttk.Combobox(
            fields_frame,
            textvariable=self.form_departamento,
            values=DEPARTAMENTOS,
            bootstyle="info"
        )
        self.form_departamento_combo.grid(row=4, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Email
        ttk.Label(fields_frame, text="Email:").grid(row=5, column=0, sticky="w", pady=2)
        self.form_email_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_email,
            bootstyle="info"
        )
        self.form_email_entry.grid(row=5, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Teléfono
        ttk.Label(fields_frame, text="Teléfono:").grid(row=6, column=0, sticky="w", pady=2)
        self.form_telefono_entry = ttk.Entry(
            fields_frame,
            textvariable=self.form_telefono,
            bootstyle="info"
        )
        self.form_telefono_entry.grid(row=6, column=1, sticky="ew", padx=(5, 0), pady=2)
        
        # Estado (Activo/Inactivo)
        ttk.Label(fields_frame, text="Estado:").grid(row=7, column=0, sticky="w", pady=2)
        self.form_activo_chk = ttk.Checkbutton(
            fields_frame,
            text="Activo",
            variable=self.form_activo,
            bootstyle="success-round-toggle"
        )
        self.form_activo_chk.grid(row=7, column=1, sticky="w", padx=(5, 0), pady=2)
        
        # Nota
        ttk.Label(fields_frame, text="Nota:").grid(row=8, column=0, sticky="nw", pady=2)
        self.form_nota_text = tk.Text(
            fields_frame,
            height=3,
            wrap=tk.WORD,
            font=("Helvetica", 9)
        )
        self.form_nota_text.grid(row=8, column=1, sticky="ew", padx=(5, 0), pady=2)
        self.form_nota_text.bind("<KeyRelease>", self._update_nota_var)
        
        # Fecha de ingreso (eliminada - no necesaria)
        
        # Configurar grid
        fields_frame.columnconfigure(1, weight=1)
        
        # Frame de información adicional (se llena al seleccionar empleado)
        self.info_frame = ttk.Labelframe(
            fields_frame,
            text="ℹ️ Información Adicional",
            padding="10"
        )
        self.info_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(15, 0))
        
        self.info_text = tk.Text(
            self.info_frame,
            height=4,
            wrap=tk.WORD,
            font=("Helvetica", 9)
        )
        self.info_text.pack(fill=BOTH, expand=True)
        self.info_text.config(state="disabled")
        
        # Indicador de campos obligatorios
        ttk.Label(
            fields_frame,
            text="* Campos obligatorios",
            font=("Helvetica", 8),
            bootstyle="danger"
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(10, 0))
    
    def _create_employee_form_actions(self, parent):
        """Crea los botones de acción del formulario"""
        
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=X, pady=(10, 0))
        
        # Botón guardar
        self.save_btn = ttk.Button(
            actions_frame,
            text="💾 Guardar",
            command=self._save_empleado,
            bootstyle="success"
        )
        self.save_btn.pack(side=LEFT, padx=(0, 5))

        # Botón ver entregas
        self.view_deliveries_btn = ttk.Button(
            actions_frame,
            text="📋 Ver Entregas",
            command=self._view_employee_deliveries,
            bootstyle="info"
        )
        self.view_deliveries_btn.pack(side=LEFT, padx=(0, 5))

        # Botón eliminar
        self.delete_btn = ttk.Button(
            actions_frame,
            text="🗑️ Eliminar",
            command=self._delete_empleado,
            bootstyle="danger-outline"
        )
        self.delete_btn.pack(side=LEFT, padx=(0, 5))
        
        # Estado del empleado
        self.employee_status_frame = ttk.Frame(actions_frame)
        self.employee_status_frame.pack(side=RIGHT, fill=X, expand=True)
        
        self.employee_status_label = ttk.Label(
            self.employee_status_frame,
            text="",
            font=("Helvetica", 9),
            bootstyle="secondary"
        )
        self.employee_status_label.pack(side=RIGHT)
        
        # Inicialmente ocultar botones de edición
        self.view_deliveries_btn.pack_forget()
        self.delete_btn.pack_forget()
    
    def refresh_data(self, quick: bool = False):
        """Actualiza la lista de empleados.
        
        Args:
            quick: Si True, realiza una recarga rápida (sin reconstruir elementos de UI innecesarios).
        """
        try:
            self.logger.debug(f"Actualizando datos de empleados (quick={quick})")
            
            # Obtener lista de empleados con estadísticas (incluir activos e inactivos)
            result = micro_empleados.listar_empleados(active_only=False, include_stats=True)
            self.empleados_list = result.get('empleados', [])
            
            # Aplicar filtros actuales
            self._apply_filters()
            
            # Actualizar estadísticas
            self._update_statistics(result)
            
            if hasattr(self.app, 'update_status'):
                msg = "Lista de empleados actualizada (rápida)" if quick else "Lista de empleados actualizada"
                self.app.update_status(msg, "success")
            
            self.logger.info(f"Lista de empleados actualizada: {len(self.empleados_list)} empleados (quick={quick})")
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de empleados: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error cargando empleados", "danger")
            show_error_message("Error", f"Error cargando empleados: {str(e)}", self.frame)
    
    def _apply_filters(self):
        """Aplica filtros a la lista de empleados"""
        try:
            # Obtener valores de filtros
            search_term = self.filter_search.get().lower().strip()
            departamento_filter = self.filter_departamento.get()
            status_filter = self.filter_status.get()
            
            # Filtrar lista
            filtered_empleados = []
            
            for empleado in self.empleados_list:
                # Crear objeto Empleado para usar métodos de búsqueda
                emp_obj = Empleado.from_dict(empleado)
                
                # Filtro de búsqueda
                if search_term and not emp_obj.matches_search_term(search_term):
                    continue
                
                # Filtro de departamento
                if departamento_filter and departamento_filter != "Todos":
                    if empleado.get('departamento', '') != departamento_filter:
                        continue
                
                # Filtro de estado
                if status_filter and status_filter != "Todos":
                    if status_filter == "Activos" and not empleado.get('activo', True):
                        continue
                    elif status_filter == "Inactivos" and empleado.get('activo', True):
                        continue
                
                filtered_empleados.append(empleado)
            
            # Actualizar tree con empleados filtrados
            self._update_tree_display(filtered_empleados)
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtros de empleados: {e}")
    
    def _update_tree_display(self, empleados: List[Dict[str, Any]]):
        """Actualiza la visualización del tree con empleados"""
        try:
            # Limpiar tree y almacenamiento auxiliar
            for item in self.empleados_tree.get_children():
                self.empleados_tree.delete(item)
            # Resetear mapa de datos completos por item
            self._item_data = {}
            
            # Agregar empleados (con zebra y estado)
            for idx, empleado in enumerate(empleados):
                # Determinar tags: 'inactive' para inactivos; zebra para activos
                estado_inactivo = not empleado.get('activo', True)
                zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
                tags_to_apply = ("inactive",) if estado_inactivo else (zebra_tag,)
                
                # Insertar en tree
                item_id = self.empleados_tree.insert(
                    "", "end",
                    text=empleado.get('nombre_completo', ''),
                    values=(
                        empleado.get('codigo', ''),
                        empleado.get('cedula', ''),
                        empleado.get('cargo', ''),
                        empleado.get('departamento', ''),
                        empleado.get('email', ''),
                        empleado.get('telefono', '')
                    ),
                    tags=tags_to_apply
                )
                
                # Guardar datos completos en un mapa auxiliar
                self._item_data[item_id] = empleado.copy()
            
            # Configurar colores por estado:
            # - Activos: verde claro (zebra)
            # - Inactivos: gris
            self.empleados_tree.tag_configure("inactive", background="#F5F5F5", foreground="#616161")  # Inactivo (gris claro)
            self.empleados_tree.tag_configure("zebra_even", background="#E8F5E9", foreground="#1B5E20") # Activo (par, verde)
            self.empleados_tree.tag_configure("zebra_odd", background="#C8E6C9", foreground="#1B5E20")  # Activo (impar, verde)
        except Exception as e:
            self.logger.error(f"Error actualizando visualización de empleados: {e}")
    
    def _update_statistics(self, data: Dict[str, Any]):
        """Actualiza las estadísticas mostradas"""
        try:
            total = data.get('total', 0)
            statistics = data.get('statistics', {})
            by_department = data.get('by_department', {})
            
            # Estadísticas principales
            stats_text = f"Total: {total} empleados"
            
            activos = statistics.get('empleados_activos', 0)
            if activos != total:
                stats_text += f" ({activos} activos)"
            
            # Estadísticas simplificadas sin clasificaciones de tiempo
            
            self.stats_label.config(text=stats_text)
            
            # Estadísticas por departamento
            if by_department:
                dept_stats = f"Departamentos: {len(by_department)}"
                if len(by_department) <= 3:
                    # Mostrar nombres si son pocos
                    dept_names = list(by_department.keys())[:3]
                    dept_stats += f" ({', '.join(dept_names)})"
                
                self.department_stats_label.config(text=dept_stats)
            
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas de empleados: {e}")
    
    def _on_search_changed(self, event=None):
        """Maneja cambio en el campo de búsqueda"""
        # Aplicar filtros con delay
        if hasattr(self, '_search_timer'):
            self.frame.after_cancel(self._search_timer)
        
        self._search_timer = self.frame.after(500, self._apply_filters)
    
    def _on_filter_changed(self, event=None):
        """Maneja cambio en los filtros"""
        self._apply_filters()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        log_user_action("CLICK", "clear_filters", "EmpleadosTab")
        
        self.filter_search.set("")
        self.filter_departamento.set("Todos")
        self.filter_status.set("Todos")
        
        self._apply_filters()
    
    def _on_empleado_selected(self, event=None):
        """Maneja la selección de un empleado"""
        selection = self.empleados_tree.selection()
        
        if selection:
            selected_item = selection[0]
            
            # Cargar datos en formulario
            self._load_empleado_to_form(selected_item)
            
            # Mostrar botones de edición (evitar usar 'before' si no están empacados aún)
            if not self.view_deliveries_btn.winfo_ismapped():
                self.view_deliveries_btn.pack(side=LEFT, padx=(0, 5))
            if not self.delete_btn.winfo_ismapped():
                self.delete_btn.pack(side=LEFT, padx=(0, 5))
            
            # Cambiar modo del formulario
            self.form_mode_label.config(text="Editar Empleado", bootstyle="warning")
            
        else:
            # Ocultar botones de edición
            self.view_deliveries_btn.pack_forget()
            self.delete_btn.pack_forget()
            self.delete_btn.pack_forget()
            
            # Cambiar a modo agregar
            self.form_mode_label.config(text="Nuevo Empleado", bootstyle="success")
    
    def _load_empleado_to_form(self, tree_item):
        """Carga datos de un empleado en el formulario"""
        try:
            # Datos completos desde el almacenamiento auxiliar
            data = self._item_data.get(tree_item, {})
            self.selected_empleado = data.copy()
            
            # Cargar valores principales al formulario
            self.form_id.set(str(data.get("id", "")))          # Interno
            self.form_codigo.set(data.get("codigo", ""))        # Público
            nombre = data.get("nombre_completo") or self.empleados_tree.item(tree_item, "text") or ""
            self.form_nombre_completo.set(nombre)
            self.form_cedula.set(data.get("cedula", ""))
            self.form_cargo.set(data.get("cargo", ""))
            self.form_departamento.set(data.get("departamento", ""))
            self.form_email.set(data.get("email", ""))
            self.form_telefono.set(data.get("telefono", ""))
            # Estado y nota
            self.form_activo.set(bool(data.get("activo", True)))
            nota_val = data.get("nota", "")
            self.form_nota.set(nota_val)
            # Sincronizar widget de nota
            try:
                self.form_nota_text.delete("1.0", tk.END)
                if nota_val:
                    self.form_nota_text.insert("1.0", nota_val)
            except Exception:
                pass
            
            # Actualizar información adicional
            self._update_employee_info_display(tree_item)
            
        except Exception as e:
            self.logger.error(f"Error cargando empleado al formulario: {e}")
    
    def _update_employee_info_display(self, tree_item):
        """Actualiza la información adicional del empleado"""
        try:
            # Datos completos desde el almacenamiento auxiliar
            empleado_data = self._item_data.get(tree_item, {})
            if not empleado_data:
                # Fallback a valores visibles si no se encontró en el mapa auxiliar
                empleado_data = {
                    "codigo": self.empleados_tree.set(tree_item, "Código"),
                    "nombre_completo": self.empleados_tree.item(tree_item, "text"),
                    "cargo": self.empleados_tree.set(tree_item, "Cargo"),
                    "departamento": self.empleados_tree.set(tree_item, "Departamento"),
                    "cedula": self.empleados_tree.set(tree_item, "Cédula"),
                    "email": self.empleados_tree.set(tree_item, "Email"),
                    "telefono": self.empleados_tree.set(tree_item, "Teléfono"),
                }
            
            emp_obj = Empleado.from_dict(empleado_data)
            
            # Generar información
            info_text = ""
            
            # Información básica del empleado
            info_text += f"👤 Empleado registrado en el sistema\n"
            
            # Estado del empleado
            if getattr(emp_obj, "can_receive_supplies", None) and emp_obj.can_receive_supplies():
                info_text += "✅ Puede recibir insumos\n"
                self.employee_status_label.config(text="✅ Activo para entregas", bootstyle="success")
            else:
                info_text += "❌ No puede recibir insumos\n"
                self.employee_status_label.config(text="❌ Inactivo para entregas", bootstyle="danger")
            
            # Información de contacto
            if getattr(emp_obj, "has_contact_info", None) and emp_obj.has_contact_info():
                info_text += f"📞 Contacto: {emp_obj.get_contact_summary()}\n"
            else:
                info_text += "📞 Sin información de contacto\n"
            
            # Nota
            nota_txt = (empleado_data.get('nota') or '').strip()
            info_text += f"📝 Nota: {nota_txt if nota_txt else 'Sin nota'}\n"
            
            # Actualizar display
            self.info_text.config(state="normal")
            self.info_text.delete("1.0", tk.END)
            self.info_text.insert("1.0", info_text)
            self.info_text.config(state="disabled")
            
        except Exception as e:
            self.logger.error(f"Error actualizando información del empleado: {e}")
        
    def _update_nota_var(self, event=None):
        """Actualiza la variable de nota desde el widget Text."""
        try:
            content = self.form_nota_text.get("1.0", tk.END).strip()
            self.form_nota.set(content)
        except Exception as e:
            self.logger.debug(f"Error actualizando nota: {e}")
        
    def show_add_form(self):
        """Muestra el formulario para agregar nuevo empleado"""
        log_user_action("SHOW_ADD_FORM", "new_empleado", "EmpleadosTab")
        
        # Limpiar selección del tree
        self.empleados_tree.selection_remove(self.empleados_tree.selection())
        
        # Limpiar formulario
        self._clear_form()
        
        # Enfocar campo de nombre
        self.form_nombre_entry.focus_set()
    
    def _clear_form(self):
        """Limpia el formulario"""
        log_user_action("CLEAR_FORM", "form_cleared", "EmpleadosTab")
        
        self.form_id.set("")
        self.form_nombre_completo.set("")
        self.form_cargo.set("")
        self.form_departamento.set("")
        self.form_cedula.set("")
        self.form_email.set("")
        self.form_telefono.set("")
        self.form_activo.set(True)
        self.form_nota.set("")
        # Limpiar widget Nota si existe
        try:
            self.form_nota_text.delete("1.0", tk.END)
        except Exception:
            pass
        # Fecha de ingreso eliminada
        
        self.selected_empleado = None
        
        # Ocultar botones de edición
        self.view_deliveries_btn.pack_forget()
        
        # Cambiar modo
        self.form_mode_label.config(text="Nuevo Empleado", bootstyle="success")
        
        # Limpiar información adicional
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.config(state="disabled")
        self.employee_status_label.config(text="")
    
    def _cancel_form(self):
        """Cancela la edición actual"""
        log_user_action("CANCEL_FORM", "form_cancelled", "EmpleadosTab")
        
        # Limpiar selección
        self.empleados_tree.selection_remove(self.empleados_tree.selection())
        
        # Limpiar formulario
        self._clear_form()
    
    def _save_empleado(self):
        """Guarda el empleado (nuevo o editado)"""
        try:
            # Preparar datos del formulario
            # Sincronizar nota desde el widget
            self._update_nota_var()
            form_data = {
                'nombre_completo': self.form_nombre_completo.get().strip(),
                'cargo': self.form_cargo.get().strip(),
                'departamento': self.form_departamento.get().strip(),
                'cedula': self.form_cedula.get().strip(),
                'email': self.form_email.get().strip(),
                'telefono': self.form_telefono.get().strip(),
                'activo': bool(self.form_activo.get()),
                'nota': self.form_nota.get().strip()
            }
            
            # Validar datos básicos
            if not form_data['nombre_completo']:
                show_error_message("Error", "El nombre completo es obligatorio", self.frame)
                self.form_nombre_entry.focus_set()
                return
            
            if not form_data['cedula']:
                show_error_message("Error", "La cédula es obligatoria", self.frame)
                self.form_cedula_entry.focus_set()
                return
            
            # Determinar si es creación o actualización
            is_update = bool(self.selected_empleado and self.form_id.get())
            
            if hasattr(self.app, 'update_status'):
                action = "Actualizando" if is_update else "Creando"
                self.app.update_status(f"{action} empleado...")
            
            if is_update:
                # Actualizar empleado existente
                empleado_id = int(self.form_id.get())
                result = micro_empleados.actualizar_empleado(empleado_id, form_data)
                
                log_user_action("UPDATE_EMPLEADO", "empleado_updated", f"ID: {empleado_id}")
            else:
                # Crear nuevo empleado
                result = micro_empleados.crear_empleado(form_data)
                
                log_user_action("CREATE_EMPLEADO", "empleado_created", f"Nombre: {form_data['nombre_completo']}")
            
            if result['success']:
                action_text = "actualizado" if is_update else "creado"
                
                if hasattr(self.app, 'update_status'):
                    self.app.update_status(f"Empleado {action_text} exitosamente", "success")
                
                show_info_message("Operación Exitosa", result['message'], self.frame)
                
                # Actualizar lista y limpiar formulario
                self.refresh_data()
                self._clear_form()
                
            else:
                if hasattr(self.app, 'update_status'):
                    self.app.update_status("Error guardando empleado", "danger")
                show_error_message("Error", "No se pudo guardar el empleado", self.frame)
                
        except ValidationException as e:
            show_error_message("Error de Validación", f"Error en el campo '{e.field}': {e.message}", self.frame)
            
        except DuplicateRecordException as e:
            show_error_message("Empleado Duplicado", e.message, self.frame)
            self.form_cedula_entry.focus_set()
            
        except Exception as e:
            self.logger.error(f"Error guardando empleado: {e}")
            if hasattr(self.app, 'update_status'):
                self.app.update_status("Error guardando empleado", "danger")
            show_error_message("Error", f"Error guardando empleado: {str(e)}", self.frame)
    
    def _edit_selected_empleado(self):
        """Edita el empleado seleccionado (doble click)"""
        log_user_action("DOUBLE_CLICK", "edit_empleado", "EmpleadosTab")
        
        if self.selected_empleado:
            self.form_nombre_entry.focus_set()
    
    def _delete_empleado(self):
        """Elimina el empleado seleccionado"""
        if not self.selected_empleado:
            return

        try:
            empleado_nombre = self.form_nombre_completo.get()

            # Confirmar eliminación
            if ask_yes_no(
                "Confirmar Eliminación",
                f"¿Está seguro que desea eliminar el empleado?\n\n{empleado_nombre}\n\n"
                f"El empleado será eliminado permanentemente del sistema.",
                self.frame
            ):
                empleado_id = int(self.form_id.get())
                result = micro_empleados.eliminar_empleado(empleado_id, soft_delete=False)

                if result['success']:
                    show_info_message("Empleado Eliminado", result['message'], self.frame)

                    # Actualizar lista y limpiar formulario
                    self.refresh_data()
                    self._clear_form()

                    log_user_action("DELETE_EMPLEADO", "empleado_deleted", f"ID: {empleado_id}")

                    if hasattr(self.app, 'update_status'):
                        self.app.update_status("Empleado eliminado", "success")
                else:
                    show_error_message("Error", "No se pudo eliminar el empleado", self.frame)

        except Exception as e:
            self.logger.error(f"Error eliminando empleado: {e}")
            show_error_message("Error", f"Error eliminando empleado: {str(e)}", self.frame)

    def _view_employee_deliveries(self):
        """Muestra las entregas del empleado seleccionado"""
        if not self.selected_empleado:
            return

        log_user_action("CLICK", "view_employee_deliveries", "EmpleadosTab")

        # Cambiar al tab de entregas con filtro del empleado
        if hasattr(self.app, 'entregas_tab'):
            self.app.notebook.select(3)  # Tab de entregas
            empleado_id = int(self.form_id.get())
            self.app.entregas_tab.filter_by_employee(empleado_id, self.form_nombre_completo.get())
    