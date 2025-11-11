"""
DelegInsumos - Gestor de Configuración
Maneja la carga y acceso a configuraciones del sistema desde settings.json
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """
    Gestor centralizado de configuración del sistema.
    Singleton para garantizar una única instancia de configuración.
    """
    
    _instance: Optional['ConfigManager'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> 'ConfigManager':
        """Implementación Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        """Carga la configuración desde el archivo settings.json"""
        try:
            config_path = Path(__file__).parent / 'settings.json'
            with open(config_path, 'r', encoding='utf-8') as file:
                self._config = json.load(file)
            print(f"[OK] Configuracion cargada desde: {config_path}")
        except FileNotFoundError:
            print(f"[ERROR] No se encontro el archivo settings.json")
            self._config = self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"[ERROR] Error al parsear settings.json: {e}")
            self._config = self._get_default_config()
        except Exception as e:
            print(f"[ERROR] Error inesperado cargando configuracion: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuración por defecto en caso de error"""
        return {
            "sistema": {
                "nombre": "DelegInsumos",
                "version": "1.0.0",
                "descripcion": "Sistema de Gestión de Insumos de Oficina"
            },
            "base_datos": {
                "archivo": "./data/deleginsumos.db",
                "backup_automatico": True
            },
            "interfaz": {
                "tema": "cosmo",
                "ventana_ancho": 1200,
                "ventana_altura": 800
            },
            "logging": {
                "nivel": "INFO",
                "archivo": "./logs/deleginsumos.log"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando notación de puntos.
        
        Args:
            key_path: Ruta de la clave (ej: "base_datos.archivo")
            default: Valor por defecto si no se encuentra la clave
            
        Returns:
            Valor de configuración o default
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def get_database_config(self) -> Dict[str, Any]:
        """Configuración específica de base de datos"""
        return self.get('base_datos', {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Configuración específica de interfaz"""
        return self.get('interfaz', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Configuración específica de logging"""
        return self.get('logging', {})
    
    def get_alerts_config(self) -> Dict[str, Any]:
        """Configuración específica de alertas"""
        return self.get('alertas', {})
    
    def get_reports_config(self) -> Dict[str, Any]:
        """Configuración específica de reportes"""
        return self.get('reportes', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Configuración específica de seguridad"""
        return self.get('seguridad', {})
    
    def get_system_info(self) -> Dict[str, str]:
        """Información del sistema"""
        return {
            'nombre': self.get('sistema.nombre', 'DelegInsumos'),
            'version': self.get('sistema.version', '1.0.0'),
            'descripcion': self.get('sistema.descripcion', 'Sistema de Gestión de Insumos'),
            'autor': self.get('sistema.autor', 'KiloCode System')
        }
    
    def ensure_directories(self) -> None:
        """Crea los directorios necesarios según la configuración"""
        directories = [
            os.path.dirname(self.get('base_datos.archivo', './data/')),
            self.get('reportes.directorio', './reportes/'),
            os.path.dirname(self.get('logging.archivo', './logs/')),
            './backups/daily/',
            './backups/weekly/',
            './backups/manual/',
            './backups/updates/'
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def reload_config(self) -> bool:
        """
        Recarga la configuración desde el archivo.
        Útil para cambios en tiempo de ejecución.
        
        Returns:
            True si se recargó exitosamente, False en caso de error
        """
        try:
            self._load_config()
            self.ensure_directories()
            return True
        except Exception as e:
            print(f"[ERROR] Error recargando configuracion: {e}")
            return False

# Instancia global del gestor de configuración
config = ConfigManager()

# Función de conveniencia para acceso directo
def get_config(key_path: str, default: Any = None) -> Any:
    """Función de acceso directo a la configuración"""
    return config.get(key_path, default)

# Inicializar directorios necesarios
config.ensure_directories()