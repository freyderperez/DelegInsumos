"""
DelegInsumos - Servicio de Backup Automático
Sistema de respaldo y recuperación automática de la base de datos
"""

import os
import shutil
import sqlite3
import gzip
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from threading import Timer, Lock
import json

from config.config_manager import config
from database.connection import db_connection
from utils.logger import LoggerMixin, log_operation
from utils.helpers import create_backup_filename, get_file_size_mb, copy_file_safe
from utils import safe_filename
from exceptions.custom_exceptions import (
    service_exception_handler,
    BackupException,
    FileOperationException
)


class BackupService(LoggerMixin):
    """
    Servicio de backup automático y manual con versionado y compresión
    """
    
    def __init__(self):
        super().__init__()
        self.backup_config = config.get_database_config()
        self.db_path = self.backup_config.get('archivo', './data/deleginsumos.db')
        
        # Directorios de backup
        self.backup_root = Path('./backups/')
        self.daily_dir = self.backup_root / 'daily'
        self.weekly_dir = self.backup_root / 'weekly'
        self.manual_dir = self.backup_root / 'manual'
        self.updates_dir = self.backup_root / 'updates'
        
        # Crear directorios
        for directory in [self.daily_dir, self.weekly_dir, self.manual_dir, self.updates_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Control de backups automáticos
        self.auto_backup_enabled = self.backup_config.get('backup_automatico', True)
        self.backup_interval_hours = self.backup_config.get('backup_intervalo_horas', 24)
        self.backup_timer: Optional[Timer] = None
        self.backup_lock = Lock()
        
        # Estado del último backup
        self.last_backup_info = self._load_backup_state()
        
        self.logger.info("BackupService inicializado")
        
        # Iniciar backup automático si está habilitado
        if self.auto_backup_enabled:
            self._schedule_next_backup()
    
    def _load_backup_state(self) -> Dict[str, Any]:
        """Carga el estado del último backup desde archivo"""
        state_file = self.backup_root / 'backup_state.json'
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error cargando estado de backup: {e}")
        
        return {
            'last_backup': None,
            'last_success': None,
            'backup_count': 0,
            'total_size_mb': 0
        }
    
    def _save_backup_state(self) -> None:
        """Guarda el estado del backup actual"""
        state_file = self.backup_root / 'backup_state.json'
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_backup_info, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Error guardando estado de backup: {e}")
    
    @service_exception_handler("BackupService")
    def crear_backup_manual(self, descripcion: str = "") -> Dict[str, Any]:
        """
        Crea un backup manual de la base de datos.
        
        Args:
            descripcion: Descripción opcional del backup
            
        Returns:
            Diccionario con información del backup creado
        """
        self.logger.info(f"Creando backup manual: {descripcion}")
        
        with self.backup_lock:
            try:
                # Generar nombre de archivo
                base_name = "manual_backup"
                if descripcion:
                    base_name += f"_{safe_filename(descripcion)}"
                
                backup_filename = create_backup_filename(base_name, "db")
                backup_path = self.manual_dir / backup_filename
                
                # Verificar que la base de datos existe
                if not Path(self.db_path).exists():
                    raise BackupException("manual", f"Base de datos no encontrada: {self.db_path}")
                
                # Crear backup usando SQLite backup API (más seguro)
                success = self._create_sqlite_backup(self.db_path, str(backup_path))
                
                if not success:
                    raise BackupException("manual", "Error en la creación del backup SQLite")
                
                # Comprimir backup
                compressed_path = self._compress_backup(backup_path)
                if compressed_path:
                    backup_path.unlink()  # Eliminar versión sin comprimir
                    backup_path = compressed_path
                
                # Validar backup
                validation_result = self._validate_backup(backup_path)
                if not validation_result['valid']:
                    backup_path.unlink()  # Limpiar backup inválido
                    raise BackupException("manual", f"Backup inválido: {validation_result['error']}")
                
                # Actualizar estado
                backup_info = {
                    'type': 'manual',
                    'filename': backup_path.name,
                    'filepath': str(backup_path),
                    'size_mb': get_file_size_mb(str(backup_path)),
                    'created_at': datetime.now().isoformat(),
                    'description': descripcion,
                    'compressed': str(backup_path).endswith('.gz'),
                    'validation': validation_result
                }
                
                self._update_backup_state(backup_info)
                
                log_operation("BACKUP_MANUAL_CREADO", 
                             f"Archivo: {backup_filename}, Tamaño: {backup_info['size_mb']:.2f} MB")
                self.logger.info(f"Backup manual creado exitosamente: {backup_path}")
                
                return {
                    'success': True,
                    'backup_info': backup_info,
                    'message': f'Backup manual creado: {backup_filename}'
                }
                
            except Exception as e:
                self.logger.error(f"Error creando backup manual: {e}")
                raise BackupException("manual", str(e))
    
    @service_exception_handler("BackupService")
    def crear_backup_automatico(self) -> Dict[str, Any]:
        """
        Crea un backup automático programado.
        
        Returns:
            Diccionario con información del backup creado
        """
        self.logger.info("Ejecutando backup automático programado")
        
        with self.backup_lock:
            try:
                # Determinar si es backup diario o semanal
                now = datetime.now()
                is_weekly = now.weekday() == 6  # Domingo
                
                backup_dir = self.weekly_dir if is_weekly else self.daily_dir
                backup_type = "weekly" if is_weekly else "daily"
                
                # Generar nombre
                backup_filename = create_backup_filename(f"auto_{backup_type}", "db")
                backup_path = backup_dir / backup_filename
                
                # Crear backup
                success = self._create_sqlite_backup(self.db_path, str(backup_path))
                
                if not success:
                    raise BackupException("automatico", "Error en backup automático SQLite")
                
                # Comprimir
                compressed_path = self._compress_backup(backup_path)
                if compressed_path:
                    backup_path.unlink()
                    backup_path = compressed_path
                
                # Validar
                validation_result = self._validate_backup(backup_path)
                if not validation_result['valid']:
                    backup_path.unlink()
                    raise BackupException("automatico", f"Backup automático inválido: {validation_result['error']}")
                
                # Limpiar backups antiguos
                self._cleanup_old_backups(backup_dir, backup_type)
                
                # Actualizar estado
                backup_info = {
                    'type': 'automatico',
                    'subtype': backup_type,
                    'filename': backup_path.name,
                    'filepath': str(backup_path),
                    'size_mb': get_file_size_mb(str(backup_path)),
                    'created_at': datetime.now().isoformat(),
                    'compressed': True,
                    'validation': validation_result
                }
                
                self._update_backup_state(backup_info)
                
                # Programar próximo backup
                self._schedule_next_backup()
                
                log_operation("BACKUP_AUTOMATICO_CREADO", 
                             f"Tipo: {backup_type}, Archivo: {backup_filename}")
                self.logger.info(f"Backup automático {backup_type} creado: {backup_path}")
                
                return {
                    'success': True,
                    'backup_info': backup_info,
                    'message': f'Backup automático {backup_type} creado exitosamente'
                }
                
            except Exception as e:
                self.logger.error(f"Error en backup automático: {e}")
                
                # Reintent ar en 1 hora
                self._schedule_backup_retry()
                
                raise BackupException("automatico", str(e))
    
    def _create_sqlite_backup(self, source_db: str, target_path: str) -> bool:
        """
        Crea backup usando SQLite backup API para máxima integridad.
        
        Args:
            source_db: Ruta de la base de datos fuente
            target_path: Ruta del backup destino
            
        Returns:
            True si el backup fue exitoso
        """
        try:
            # Conexión a base fuente
            source_conn = sqlite3.connect(source_db)
            
            # Conexión a backup destino
            target_conn = sqlite3.connect(target_path)
            
            # Realizar backup usando SQLite API
            source_conn.backup(target_conn)
            
            # Cerrar conexiones
            source_conn.close()
            target_conn.close()
            
            self.logger.debug(f"Backup SQLite creado: {source_db} → {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error en backup SQLite: {e}")
            return False
    
    def _compress_backup(self, backup_path: Path) -> Optional[Path]:
        """
        Comprime un archivo de backup usando gzip.
        
        Args:
            backup_path: Ruta del archivo a comprimir
            
        Returns:
            Ruta del archivo comprimido o None si hubo error
        """
        try:
            compressed_path = backup_path.with_suffix(backup_path.suffix + '.gz')
            
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            self.logger.debug(f"Backup comprimido: {backup_path} → {compressed_path}")
            return compressed_path
            
        except Exception as e:
            self.logger.warning(f"Error comprimiendo backup: {e}")
            return None
    
    def _validate_backup(self, backup_path: Path) -> Dict[str, Any]:
        """
        Valida la integridad de un archivo de backup.
        
        Args:
            backup_path: Ruta del archivo de backup
            
        Returns:
            Diccionario con resultado de validación
        """
        try:
            # Si está comprimido, descomprimir temporalmente para validar
            temp_file = None
            validate_path = backup_path
            
            if str(backup_path).endswith('.gz'):
                temp_file = backup_path.with_suffix('')
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                validate_path = temp_file
            
            # Validar estructura SQLite
            conn = sqlite3.connect(str(validate_path))
            cursor = conn.cursor()
            
            # Verificar integridad
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            # Verificar que las tablas principales existan
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('insumos', 'empleados', 'entregas')
            """)
            tables = cursor.fetchall()
            
            conn.close()
            
            # Limpiar archivo temporal
            if temp_file and temp_file.exists():
                temp_file.unlink()
            
            # Evaluar resultados
            is_valid = (integrity_result == "ok" and len(tables) >= 3)
            
            return {
                'valid': is_valid,
                'integrity_check': integrity_result,
                'tables_found': len(tables),
                'size_mb': get_file_size_mb(str(backup_path)),
                'validation_time': datetime.now().isoformat(),
                'error': None if is_valid else f"Integridad: {integrity_result}, Tablas: {len(tables)}"
            }
            
        except Exception as e:
            # Limpiar archivo temporal en caso de error
            if 'temp_file' in locals() and temp_file and temp_file.exists():
                temp_file.unlink()
            
            self.logger.error(f"Error validando backup {backup_path}: {e}")
            return {
                'valid': False,
                'error': str(e),
                'validation_time': datetime.now().isoformat()
            }
    
    def _cleanup_old_backups(self, backup_dir: Path, backup_type: str) -> int:
        """
        Limpia backups antiguos según configuración.
        
        Args:
            backup_dir: Directorio de backups
            backup_type: Tipo de backup (daily/weekly)
            
        Returns:
            Número de archivos eliminados
        """
        try:
            if backup_type == "daily":
                max_backups = self.backup_config.get('max_backups_diarios', 7)
            else:
                max_backups = self.backup_config.get('max_backups_semanales', 4)
            
            # Obtener lista de backups ordenada por fecha
            backup_files = []
            for file_path in backup_dir.glob('*.db*'):
                if file_path.is_file():
                    backup_files.append((file_path, file_path.stat().st_mtime))
            
            # Ordenar por fecha de modificación (más reciente primero)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Eliminar los más antiguos si exceden el límite
            deleted_count = 0
            for i, (file_path, _) in enumerate(backup_files):
                if i >= max_backups:
                    file_path.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Backup antiguo eliminado: {file_path.name}")
            
            if deleted_count > 0:
                self.logger.info(f"Limpieza {backup_type}: {deleted_count} backups antiguos eliminados")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error limpiando backups {backup_type}: {e}")
            return 0
    
    def _update_backup_state(self, backup_info: Dict[str, Any]) -> None:
        """Actualiza el estado interno del servicio de backup"""
        self.last_backup_info.update({
            'last_backup': backup_info['created_at'],
            'last_success': backup_info['created_at'],
            'last_backup_info': backup_info,
            'backup_count': self.last_backup_info.get('backup_count', 0) + 1,
            'total_size_mb': self.last_backup_info.get('total_size_mb', 0) + backup_info['size_mb']
        })
        
        self._save_backup_state()
    
    def _schedule_next_backup(self) -> None:
        """Programa el próximo backup automático"""
        if not self.auto_backup_enabled:
            return
        
        try:
            # Cancelar timer anterior si existe
            if self.backup_timer:
                self.backup_timer.cancel()
            
            # Programar próximo backup
            interval_seconds = self.backup_interval_hours * 3600
            
            self.backup_timer = Timer(interval_seconds, self._execute_auto_backup)
            self.backup_timer.daemon = True
            self.backup_timer.start()
            
            next_backup = datetime.now() + timedelta(seconds=interval_seconds)
            self.logger.info(f"Próximo backup automático programado para: {next_backup.strftime('%d/%m/%Y %H:%M')}")
            
        except Exception as e:
            self.logger.error(f"Error programando backup automático: {e}")
    
    def _schedule_backup_retry(self, retry_minutes: int = 60) -> None:
        """Programa un reintento de backup automático"""
        try:
            self.backup_timer = Timer(retry_minutes * 60, self._execute_auto_backup)
            self.backup_timer.daemon = True
            self.backup_timer.start()
            
            retry_time = datetime.now() + timedelta(minutes=retry_minutes)
            self.logger.info(f"Reintento de backup programado para: {retry_time.strftime('%d/%m/%Y %H:%M')}")
            
        except Exception as e:
            self.logger.error(f"Error programando reintento de backup: {e}")
    
    def _execute_auto_backup(self) -> None:
        """Ejecuta backup automático en hilo separado"""
        try:
            self.crear_backup_automatico()
        except Exception as e:
            self.logger.error(f"Error en backup automático: {e}")
            # Programar reintento
            self._schedule_backup_retry()
    
    @service_exception_handler("BackupService")
    def restaurar_backup(self, backup_filename: str) -> Dict[str, Any]:
        """
        Restaura la base de datos desde un backup.
        
        Args:
            backup_filename: Nombre del archivo de backup
            
        Returns:
            Diccionario con resultado de la restauración
        """
        self.logger.warning(f"Iniciando restauración desde backup: {backup_filename}")
        
        try:
            # Buscar archivo en todos los directorios de backup
            backup_path = None
            for backup_dir in [self.manual_dir, self.daily_dir, self.weekly_dir, self.updates_dir]:
                potential_path = backup_dir / backup_filename
                if potential_path.exists():
                    backup_path = potential_path
                    break
            
            if not backup_path:
                raise BackupException("restauracion", f"Backup no encontrado: {backup_filename}")
            
            # Crear backup de la base actual antes de restaurar
            pre_restore_backup = self.crear_backup_manual("pre_restauracion")
            
            # Validar backup a restaurar
            validation = self._validate_backup(backup_path)
            if not validation['valid']:
                raise BackupException("restauracion", f"Backup inválido: {validation['error']}")
            
            # Cerrar conexiones activas
            db_connection.close_all_connections()
            
            # Crear archivo temporal para restauración
            temp_path = Path(self.db_path).with_suffix('.temp')
            
            # Descomprimir si es necesario
            if str(backup_path).endswith('.gz'):
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                copy_file_safe(str(backup_path), str(temp_path))
            
            # Hacer backup de la base actual
            current_backup = Path(self.db_path).with_suffix('.backup')
            if Path(self.db_path).exists():
                copy_file_safe(self.db_path, str(current_backup))
            
            # Reemplazar base de datos actual
            if Path(self.db_path).exists():
                Path(self.db_path).unlink()
            
            temp_path.rename(self.db_path)
            
            # Validar restauración
            restored_validation = self._validate_backup(Path(self.db_path))
            if not restored_validation['valid']:
                # Rollback: restaurar backup anterior
                if current_backup.exists():
                    Path(self.db_path).unlink()
                    current_backup.rename(self.db_path)
                
                raise BackupException("restauracion", "La base restaurada es inválida. Operación revertida.")
            
            # Limpiar archivos temporales
            if current_backup.exists():
                current_backup.unlink()
            
            log_operation("BACKUP_RESTAURADO", 
                         f"Archivo: {backup_filename}, Validación: OK")
            self.logger.warning(f"Base de datos restaurada exitosamente desde: {backup_filename}")
            
            return {
                'success': True,
                'backup_filename': backup_filename,
                'backup_size_mb': validation['size_mb'],
                'pre_restore_backup': pre_restore_backup['backup_info']['filename'],
                'validation': restored_validation,
                'message': f'Base de datos restaurada exitosamente desde {backup_filename}'
            }
            
        except Exception as e:
            self.logger.error(f"Error restaurando backup {backup_filename}: {e}")
            raise BackupException("restauracion", str(e))
    
    @service_exception_handler("BackupService")
    def listar_backups(self) -> Dict[str, Any]:
        """
        Lista todos los backups disponibles organizados por tipo.
        
        Returns:
            Diccionario con backups organizados
        """
        try:
            backups = {
                'manual': [],
                'daily': [],
                'weekly': [],
                'updates': []
            }
            
            # Escanear cada directorio
            dirs_map = {
                'manual': self.manual_dir,
                'daily': self.daily_dir,
                'weekly': self.weekly_dir,
                'updates': self.updates_dir
            }
            
            for backup_type, backup_dir in dirs_map.items():
                if backup_dir.exists():
                    for file_path in backup_dir.glob('*.db*'):
                        if file_path.is_file():
                            stat = file_path.stat()
                            
                            backup_info = {
                                'filename': file_path.name,
                                'filepath': str(file_path),
                                'size_mb': round(stat.st_size / (1024*1024), 2),
                                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'compressed': file_path.suffix == '.gz',
                                'type': backup_type
                            }
                            
                            backups[backup_type].append(backup_info)
            
            # Ordenar cada lista por fecha (más reciente primero)
            for backup_type in backups:
                backups[backup_type].sort(key=lambda x: x['created_at'], reverse=True)
            
            # Calcular totales
            total_backups = sum(len(backup_list) for backup_list in backups.values())
            total_size = sum(
                backup['size_mb'] 
                for backup_list in backups.values() 
                for backup in backup_list
            )
            
            return {
                'backups': backups,
                'summary': {
                    'total_backups': total_backups,
                    'total_size_mb': round(total_size, 2),
                    'by_type': {k: len(v) for k, v in backups.items()},
                    'last_state': self.last_backup_info
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error listando backups: {e}")
            return {
                'backups': {'manual': [], 'daily': [], 'weekly': [], 'updates': []},
                'summary': {'total_backups': 0, 'error': str(e)}
            }
    
    @service_exception_handler("BackupService")
    def obtener_estado_backup(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del sistema de backup.
        
        Returns:
            Diccionario con estado completo del sistema de backup
        """
        estado = {
            'backup_automatico_activo': self.auto_backup_enabled,
            'intervalo_horas': self.backup_interval_hours,
            'ultimo_backup': self.last_backup_info,
            'proximo_backup_programado': None,
            'directorios': {
                'daily': str(self.daily_dir),
                'weekly': str(self.weekly_dir), 
                'manual': str(self.manual_dir),
                'updates': str(self.updates_dir)
            },
            'configuracion': self.backup_config
        }
        
        # Calcular próximo backup si hay timer activo
        if self.backup_timer and self.backup_timer.is_alive():
            # Estimar tiempo restante (aproximado)
            next_backup = datetime.now() + timedelta(hours=self.backup_interval_hours)
            estado['proximo_backup_programado'] = next_backup.isoformat()
        
        return estado
    
    def activar_backup_automatico(self) -> Dict[str, Any]:
        """
        Activa el sistema de backup automático.
        
        Returns:
            Resultado de la activación
        """
        if self.auto_backup_enabled:
            return {
                'success': True,
                'message': 'El backup automático ya estaba activo'
            }
        
        self.auto_backup_enabled = True
        self._schedule_next_backup()
        
        log_operation("BACKUP_AUTOMATICO_ACTIVADO", "Sistema de backup automático activado")
        
        return {
            'success': True,
            'message': 'Sistema de backup automático activado',
            'next_backup': (datetime.now() + timedelta(hours=self.backup_interval_hours)).isoformat()
        }
    
    def desactivar_backup_automatico(self) -> Dict[str, Any]:
        """
        Desactiva el sistema de backup automático.
        
        Returns:
            Resultado de la desactivación
        """
        self.auto_backup_enabled = False
        
        if self.backup_timer:
            self.backup_timer.cancel()
            self.backup_timer = None
        
        log_operation("BACKUP_AUTOMATICO_DESACTIVADO", "Sistema de backup automático desactivado")
        
        return {
            'success': True,
            'message': 'Sistema de backup automático desactivado'
        }


# Instancia global del servicio de backup
backup_service = BackupService()

# Funciones de conveniencia para uso directo
def crear_backup_manual(descripcion: str = "") -> Dict[str, Any]:
    """Función de conveniencia para crear backup manual"""
    return backup_service.crear_backup_manual(descripcion)

def listar_backups() -> Dict[str, Any]:
    """Función de conveniencia para listar backups"""
    return backup_service.listar_backups()

def restaurar_backup(backup_filename: str) -> Dict[str, Any]:
    """Función de conveniencia para restaurar backup"""
    return backup_service.restaurar_backup(backup_filename)

def obtener_estado_backup() -> Dict[str, Any]:
    """Función de conveniencia para obtener estado del backup"""
    return backup_service.obtener_estado_backup()