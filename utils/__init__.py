"""
DelegInsumos - Utilidades del Sistema
Módulo de utilidades compartidas para el sistema DelegInsumos
"""

import re
import datetime
import random
import string
from typing import Optional
from utils.helpers import generar_id as _helpers_generar_id


def safe_filename(prefix: str = "backup") -> str:
    """
    Genera un nombre de archivo seguro para backups.

    Args:
        prefix: Prefijo para el nombre del archivo

    Returns:
        Nombre de archivo seguro con timestamp
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', prefix)
    return f"{safe_prefix}_{timestamp}.db"


def generar_id(prefijo: str, longitud: int = 6) -> str:
    """
    Genera un ID legible delegando al generador central en utils.helpers.

    Patrones requeridos:
      - INS → INS-YYYY-XXXX
      - EMP → EMP-REG-XXXX
      - ENT → ENT-XXXX

    Nota: El parámetro 'longitud' se mantiene por compatibilidad y no se usa.
    """
    p = (prefijo or "").upper()
    if p == "INS":
        return _helpers_generar_id("INS", include_year=True)
    if p == "EMP":
        return _helpers_generar_id("EMP-REG", include_year=False)
    if p == "ENT":
        return _helpers_generar_id("ENT", include_year=False)
    # Fallback: incluir año por defecto
    return _helpers_generar_id(prefijo, include_year=True)


# Funciones de compatibilidad para widgets DateEntry
def set_date_entry_value(entry_widget, date_value):
    """
    Establece el valor de un widget de fecha de forma compatible.

    Args:
        entry_widget: Widget Entry o DateEntry
        date_value: Valor de fecha (date, datetime o string)
    """
    try:
        # Intentar como DateEntry primero
        if hasattr(entry_widget, 'set_date'):
            if isinstance(date_value, str):
                date_obj = datetime.datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            elif isinstance(date_value, datetime.datetime):
                date_obj = date_value.date()
            else:
                date_obj = date_value
            entry_widget.set_date(date_obj)
        else:
            # Como Entry normal
            if isinstance(date_value, (datetime.date, datetime.datetime)):
                date_str = date_value.strftime('%Y-%m-%d')
            else:
                date_str = str(date_value)
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, date_str)
    except Exception:
        # Fallback: usar string simple
        entry_widget.delete(0, 'end')
        entry_widget.insert(0, str(date_value))


def get_date_entry_value(entry_widget):
    """
    Obtiene el valor de un widget de fecha de forma compatible.

    Args:
        entry_widget: Widget Entry o DateEntry

    Returns:
        Valor de fecha como objeto date
    """
    try:
        # Intentar como DateEntry primero
        if hasattr(entry_widget, 'get_date'):
            return entry_widget.get_date()
        else:
            # Como Entry normal
            date_str = entry_widget.get().strip()
            if date_str:
                return datetime.datetime.fromisoformat(date_str).date()
            else:
                return datetime.date.today()
    except Exception:
        # Fallback: fecha actual
        return datetime.date.today()