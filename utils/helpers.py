"""
DelegInsumos - Utilidades Compartidas
Funciones auxiliares para uso general en todo el sistema
"""

import os
import shutil
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import tkinter as tk
from tkinter import messagebox, filedialog
import json


def format_currency(amount: Union[int, float, str]) -> str:
    """
    Formatea un monto como moneda colombiana.
    
    Args:
        amount: Monto a formatear
        
    Returns:
        String formateado como moneda (ej: "$1.234,56")
    """
    try:
        num_amount = float(amount)
        return f"${num_amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "$0,00"


def format_date(date_obj: Optional[datetime], format_type: str = "short") -> str:
    """
    Formatea una fecha según el tipo especificado.
    
    Args:
        date_obj: Objeto datetime a formatear
        format_type: Tipo de formato ("short", "long", "iso")
        
    Returns:
        Fecha formateada como string
    """
    if not date_obj:
        return ""
    
    if format_type == "short":
        return date_obj.strftime("%d/%m/%Y")
    elif format_type == "long":
        return date_obj.strftime("%d de %B de %Y")
    elif format_type == "iso":
        return date_obj.strftime("%Y-%m-%d")
    elif format_type == "datetime":
        return date_obj.strftime("%d/%m/%Y %H:%M")
    else:
        return date_obj.strftime("%d/%m/%Y")


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parsea una fecha desde string a datetime.
    
    Args:
        date_str: String de fecha a parsear
        
    Returns:
        Objeto datetime o None si no se puede parsear
    """
    if not date_str:
        return None
    
    # Formatos soportados
    formats = [
        "%Y-%m-%d",        # 2024-01-15
        "%d/%m/%Y",        # 15/01/2024
        "%d-%m-%Y",        # 15-01-2024
        "%Y-%m-%d %H:%M:%S"  # 2024-01-15 14:30:00
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def safe_filename(filename: str) -> str:
    """
    Convierte un string en un nombre de archivo seguro.
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo seguro
    """
    # Caracteres no permitidos en nombres de archivo
    invalid_chars = '<>:"/\\|?*'
    
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remover espacios múltiples y al inicio/final
    safe_name = ' '.join(safe_name.split())
    
    return safe_name[:100]  # Limitar longitud


def create_backup_filename(base_name: str, extension: str = "db") -> str:
    """
    Crea un nombre de archivo para backup con timestamp.
    
    Args:
        base_name: Nombre base del archivo
        extension: Extensión del archivo
        
    Returns:
        Nombre de archivo con timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"


def get_file_size_mb(filepath: str) -> float:
    """
    Obtiene el tamaño de un archivo en MB.
    
    Args:
        filepath: Ruta del archivo
        
    Returns:
        Tamaño en MB
    """
    try:
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def cleanup_old_files(directory: str, max_age_days: int = 30, 
                      file_pattern: str = "*") -> int:
    """
    Limpia archivos antiguos de un directorio.
    
    Args:
        directory: Directorio a limpiar
        max_age_days: Edad máxima en días para conservar archivos
        file_pattern: Patrón de archivos a limpiar
        
    Returns:
        Número de archivos eliminados
    """
    if not os.path.exists(directory):
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0
    
    try:
        directory_path = Path(directory)
        for file_path in directory_path.glob(file_pattern):
            if file_path.is_file():
                file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_modified < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
    except Exception as e:
        print(f"Error limpiando archivos antiguos: {e}")
    
    return deleted_count


def show_info_message(title: str, message: str, parent: tk.Widget = None):
    """
    Muestra un mensaje informativo.
    
    Args:
        title: Título del mensaje
        message: Contenido del mensaje
        parent: Widget padre (opcional)
    """
    messagebox.showinfo(title, message, parent=parent)


def show_error_message(title: str, message: str, parent: tk.Widget = None):
    """
    Muestra un mensaje de error.
    
    Args:
        title: Título del mensaje
        message: Contenido del mensaje
        parent: Widget padre (opcional)
    """
    messagebox.showerror(title, message, parent=parent)


def show_warning_message(title: str, message: str, parent: tk.Widget = None):
    """
    Muestra un mensaje de advertencia.
    
    Args:
        title: Título del mensaje
        message: Contenido del mensaje
        parent: Widget padre (opcional)
    """
    messagebox.showwarning(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent: tk.Widget = None) -> bool:
    """
    Muestra un diálogo de confirmación Sí/No.
    
    Args:
        title: Título del diálogo
        message: Mensaje de confirmación
        parent: Widget padre (opcional)
        
    Returns:
        True si el usuario seleccionó Sí, False si seleccionó No
    """
    return messagebox.askyesno(title, message, parent=parent)


def select_save_file(title: str, initial_name: str = "", 
                    file_types: List[tuple] = None, 
                    parent: tk.Widget = None) -> Optional[str]:
    """
    Abre un diálogo para guardar archivo.
    
    Args:
        title: Título del diálogo
        initial_name: Nombre inicial sugerido
        file_types: Lista de tipos de archivo [(descripción, extensión)]
        parent: Widget padre (opcional)
        
    Returns:
        Ruta del archivo seleccionado o None si se canceló
    """
    if file_types is None:
        file_types = [("Todos los archivos", "*.*")]
    
    return filedialog.asksaveasfilename(
        title=title,
        initialname=initial_name,
        filetypes=file_types,
        parent=parent
    )


def select_open_file(title: str, file_types: List[tuple] = None, 
                    parent: tk.Widget = None) -> Optional[str]:
    """
    Abre un diálogo para seleccionar archivo.
    
    Args:
        title: Título del diálogo
        file_types: Lista de tipos de archivo [(descripción, extensión)]
        parent: Widget padre (opcional)
        
    Returns:
        Ruta del archivo seleccionado o None si se canceló
    """
    if file_types is None:
        file_types = [("Todos los archivos", "*.*")]
    
    return filedialog.askopenfilename(
        title=title,
        filetypes=file_types,
        parent=parent
    )


def center_window(window: tk.Toplevel, width: int, height: int):
    """
    Centra una ventana en la pantalla.
    
    Args:
        window: Ventana a centrar
        width: Ancho de la ventana
        height: Alto de la ventana
    """
    # Obtener dimensiones de la pantalla
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Calcular posición centrada
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Trunca texto si excede la longitud máxima.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima permitida
        suffix: Sufijo a agregar si se trunca
        
    Returns:
        Texto truncado
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def export_to_json(data: Dict[str, Any], filepath: str) -> bool:
    """
    Exporta datos a archivo JSON.
    
    Args:
        data: Datos a exportar
        filepath: Ruta del archivo destino
        
    Returns:
        True si la exportación fue exitosa
    """
    try:
        # Crear directorio si no existe
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False, default=str)
        
        return True
    except Exception as e:
        print(f"Error exportando a JSON: {e}")
        return False


def import_from_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Importa datos desde archivo JSON.
    
    Args:
        filepath: Ruta del archivo fuente
        
    Returns:
        Datos importados o None si hubo error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error importando desde JSON: {e}")
        return None


def calculate_stock_percentage(current: int, maximum: int) -> float:
    """
    Calcula el porcentaje de stock actual respecto al máximo.
    
    Args:
        current: Cantidad actual
        maximum: Cantidad máxima
        
    Returns:
        Porcentaje de stock (0.0 - 1.0)
    """
    if maximum <= 0:
        return 0.0
    
    return min(current / maximum, 1.0)


def get_stock_status(current: int, minimum: int, maximum: int) -> Dict[str, Any]:
    """
    Determina el estado del stock de un insumo.
    
    Args:
        current: Cantidad actual
        minimum: Cantidad mínima
        maximum: Cantidad máxima
        
    Returns:
        Diccionario con estado del stock
    """
    if current <= 0:
        status = "CRITICO"
        color = "#F44336"  # Rojo
        message = "Sin stock disponible"
    elif current <= minimum:
        status = "BAJO"
        color = "#FF9800"  # Naranja
        message = "Stock por debajo del mínimo"
    elif current >= maximum:
        status = "EXCESO"
        color = "#9E9E9E"  # Gris
        message = "Stock por encima del máximo"
    else:
        status = "NORMAL"
        color = "#4CAF50"  # Verde
        message = "Stock en nivel normal"
    
    percentage = calculate_stock_percentage(current, maximum)
    
    return {
        "status": status,
        "color": color,
        "message": message,
        "percentage": percentage,
        "needs_attention": status in ["CRITICO", "BAJO", "EXCESO"]
    }


def validate_positive_integer(value: str) -> Optional[int]:
    """
    Valida que un string sea un entero positivo.
    
    Args:
        value: String a validar
        
    Returns:
        Entero validado o None si no es válido
    """
    try:
        int_val = int(value)
        return int_val if int_val >= 0 else None
    except ValueError:
        return None


def copy_file_safe(source: str, destination: str) -> bool:
    """
    Copia un archivo de forma segura, creando directorios si es necesario.
    
    Args:
        source: Archivo fuente
        destination: Archivo destino
        
    Returns:
        True si la copia fue exitosa
    """
    try:
        # Crear directorio destino si no existe
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        print(f"Error copiando archivo: {e}")
        return False


# Constantes útiles para la aplicación
CATEGORIAS_INSUMOS = [
    "Papelería",
    "Tecnología",
    "Limpieza",
    "Oficina",
    "Seguridad",
    "Cocina",
    "Otros"
]

UNIDADES_MEDIDA = [
    "Unidad",
    "Caja",
    "Paquete", 
    "Resma",
    "Litro",
    "Kilogramo",
    "Bolsa",
    "Rollo",
    "Cartucho"
]

DEPARTAMENTOS = [
    "Delegados Departamentales",
    "Archivos Central",
    "Talento Humanos",
    "Recepción Y Correspondencia",
    "Almacen e Inventario",
    "Cobro Coactivo",
    "Jurídica",
    "Ambiental",
    "Registro Civil e Identificación",
    "Centro de las Nuevas Tecnologías e IA",
    "Planeación",
    "Electoral",
    "Control Interno",
    "Administrativa y Financiero",
    "Prensa",
    "Bienestar",
    "Registraduria Municipales",
    "Nómina"

]

def generar_id(prefijo: str, include_year: bool = True) -> str:
    """
    Genera un ID alfanumérico legible para entidades del sistema.

    Patrones:
      - INS: INS-YYYY-XXXX (incluye año)
      - EMP: EMP-REG-XXXX (sin año, usar prefijo 'EMP-REG' y include_year=False)
      - ENT: ENT-XXXX (sin año)

    Args:
        prefijo: Prefijo del ID (por ejemplo 'INS', 'EMP-REG', 'ENT')
        include_year: Si incluir el año en el ID

    Returns:
        ID generado, por ejemplo:
        - INS-2025-4831 (include_year=True)
        - EMP-REG-5729 (include_year=False)
        - ENT-9134 (include_year=False)
    """
    year = datetime.now().year
    numero = random.randint(1000, 9999)
    return f"{prefijo}-{year}-{numero}" if include_year else f"{prefijo}-{numero}"