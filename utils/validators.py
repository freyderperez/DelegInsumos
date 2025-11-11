"""
DelegInsumos - Sistema de Validación de Datos
Valida la entrada de datos para garantizar integridad y seguridad
"""

import re
from typing import Any, Optional, List, Dict
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from exceptions.custom_exceptions import ValidationException


class DataValidator:
    """Validador centralizado de datos del sistema"""
    
    # Patrones regex para validación
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?[\d\s\-\(\)]{7,15}$')  
    CEDULA_PATTERN = re.compile(r'^\d{6,12}$')  # Cédula colombiana básica
    NAME_PATTERN = re.compile(r'^[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]{1,150}$')
    
    # Caracteres peligrosos para prevenir inyecciones
    DANGEROUS_CHARS = ['<', '>', '"', "'", '\\', ';', '--', '/*', '*/', 'DROP', 'DELETE']
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """
        Valida que un campo requerido no esté vacío.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo para el mensaje de error
            
        Returns:
            Valor validado
            
        Raises:
            ValidationException: Si el valor está vacío
        """
        if value is None or value == "":
            raise ValidationException(field_name, "Este campo es obligatorio")
        
        if isinstance(value, str) and value.strip() == "":
            raise ValidationException(field_name, "Este campo no puede estar vacío")
            
        return value
    
    @staticmethod
    def validate_string(value: Any, field_name: str, min_length: int = 0, 
                       max_length: int = 255, required: bool = True) -> str:
        """
        Valida un campo de texto.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_length: Longitud mínima
            max_length: Longitud máxima
            required: Si el campo es obligatorio
            
        Returns:
            String validado y sanitizado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return ""
        
        if not isinstance(value, str):
            value = str(value)
        
        # Sanitizar caracteres peligrosos
        value = DataValidator.sanitize_string(value)
        
        # Validar longitud
        if len(value) < min_length:
            raise ValidationException(
                field_name, 
                f"Debe tener al menos {min_length} caracteres"
            )
        
        if len(value) > max_length:
            raise ValidationException(
                field_name, 
                f"No debe exceder {max_length} caracteres"
            )
        
        return value.strip()
    
    @staticmethod
    def validate_integer(value: Any, field_name: str, min_val: Optional[int] = None, 
                        max_val: Optional[int] = None, required: bool = True) -> int:
        """
        Valida un campo numérico entero.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_val: Valor mínimo permitido
            max_val: Valor máximo permitido
            required: Si el campo es obligatorio
            
        Returns:
            Entero validado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return 0
        
        try:
            if isinstance(value, str):
                value = value.strip()
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationException(field_name, "Debe ser un número entero válido")
        
        if min_val is not None and int_value < min_val:
            raise ValidationException(
                field_name, 
                f"Debe ser mayor o igual a {min_val}"
            )
        
        if max_val is not None and int_value > max_val:
            raise ValidationException(
                field_name, 
                f"Debe ser menor o igual a {max_val}"
            )
        
        return int_value
    
    @staticmethod
    def validate_decimal(value: Any, field_name: str, min_val: Optional[float] = None, 
                        max_val: Optional[float] = None, decimal_places: int = 2, 
                        required: bool = True) -> Decimal:
        """
        Valida un campo decimal/monetario.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            min_val: Valor mínimo permitido
            max_val: Valor máximo permitido
            decimal_places: Número de decimales permitidos
            required: Si el campo es obligatorio
            
        Returns:
            Decimal validado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return Decimal('0.00')
        
        try:
            if isinstance(value, str):
                value = value.strip()
            decimal_value = Decimal(str(value))
        except InvalidOperation:
            raise ValidationException(field_name, "Debe ser un número decimal válido")
        
        if min_val is not None and decimal_value < Decimal(str(min_val)):
            raise ValidationException(
                field_name, 
                f"Debe ser mayor o igual a {min_val}"
            )
        
        if max_val is not None and decimal_value > Decimal(str(max_val)):
            raise ValidationException(
                field_name, 
                f"Debe ser menor o igual a {max_val}"
            )
        
        # Validar número de decimales
        if decimal_value.as_tuple().exponent < -decimal_places:
            raise ValidationException(
                field_name, 
                f"No puede tener más de {decimal_places} decimales"
            )
        
        return decimal_value.quantize(Decimal('0.01'))  # Redondear a 2 decimales
    
    @staticmethod
    def validate_email(value: Any, field_name: str, required: bool = False) -> str:
        """
        Valida un campo de email.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            required: Si el campo es obligatorio
            
        Returns:
            Email validado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return ""
        
        email = str(value).strip().lower()
        
        if not DataValidator.EMAIL_PATTERN.match(email):
            raise ValidationException(field_name, "Formato de email inválido")
        
        return email
    
    @staticmethod
    def validate_phone(value: Any, field_name: str, required: bool = False) -> str:
        """
        Valida un campo de teléfono.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            required: Si el campo es obligatorio
            
        Returns:
            Teléfono validado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return ""
        
        phone = str(value).strip()
        
        if not DataValidator.PHONE_PATTERN.match(phone):
            raise ValidationException(field_name, "Formato de teléfono inválido")
        
        return phone
    
    @staticmethod
    def validate_cedula(value: Any, field_name: str, required: bool = True) -> str:
        """
        Valida un número de cédula colombiana.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            required: Si el campo es obligatorio
            
        Returns:
            Cédula validada
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return ""
        
        cedula = str(value).strip()
        
        if not DataValidator.CEDULA_PATTERN.match(cedula):
            raise ValidationException(
                field_name, 
                "La cédula debe contener entre 6 y 12 dígitos"
            )
        
        return cedula
    
    @staticmethod
    def validate_date(value: Any, field_name: str, required: bool = False) -> Optional[date]:
        """
        Valida un campo de fecha.
        
        Args:
            value: Valor a validar (string, datetime, date)
            field_name: Nombre del campo
            required: Si el campo es obligatorio
            
        Returns:
            Fecha validada
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        # Intentar parsear string
        try:
            if isinstance(value, str):
                value = value.strip()
                # Formato esperado: YYYY-MM-DD
                return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
        
        raise ValidationException(field_name, "Formato de fecha inválido (use YYYY-MM-DD)")
    
    @staticmethod
    def validate_choice(value: Any, field_name: str, choices: List[str], 
                       required: bool = True) -> str:
        """
        Valida que un valor esté dentro de opciones permitidas.
        
        Args:
            value: Valor a validar
            field_name: Nombre del campo
            choices: Lista de opciones válidas
            required: Si el campo es obligatorio
            
        Returns:
            Valor validado
            
        Raises:
            ValidationException: Si la validación falla
        """
        if required:
            DataValidator.validate_required(value, field_name)
        elif value is None or value == "":
            return ""
        
        str_value = str(value).strip()
        
        if str_value not in choices:
            raise ValidationException(
                field_name, 
                f"Debe ser uno de: {', '.join(choices)}"
            )
        
        return str_value
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """
        Sanitiza un string removiendo caracteres peligrosos.
        
        Args:
            value: String a sanitizar
            
        Returns:
            String sanitizado
        """
        if not isinstance(value, str):
            return str(value)
        
        sanitized = value
        
        # Remover caracteres peligrosos
        for char in DataValidator.DANGEROUS_CHARS:
            sanitized = sanitized.replace(char, "")
        
        return sanitized


# Funciones de conveniencia para validaciones comunes

def validate_insumo_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida datos completos de un insumo.
    
    Args:
        data: Diccionario con datos del insumo
        
    Returns:
        Diccionario con datos validados
        
    Raises:
        ValidationException: Si algún campo no es válido
    """
    validator = DataValidator()
    
    return {
        'nombre': validator.validate_string(
            data.get('nombre'), 'nombre', min_length=1, max_length=100
        ),
        'categoria': validator.validate_string(
            data.get('categoria'), 'categoria', min_length=1, max_length=50
        ),
        'cantidad_actual': validator.validate_integer(
            data.get('cantidad_actual', 0), 'cantidad_actual', min_val=0
        ),
        'cantidad_minima': validator.validate_integer(
            data.get('cantidad_minima', 5), 'cantidad_minima', min_val=0
        ),
        'cantidad_maxima': validator.validate_integer(
            data.get('cantidad_maxima', 100), 'cantidad_maxima', min_val=1
        ),
        'unidad_medida': validator.validate_string(
            data.get('unidad_medida', 'unidad'), 'unidad_medida', max_length=20
        ),
        'precio_unitario': validator.validate_decimal(
            data.get('precio_unitario', 0), 'precio_unitario', min_val=0
        ),
        'proveedor': validator.validate_string(
            data.get('proveedor', ''), 'proveedor', max_length=100, required=False
        )
    }


def validate_empleado_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida datos completos de un empleado.
    
    Args:
        data: Diccionario con datos del empleado
        
    Returns:
        Diccionario con datos validados
        
    Raises:
        ValidationException: Si algún campo no es válido
    """
    validator = DataValidator()
    
    return {
        'nombre_completo': validator.validate_string(
            data.get('nombre_completo'), 'nombre_completo', min_length=2, max_length=150
        ),
        'cargo': validator.validate_string(
            data.get('cargo', ''), 'cargo', max_length=100, required=False
        ),
        'departamento': validator.validate_string(
            data.get('departamento', ''), 'departamento', max_length=100, required=False
        ),
        'cedula': validator.validate_cedula(
            data.get('cedula'), 'cedula'
        ),
        'email': validator.validate_email(
            data.get('email', ''), 'email', required=False
        ),
        'telefono': validator.validate_phone(
            data.get('telefono', ''), 'telefono', required=False
        ),
        'fecha_ingreso': validator.validate_date(
            data.get('fecha_ingreso'), 'fecha_ingreso', required=False
        )
    }


def validate_entrega_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida datos completos de una entrega.
    
    Args:
        data: Diccionario con datos de la entrega
        
    Returns:
        Diccionario con datos validados
        
    Raises:
        ValidationException: Si algún campo no es válido
    """
    validator = DataValidator()
    
    return {
        'empleado_id': validator.validate_integer(
            data.get('empleado_id'), 'empleado_id', min_val=1
        ),
        'insumo_id': validator.validate_integer(
            data.get('insumo_id'), 'insumo_id', min_val=1
        ),
        'cantidad': validator.validate_integer(
            data.get('cantidad'), 'cantidad', min_val=1
        ),
        'observaciones': validator.validate_string(
            data.get('observaciones', ''), 'observaciones', max_length=500, required=False
        ),
        'entregado_por': validator.validate_string(
            data.get('entregado_por', ''), 'entregado_por', max_length=100, required=False
        )
    }