"""
DelegInsumos - Sistema de Gestión de Insumos de Oficina
"""
8
import sys
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# Verificar que estamos en el directorio correcto
sys.path.insert(0, str(Path(__file__).parent))

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    print("Error: ttkbootstrap no está instalado. Ejecute: pip install -r requirements.txt")
    sys.exit(1)

from config.config_manager import config
from database.migrations import initialize_database
from utils.logger import log_system_startup, log_system_shutdown, main_logger
from utils.helpers import center_window, show_error_message
from services.micro_alertas import verificar_todas_las_alertas

# Importar tabs de la interfaz
from ui.dashboard_tab import DashboardTab
from ui.insumos_tab import InsumosTab  
from ui.empleados_tab import EmpleadosTab
from ui.entregas_tab import EntregasTab
from ui.reportes_tab import ReportesTab


class DelegInsumosApp:
    """
    Aplicación principal del sistema DelegInsumos
    """
    
    def __init__(self):
        """Inicializa la aplicación principal"""
        
        # Configurar logging del sistema
        log_system_startup()
        main_logger.info("Iniciando DelegInsumos v1.0.0")
        
        try:
            # Obtener configuración de interfaz
            self.ui_config = config.get_ui_config()
            self.system_info = config.get_system_info()
            
            # Inicializar base de datos
            self._initialize_database()
            
            # Crear ventana principal
            self._create_main_window()
            
            # Crear interfaz
            self._create_interface()
            
            # Configurar eventos
            self._setup_event_handlers()
            
            # Verificar alertas al inicio
            self._check_startup_alerts()
            
            main_logger.info("DelegInsumos inicializado exitosamente")
            
        except Exception as e:
            main_logger.error(f"Error crítico inicializando aplicación: {e}")
            self._handle_startup_error(e)
    
    def _initialize_database(self):
        """Inicializa la base de datos del sistema"""
        try:
            main_logger.info("Inicializando base de datos...")
            
            # Ejecutar migraciones
            success = initialize_database()
            
            if not success:
                raise Exception("Error inicializando base de datos")
            
            main_logger.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            main_logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    def _create_main_window(self):
        """Crea y configura la ventana principal"""
        
        # Crear ventana principal con ttkbootstrap
        tema = self.ui_config.get('tema', 'cosmo')
        self.root = ttk.Window(themename=tema)
        
        # Configurar ventana
        self.root.title(f"{self.system_info['nombre']} v{self.system_info['version']}")
        self.root.iconify()  # Minimizar temporalmente durante carga
        
        # Dimensiones de la ventana
        width = self.ui_config.get('ventana_ancho', 1200)
        height = self.ui_config.get('ventana_altura', 800)
        
        # Centrar ventana en la pantalla
        center_window(self.root, width, height)
        
        # Configurar redimensionamiento
        resizable = self.ui_config.get('ventana_redimensionable', True)
        self.root.resizable(resizable, resizable)
        
        # Configurar estado mínimo
        self.root.state('normal')
        
        main_logger.info(f"Ventana principal creada: {width}x{height}")
    
    def _create_interface(self):
        """Crea la interfaz principal con tabs"""
        
        # Crear marco principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # Header con información del sistema
        self._create_header(main_frame)
        
        # Notebook principal para tabs
        self.notebook = ttk.Notebook(main_frame, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # Crear tabs
        self._create_tabs()
        
        # Footer con estado del sistema
        self._create_footer(main_frame)
        
        main_logger.info("Interfaz principal creada")
    
    def _create_header(self, parent):
        """Crea el header de la aplicación"""
        
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 10))
        
        # Título principal
        title_label = ttk.Label(
            header_frame,
            text=self.system_info['nombre'],
            font=("Helvetica", 18, "bold"),
            bootstyle="primary"
        )
        title_label.pack(side=LEFT)
        
        # Información del sistema
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side=RIGHT)
        
        version_label = ttk.Label(
            info_frame,
            text=f"v{self.system_info['version']}",
            font=("Helvetica", 10),
            bootstyle="secondary"
        )
        version_label.pack(side=TOP, anchor=E)
        
        self.status_label = ttk.Label(
            info_frame,
            text="Sistema listo",
            font=("Helvetica", 9),
            bootstyle="success"
        )
        self.status_label.pack(side=TOP, anchor=E)
        
        main_logger.debug("Header creado")
    
    def _create_tabs(self):
        """Crea todos los tabs de la aplicación"""
        
        try:
            # Tab 1: Dashboard principal
            self.dashboard_tab = DashboardTab(self.notebook, self)
            self.notebook.add(self.dashboard_tab.frame, text="📊 Dashboard", sticky="nsew")
            
            # Tab 2: Gestión de insumos
            self.insumos_tab = InsumosTab(self.notebook, self)
            self.notebook.add(self.insumos_tab.frame, text="📦 Insumos", sticky="nsew")
            
            # Tab 3: Gestión de empleados
            self.empleados_tab = EmpleadosTab(self.notebook, self)
            self.notebook.add(self.empleados_tab.frame, text="👥 Empleados", sticky="nsew")
            
            # Tab 4: Registro de entregas
            self.entregas_tab = EntregasTab(self.notebook, self)
            self.notebook.add(self.entregas_tab.frame, text="📋 Entregas", sticky="nsew")
            
            # Tab 5: Reportes
            self.reportes_tab = ReportesTab(self.notebook, self)
            self.notebook.add(self.reportes_tab.frame, text="📄 Reportes", sticky="nsew")
            
            # Configurar grid del notebook
            for i in range(5):
                self.notebook.tab(i, sticky="nsew")
            
            main_logger.info("Tabs de la interfaz creados")
            
        except Exception as e:
            main_logger.error(f"Error creando tabs: {e}")
            raise
    
    def _create_footer(self, parent):
        """Crea el footer con información de estado"""
        
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(fill=X, pady=(10, 0))
        
        # Separador visual
        separator = ttk.Separator(footer_frame, orient=HORIZONTAL, bootstyle="primary")
        separator.pack(fill=X, pady=(0, 5))
        
        # Frame para información de estado
        status_frame = ttk.Frame(footer_frame)
        status_frame.pack(fill=X)
        
        # Información de base de datos
        db_info = config.get_database_config()
        db_status = ttk.Label(
            status_frame,
            text=f"BD: {Path(db_info.get('archivo', '')).name}",
            font=("Helvetica", 8),
            bootstyle="info"
        )
        db_status.pack(side=LEFT)
        
        # Información de alertas (se actualizará dinámicamente)
        self.alerts_status = ttk.Label(
            status_frame,
            text="Verificando alertas...",
            font=("Helvetica", 8),
            bootstyle="warning"
        )
        self.alerts_status.pack(side=LEFT, padx=(20, 0))
        
        # Tiempo actual
        self.time_label = ttk.Label(
            status_frame,
            text="",
            font=("Helvetica", 8),
            bootstyle="secondary"
        )
        self.time_label.pack(side=RIGHT)
        
        # Actualizar reloj
        self._update_time()
        
        main_logger.debug("Footer creado")
    
    def _setup_event_handlers(self):
        """Configura manejadores de eventos de la aplicación"""
        
        # Evento de cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Evento de cambio de tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Eventos de teclado globales
        self.root.bind("<F5>", self._refresh_all_data)
        self.root.bind("<Control-q>", lambda e: self._on_closing())
        self.root.bind("<Control-b>", lambda e: self._create_manual_backup())
        
        main_logger.debug("Manejadores de eventos configurados")
    
    def _check_startup_alerts(self):
        """Verifica alertas al inicio de la aplicación"""
        try:
            # Verificar alertas en hilo separado para no bloquear la UI
            self.root.after(2000, self._verify_alerts_async)
            
        except Exception as e:
            main_logger.warning(f"Error verificando alertas al inicio: {e}")
    
    def _verify_alerts_async(self):
        """Verifica alertas de forma asíncrona"""
        try:
            alert_result = verificar_todas_las_alertas()
            total_alerts = alert_result.get('total_new_alerts', 0)
            
            # Actualizar estado en footer
            if total_alerts > 0:
                self.alerts_status.config(
                    text=f"⚠️ {total_alerts} alertas activas",
                    bootstyle="danger"
                )
            else:
                self.alerts_status.config(
                    text="✅ Sin alertas críticas",
                    bootstyle="success"
                )
            
            # Actualizar dashboard si está visible
            current_tab = self.notebook.select()
            if current_tab == str(self.dashboard_tab.frame):
                self.dashboard_tab.refresh_data()
            
        except Exception as e:
            main_logger.warning(f"Error en verificación de alertas asíncrona: {e}")
            self.alerts_status.config(
                text="❌ Error verificando alertas",
                bootstyle="warning"
            )
    
    def _update_time(self):
        """Actualiza el reloj en el footer"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.config(text=current_time)
        
        # Programar próxima actualización
        self.root.after(1000, self._update_time)
    
    def _on_tab_changed(self, event):
        """Maneja el cambio de tab"""
        try:
            selected_tab = event.widget.select()
            tab_text = event.widget.tab(selected_tab, "text")
            
            main_logger.debug(f"Tab cambiado a: {tab_text}")
            
            # Refrescar datos del tab actual
            if hasattr(self, 'dashboard_tab') and selected_tab == str(self.dashboard_tab.frame):
                self.dashboard_tab.refresh_data()
            elif hasattr(self, 'insumos_tab') and selected_tab == str(self.insumos_tab.frame):
                self.insumos_tab.refresh_data()
            elif hasattr(self, 'empleados_tab') and selected_tab == str(self.empleados_tab.frame):
                self.empleados_tab.refresh_data()
            elif hasattr(self, 'entregas_tab') and selected_tab == str(self.entregas_tab.frame):
                self.entregas_tab.refresh_data()
            
        except Exception as e:
            main_logger.warning(f"Error manejando cambio de tab: {e}")
    
    def _refresh_all_data(self, event=None):
        """Refresca los datos de todos los tabs (F5)"""
        try:
            self.update_status("Actualizando datos...")
            
            # Refrescar tab actual
            current_tab_id = self.notebook.select()
            current_tab = self.notebook.nametowidget(current_tab_id)
            
            if hasattr(current_tab, 'refresh_data'):
                current_tab.refresh_data()
            
            # Verificar alertas nuevamente
            self._verify_alerts_async()
            
            self.update_status("Datos actualizados")
            
            main_logger.info("Datos de la aplicación refrescados")
            
        except Exception as e:
            main_logger.error(f"Error refrescando datos: {e}")
            self.update_status("Error actualizando datos")
    
    def _create_manual_backup(self):
        """Crea un backup manual (Ctrl+B)"""
        try:
            from services.backup_service import crear_backup_manual
            
            self.update_status("Creando backup...")
            
            result = crear_backup_manual("backup_usuario_manual")
            
            if result['success']:
                self.update_status("Backup creado exitosamente")
                messagebox.showinfo(
                    "Backup Exitoso",
                    f"Backup manual creado:\n{result['backup_info']['filename']}",
                    parent=self.root
                )
            else:
                self.update_status("Error creando backup")
                messagebox.showerror(
                    "Error de Backup",
                    "No se pudo crear el backup manual",
                    parent=self.root
                )
            
        except Exception as e:
            main_logger.error(f"Error creando backup manual: {e}")
            self.update_status("Error en backup")
            show_error_message("Error de Backup", f"Error creando backup: {str(e)}", self.root)
    
    def update_status(self, message: str, style: str = "info"):
        """
        Actualiza el mensaje de estado en el footer.
        
        Args:
            message: Mensaje a mostrar
            style: Estilo del mensaje (info, success, warning, danger)
        """
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message, bootstyle=style)
        
        main_logger.debug(f"Estado actualizado: {message}")
    
    def _on_closing(self):
        """Maneja el event o de cierre de la aplicación"""
        try:
            main_logger.info("Iniciando cierre de la aplicación")
            
            # Confirmar cierre
            if messagebox.askokcancel(
                "Cerrar DelegInsumos",
                "¿Está seguro que desea cerrar el sistema?",
                parent=self.root
            ):
                
                self.update_status("Cerrando sistema...")
                
                # Cerrar conexiones de base de datos
                from database.connection import db_connection
                db_connection.close_all_connections()
                
                # Detener timers de backup si existen
                from services.backup_service import backup_service
                backup_service.desactivar_backup_automatico()
                
                # Log de cierre del sistema
                log_system_shutdown()
                
                # Cerrar aplicación
                self.root.quit()
                self.root.destroy()
                
                print("DelegInsumos cerrado exitosamente")
                
        except Exception as e:
            main_logger.error(f"Error cerrando aplicación: {e}")
            self.root.quit()
            self.root.destroy()
    
    def _handle_startup_error(self, error: Exception):
        """
        Maneja errores críticos durante el inicio.
        
        Args:
            error: Error ocurrido
        """
        error_msg = f"Error crítico iniciando DelegInsumos:\n\n{str(error)}\n\nRevise los logs para más detalles."
        
        # Mostrar error al usuario
        root_temp = tk.Tk()
        root_temp.withdraw()
        
        messagebox.showerror(
            "Error Crítico - DelegInsumos",
            error_msg,
            parent=root_temp
        )
        
        root_temp.destroy()
        
        # Log del error y salir
        main_logger.critical(f"Error crítico de inicio: {error}")
        main_logger.critical(f"Stack trace: {traceback.format_exc()}")
        
        sys.exit(1)
    
    def run(self):
        """Inicia la aplicación"""
        try:
            # Mostrar ventana
            self.root.deiconify()  # Restaurar ventana
            self.root.lift()       # Traer al frente
            self.root.focus_force()  # Dar foco
            
            main_logger.info("Ventana principal mostrada - Sistema listo")
            self.update_status("Sistema listo para usar", "success")
            
            # Iniciar loop principal de tkinter
            self.root.mainloop()
            
        except KeyboardInterrupt:
            main_logger.info("Aplicación interrumpida por usuario (Ctrl+C)")
            self._on_closing()
            
        except Exception as e:
            main_logger.error(f"Error en loop principal: {e}")
            self._handle_startup_error(e)


def check_dependencies():
    """Verifica que todas las dependencias estén instaladas"""
    missing_deps = []
    
    try:
        import reportlab
    except ImportError:
        missing_deps.append("reportlab")
    
    try:
        import openpyxl
    except ImportError:
        missing_deps.append("openpyxl")
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import matplotlib
    except ImportError:
        missing_deps.append("matplotlib")
    
    if missing_deps:
        print("[ERROR] Dependencias faltantes:", ", ".join(missing_deps))
        print("[INFO] Ejecute: pip install -r requirements.txt")
        return False

    print("[OK] Todas las dependencias estan instaladas")
    return True


def main():
    """Función principal de la aplicación"""

    print("[START] Iniciando DelegInsumos...")
    print("[INFO] Sistema de Gestion de Insumos de Oficina")
    print("=" * 50)
    
    # Verificar dependencias
    if not check_dependencies():
        input("Presione Enter para salir...")
        sys.exit(1)
    
    try:
        # Crear y ejecutar aplicación
        app = DelegInsumosApp()
        app.run()
        
    except KeyboardInterrupt:
        print("\n[STOP] Aplicacion interrumpida por el usuario")

    except Exception as e:
        print(f"\n[ERROR] Error critico: {e}")
        print("[INFO] Revise el archivo de logs para mas detalles")
        input("Presione Enter para salir...")
        sys.exit(1)


if __name__ == "__main__":
    main()