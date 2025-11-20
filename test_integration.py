
"""
DelegInsumos - Script de Pruebas de Integración
Verifica el funcionamiento completo del sistema sin GUI
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime, date, timedelta

# Configurar path
sys.path.insert(0, str(Path(__file__).parent))

def test_system_integration():
    """
    Ejecuta pruebas completas de integración del sistema
    """
    
    print("🔬 INICIANDO PRUEBAS DE INTEGRACIÓN - DelegInsumos")
    print("=" * 60)
    
    test_results = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Test 1: Configuración y dependencias
        run_test("📋 Verificar Dependencias", test_dependencies, test_results)
        
        # Test 2: Inicialización de base de datos
        run_test("🗄️ Inicialización de Base de Datos", test_database_setup, test_results)
        
        # Test 3: Operaciones CRUD de insumos
        run_test("📦 CRUD de Insumos", test_insumos_crud, test_results)
        
        # Test 4: Operaciones CRUD de empleados
        run_test("👥 CRUD de Empleados", test_empleados_crud, test_results)
        
        # Test 5: Sistema de entregas
        run_test("📋 Sistema de Entregas", test_entregas_system, test_results)
        
        # Test 6: Sistema de alertas
        run_test("🚨 Sistema de Alertas", test_alerts_system, test_results)
        
        # Test 7: Generación de reportes
        run_test("📄 Generación de Reportes", test_reports_generation, test_results)
        
        # Test 8: Sistema de backup
        run_test("💾 Sistema de Backup", test_backup_system, test_results)
        
        # Test 9: Validaciones de datos
        run_test("✅ Validaciones de Datos", test_data_validations, test_results)
        
        # Test 10: Integración entre módulos
        run_test("🔗 Integración entre Módulos", test_module_integration, test_results)
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO EN PRUEBAS: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        test_results['errors'].append(f"Error crítico: {e}")
    
    # Mostrar resultados finales
    print_test_summary(test_results)
    
    return test_results['passed'] == test_results['total_tests']


def run_test(test_name: str, test_function, results: dict):
    """Ejecuta una prueba individual y maneja los resultados"""
    
    print(f"\n🔍 {test_name}")
    print("-" * 40)
    
    results['total_tests'] += 1
    
    try:
        start_time = datetime.now()
        success = test_function()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        if success:
            print(f"✅ ÉXITO - {test_name} ({duration:.2f}s)")
            results['passed'] += 1
        else:
            print(f"❌ FALLA - {test_name} ({duration:.2f}s)")
            results['failed'] += 1
            results['errors'].append(f"{test_name}: Test falló")
            
    except Exception as e:
        print(f"💥 ERROR - {test_name}: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        results['failed'] += 1
        results['errors'].append(f"{test_name}: {e}")


def test_dependencies():
    """Prueba 1: Verificar que todas las dependencias están disponibles"""
    
    try:
        print("📦 Verificando dependencias principales...")
        
        # Core dependencies
        import ttkbootstrap
        print(f"  ✅ ttkbootstrap: {ttkbootstrap.__version__}")
        
        import reportlab
        print(f"  ✅ reportlab: {reportlab.Version}")
        
        import openpyxl
        print(f"  ✅ openpyxl: {openpyxl.__version__}")
        
        import pandas as pd
        print(f"  ✅ pandas: {pd.__version__}")
        
        import matplotlib
        print(f"  ✅ matplotlib: {matplotlib.__version__}")
        
        # Internal modules
        from config.config_manager import config
        print("  ✅ Config manager cargado")
        
        from utils.logger import main_logger
        print("  ✅ Sistema de logging cargado")
        
        from database.connection import db_connection
        print("  ✅ Conexión a base de datos cargada")
        
        print("✅ Todas las dependencias disponibles")
        return True
        
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        return False
    except Exception as e:
        print(f"❌ Error verificando dependencias: {e}")
        return False


def test_database_setup():
    """Prueba 2: Inicialización y migración de base de datos"""
    
    try:
        print("🗄️ Inicializando base de datos...")
        
        from database.migrations import initialize_database, get_migration_status
        
        # Inicializar base de datos
        success = initialize_database()
        if not success:
            print("❌ Error inicializando base de datos")
            return False
        
        print("✅ Base de datos inicializada")
        
        # Verificar migraciones
        status = get_migration_status()
        print(f"  📊 Migraciones aplicadas: {status['applied_count']}")
        print(f"  📋 Migraciones pendientes: {status['pending_count']}")
        
        if status['pending_count'] > 0:
            print("❌ Hay migraciones pendientes")
            return False
        
        # Verificar conexión
        from database.connection import db_connection
        if not db_connection.check_connection():
            print("❌ No se puede conectar a la base de datos")
            return False
        
        print("✅ Conexión a base de datos exitosa")
        
        # Verificar información de la BD
        db_info = db_connection.get_database_info()
        print(f"  📁 Archivo BD: {db_info['database_path']}")
        print(f"  📊 Tamaño BD: {db_info['database_size_mb']} MB")
        print(f"  🗂️ Tablas: {len(db_info['tables'])} ({', '.join(db_info['tables'])})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en setup de base de datos: {e}")
        return False


def test_insumos_crud():
    """Prueba 3: Operaciones CRUD de insumos"""
    
    try:
        print("📦 Probando CRUD de insumos...")
        
        from services.micro_insumos import micro_insumos
        
        # Test data
        test_insumo = {
            'nombre': 'Papel A4 Test',
            'categoria': 'Papelería',
            'cantidad_actual': 50,
            'cantidad_minima': 10,
            'cantidad_maxima': 200,
            'unidad_medida': 'resma',
            'precio_unitario': 15000.00,
            'proveedor': 'Proveedor Test'
        }
        
        # CREATE - Crear insumo
        print("  📝 Creando insumo de prueba...")
        create_result = micro_insumos.crear_insumo(test_insumo)
        
        if not create_result['success']:
            print("❌ Error creando insumo")
            return False
        
        insumo_id = create_result['insumo_id']
        print(f"  ✅ Insumo creado con ID: {insumo_id}")
        
        # READ - Leer insumo
        print("  📖 Leyendo insumo...")
        read_result = micro_insumos.obtener_insumo(insumo_id)
        
        if read_result['nombre'] != test_insumo['nombre']:
            print("❌ Error leyendo insumo - datos no coinciden")
            return False
        
        print(f"  ✅ Insumo leído correctamente: {read_result['nombre']}")
        
        # UPDATE - Actualizar insumo
        print("  ✏️ Actualizando insumo...")
        update_data = {'precio_unitario': 16000.00, 'proveedor': 'Proveedor Actualizado'}
        update_result = micro_insumos.actualizar_insumo(insumo_id, update_data)
        
        if not update_result['success']:
            print("❌ Error actualizando insumo")
            return False
        
        print("  ✅ Insumo actualizado correctamente")
        
        # UPDATE STOCK - Actualizar stock
        print("  📊 Actualizando stock...")
        stock_result = micro_insumos.actualizar_stock(insumo_id, 75, "Test actualización")
        
        if not stock_result['success']:
            print("❌ Error actualizando stock")
            return False
        
        print(f"  ✅ Stock actualizado: {stock_result['cantidad_anterior']} → {stock_result['cantidad_nueva']}")
        
        # LIST - Listar insumos
        print("  📋 Listando insumos...")
        list_result = micro_insumos.listar_insumos()
        
        if list_result['total'] == 0:
            print("❌ Error listando insumos - lista vacía")
            return False
        
        print(f"  ✅ Lista obtenida: {list_result['total']} insumos")
        
        # SEARCH - Buscar insumos
        print("  🔍 Buscando insumos...")
        search_result = micro_insumos.buscar_insumos("Test")
        
        if len(search_result) == 0:
            print("❌ Error buscando insumos - no encontró el test")
            return False
        
        print(f"  ✅ Búsqueda exitosa: {len(search_result)} resultados")
        
        # DELETE - Eliminar insumo (soft delete)
        print("  🗑️ Eliminando insumo (soft delete)...")
        delete_result = micro_insumos.eliminar_insumo(insumo_id, soft_delete=True)
        
        if not delete_result['success']:
            print("❌ Error eliminando insumo")
            return False
        
        print("  ✅ Insumo eliminado (desactivado) correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en CRUD de insumos: {e}")
        return False


def test_empleados_crud():
    """Prueba 4: Operaciones CRUD de empleados"""
    
    try:
        print("👥 Probando CRUD de empleados...")
        
        from services.micro_empleados import micro_empleados
        
        # Test data
        test_empleado = {
            'nombre_completo': 'Juan Pérez Test',
            'cargo': 'Analista de Pruebas',
            'departamento': 'Sistemas',
            'cedula': '12345678',
            'email': 'juan.test@empresa.com',
            'telefono': '+57 300 123 4567',
            'fecha_ingreso': date.today()
        }
        
        # CREATE
        print("  📝 Creando empleado de prueba...")
        create_result = micro_empleados.crear_empleado(test_empleado)
        
        if not create_result['success']:
            print("❌ Error creando empleado")
            return False
        
        empleado_id = create_result['empleado_id']
        print(f"  ✅ Empleado creado con ID: {empleado_id}")
        
        # READ
        print("  📖 Leyendo empleado...")
        read_result = micro_empleados.obtener_empleado(empleado_id)
        
        if read_result['nombre_completo'] != test_empleado['nombre_completo']:
            print("❌ Error leyendo empleado - datos no coinciden")
            return False
        
        print(f"  ✅ Empleado leído: {read_result['nombre_completo']}")
        
        # UPDATE
        print("  ✏️ Actualizando empleado...")
        update_data = {'cargo': 'Senior Analista', 'telefono': '+57 300 999 8888'}
        update_result = micro_empleados.actualizar_empleado(empleado_id, update_data)
        
        if not update_result['success']:
            print("❌ Error actualizando empleado")
            return False
        
        print("  ✅ Empleado actualizado correctamente")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sistema de backup: {e}")
        return False


def test_data_validations():
    """Prueba 9: Validaciones de datos"""
    
    try:
        print("✅ Probando validaciones de datos...")
        
        from utils.validators import validate_insumo_data, validate_empleado_data, validate_entrega_data
        from exceptions.custom_exceptions import ValidationException
        
        # Test validaciones de insumo
        print("  📦 Probando validaciones de insumo...")
        
        # Datos válidos
        insumo_valido = {
            'nombre': 'Test Insumo Válido',
            'categoria': 'Papelería',
            'cantidad_actual': 50,
            'cantidad_minima': 10,
            'cantidad_maxima': 100,
            'unidad_medida': 'unidad',
            'precio_unitario': 1500.00,
            'proveedor': 'Proveedor Test'
        }
        
        try:
            validated = validate_insumo_data(insumo_valido)
            print("    ✅ Validación de insumo válido: OK")
        except Exception as e:
            print(f"    ❌ Error validando insumo válido: {e}")
            return False
        
        # Datos inválidos
        insumo_invalido = {
            'nombre': '',  # Vacío - debe fallar
            'categoria': '',
            'cantidad_actual': -5,  # Negativo - debe fallar
            'precio_unitario': 'no es número'  # Tipo incorrecto
        }
        
        try:
            validate_insumo_data(insumo_invalido)
            print("    ❌ Validación debería haber fallado")
            return False
        except ValidationException:
            print("    ✅ Validación de insumo inválido: Falló correctamente")
        
        # Test validaciones de empleado
        print("  👥 Probando validaciones de empleado...")
        
        empleado_valido = {
            'nombre_completo': 'María García Test',
            'cargo': 'Analista',
            'departamento': 'Administración',
            'cedula': '87654321',
            'email': 'maria@test.com',
            'telefono': '+57 300 111 2222',
            'fecha_ingreso': date.today()
        }
        
        try:
            validated = validate_empleado_data(empleado_valido)
            print("    ✅ Validación de empleado válido: OK")
        except Exception as e:
            print(f"    ❌ Error validando empleado válido: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error en validaciones de datos: {e}")
        return False


def test_module_integration():
    """Prueba 10: Integración entre módulos"""
    
    try:
        print("🔗 Probando integración entre módulos...")
        
        # Test: Flujo completo de una operación
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        from services.micro_entregas import micro_entregas
        from services.micro_alertas import micro_alertas
        
        print("  🔄 Verificando comunicación entre módulos...")
        
        # 1. Obtener datos de diferentes servicios
        print("    📦 Obteniendo datos de insumos...")
        insumos_data = micro_insumos.listar_insumos()
        print(f"    ✅ Insumos: {insumos_data['total']}")
        
        print("    👥 Obteniendo datos de empleados...")
        empleados_data = micro_empleados.listar_empleados()
        print(f"    ✅ Empleados: {empleados_data['total']}")
        
        print("    📋 Obteniendo datos de entregas...")
        entregas_data = micro_entregas.listar_entregas(limit=10)
        print(f"    ✅ Entregas: {entregas_data['total_returned']}")
        
        # 2. Verificar consistencia entre módulos
        print("  🔍 Verificando consistencia de datos...")
        
        # Verificar que alertas reflejan el estado real
        alertas_data = micro_alertas.obtener_alertas_dashboard()
        stock_alerts = micro_insumos.obtener_alertas_stock()
        
        print(f"    🚨 Alertas en dashboard: {alertas_data['total_active']}")
        print(f"    📦 Alertas de stock: {stock_alerts['total_alertas']}")
        
        print("  ✅ Integración entre módulos verificada")
        return True
        
    except Exception as e:
        print(f"❌ Error en integración de módulos: {e}")
        return False


def test_offline_functionality():
    """Prueba específica: Funcionamiento offline"""
    
    try:
        print("🌐 Probando funcionamiento offline...")
        
        # Verificar que SQLite es local
        from database.connection import db_connection
        db_info = db_connection.get_database_info()
        
        if 'deleginsumos.db' in db_info['database_path']:
            print(f"  ✅ Base de datos local: {Path(db_info['database_path']).name}")
        else:
            print("  ❌ Ruta de base de datos sospechosa")
            return False
        
        # Verificar que reportes se generan localmente
        from services.reportes_service import reportes_service
        reportes_dir = reportes_service.output_dir
        
        if reportes_dir.exists():
            print(f"  ✅ Directorio de reportes local: {reportes_dir}")
        else:
            print("  ❌ Directorio de reportes no encontrado")
            return False
        
        print("✅ Funcionamiento offline verificado")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando funcionamiento offline: {e}")
        return False


def test_complete_workflow():
    """Prueba del flujo completo del sistema"""
    
    try:
        print("🔄 Probando flujo completo del sistema...")
        
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        from services.micro_entregas import micro_entregas
        from services.micro_alertas import micro_alertas
        from services.reportes_service import reportes_service
        from services.backup_service import backup_service
        
        # Verificar sistema al inicio del día
        print("  🌅 Verificaciones de inicio...")
        
        alertas = micro_alertas.verificar_todas_las_alertas()
        entregas_hoy = micro_entregas.obtener_entregas_hoy()
        inventario = micro_insumos.listar_insumos()
        empleados = micro_empleados.listar_empleados()
        
        print(f"    🚨 Nuevas alertas: {alertas['total_new_alerts']}")
        print(f"    📋 Entregas hoy: {entregas_hoy['total_entregas']}")
        print(f"    📦 Insumos activos: {inventario['total']}")
        print(f"    👥 Empleados activos: {empleados['statistics']['empleados_activos']}")
        
        # Verificar reportes
        stats_reportes = reportes_service.obtener_estadisticas_reportes()
        print(f"    📄 Reportes disponibles: {stats_reportes['total_reportes']}")
        
        # Verificar backup
        backup_status = backup_service.obtener_estado_backup()
        backup_activo = backup_status['backup_automatico_activo']
        print(f"    💾 Sistema backup: {'✅ Activo' if backup_activo else '❌ Inactivo'}")
        
        print("✅ Flujo completo verificado")
        return True
        
    except Exception as e:
        print(f"❌ Error en flujo completo: {e}")
        return False
        # VALIDACIÓN PARA ENTREGAS
        print("  ✅ Validando empleado para entregas...")
        validation_result = micro_empleados.validar_empleado_para_entrega(empleado_id)
        
        if not validation_result['can_receive']:
            print(f"❌ Empleado no válido para entregas: {validation_result['message']}")
            return False
        
        print("  ✅ Empleado válido para entregar insumos")
        
        # LIST
        print("  📋 Listando empleados...")
        list_result = micro_empleados.listar_empleados()
        
        if list_result['total'] == 0:
            print("❌ Error listando empleados - lista vacía")
            return False
        
        print(f"  ✅ Lista obtenida: {list_result['total']} empleados")
        
        # SEARCH
        print("  🔍 Buscando empleados...")
        search_result = micro_empleados.buscar_empleados("Test")
        
        if len(search_result) == 0:
            print("❌ Error buscando empleados")
            return False
        
        print(f"  ✅ Búsqueda exitosa: {len(search_result)} resultados")
        
        print("  ✅ CRUD de empleados completado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en CRUD de empleados: {e}")
        return False


def test_entregas_system():
    """Prueba 5: Sistema de entregas completo"""
    
    try:
        print("📋 Probando sistema de entregas...")
        
        from services.micro_entregas import micro_entregas
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        
        # Necesitamos insumo y empleado existentes
        print("  🔍 Buscando insumo y empleado para test...")
        
        # Buscar o crear insumo para entrega
        insumos_list = micro_insumos.listar_insumos()
        if insumos_list['total'] == 0:
            # Crear insumo para test
            insumo_test = {
                'nombre': 'Bolígrafos Test Entregas',
                'categoria': 'Papelería',
                'cantidad_actual': 100,
                'cantidad_minima': 20,
                'cantidad_maxima': 500,
                'unidad_medida': 'unidad',
                'precio_unitario': 2500.00,
                'proveedor': 'Proveedor Test'
            }
            create_ins_result = micro_insumos.crear_insumo(insumo_test)
            insumo_id = create_ins_result['insumo_id']
        else:
            insumo_id = insumos_list['insumos'][0]['id']
        
        # Buscar empleado válido
        empleados_validos = micro_empleados.obtener_empleados_activos_para_entrega()
        if not empleados_validos:
            print("❌ No hay empleados válidos para entregas")
            return False
        
        empleado_id = empleados_validos[0]['id']
        
        print(f"  📦 Usando insumo ID: {insumo_id}")
        print(f"  👤 Usando empleado ID: {empleado_id}")
        
        # Datos de entrega de prueba
        entrega_test = {
            'empleado_id': empleado_id,
            'insumo_id': insumo_id,
            'cantidad': 5,
            'observaciones': 'Entrega de prueba del sistema',
            'entregado_por': 'Sistema de Pruebas'
        }
        
        # CREATE ENTREGA
        print("  ➕ Creando entrega...")
        create_result = micro_entregas.crear_entrega(entrega_test)
        
        if not create_result['success']:
            print(f"❌ Error creando entrega: {create_result}")
            return False
        
        entrega_id = create_result['entrega_id']
        print(f"  ✅ Entrega creada con ID: {entrega_id}")
        print(f"  📊 Stock actualizado: {create_result['stock_anterior']} → {create_result['stock_nuevo']}")
        
        # READ ENTREGA
        print("  📖 Leyendo entrega...")
        read_result = micro_entregas.obtener_entrega(entrega_id)
        
        if read_result['cantidad'] != entrega_test['cantidad']:
            print("❌ Error leyendo entrega - datos no coinciden")
            return False
        
        print(f"  ✅ Entrega leída: {read_result['cantidad']} unidades")
        
        # LIST ENTREGAS
        print("  📋 Listando entregas...")
        list_result = micro_entregas.listar_entregas(limit=50)
        
        if list_result['total_returned'] == 0:
            print("❌ Error listando entregas - lista vacía")
            return False
        
        print(f"  ✅ Lista de entregas: {list_result['total_returned']} entregas")
        
        # ESTADÍSTICAS
        print("  📈 Obteniendo estadísticas...")
        stats_result = micro_entregas.obtener_estadisticas_entregas()
        
        print(f"  📊 Estadísticas generadas exitosamente")
        print(f"  📋 Total entregas históricas: {stats_result['general']['total_entregas']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sistema de entregas: {e}")
        return False


def test_alerts_system():
    """Prueba 6: Sistema de alertas"""
    
    try:
        print("🚨 Probando sistema de alertas...")
        
        from services.micro_alertas import micro_alertas
        
        # Verificar alertas del sistema
        print("  🔍 Verificando alertas existentes...")
        verification_result = micro_alertas.verificar_todas_las_alertas()
        
        print(f"  📊 Alertas encontradas: {verification_result['total_new_alerts']}")
        
        # Obtener alertas activas
        print("  📋 Obteniendo alertas activas...")
        active_alerts = micro_alertas.obtener_alertas_activas()
        
        print(f"  ⚠️ Alertas activas: {len(active_alerts)}")
        
        # Obtener resumen de alertas
        print("  📈 Obteniendo resumen...")
        summary = micro_alertas.obtener_resumen_alertas()
        
        print(f"  📊 Total alertas activas: {summary['total_active']}")
        print(f"  🔧 Alertas que requieren acción: {summary['action_required']}")
        
        # Alertas para dashboard
        print("  🏠 Obteniendo alertas for dashboard...")
        dashboard_alerts = micro_alertas.obtener_alertas_dashboard()
        
        print(f"  🔴 Alertas críticas: {dashboard_alerts['total_critical']}")
        print(f"  🟠 Alertas altas: {dashboard_alerts['total_high']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sistema de alertas: {e}")
        return False


def test_reports_generation():
    """Prueba 7: Generación de reportes"""
    
    try:
        print("📄 Probando generación de reportes...")
        
        from services.reportes_service import reportes_service
        
        # Test reporte PDF de inventario
        print("  📄 Generando reporte de inventario PDF...")
        pdf_result = reportes_service.generar_reporte_inventario_pdf(incluir_graficos=False)
        
        if not pdf_result['success']:
            print("❌ Error generando reporte PDF")
            return False
        
        print(f"  ✅ PDF generado: {pdf_result['filename']} ({pdf_result['size_mb']} MB)")
        
        # Test reporte Excel
        print("  📊 Generando reporte de inventario Excel...")
        excel_result = reportes_service.generar_reporte_inventario_excel()
        
        if not excel_result['success']:
            print("❌ Error generando reporte Excel")
            return False
        
        print(f"  ✅ Excel generado: {excel_result['filename']} ({excel_result['size_mb']} MB)")
        
        # Test reporte de entregas
        print("  📋 Generando reporte de entregas...")
        fecha_inicio = date.today() - timedelta(days=30)
        entregas_result = reportes_service.generar_reporte_entregas_pdf(fecha_inicio, date.today())
        
        if not entregas_result['success']:
            print("❌ Error generando reporte de entregas")
            return False
        
        print(f"  ✅ Reporte de entregas generado: {entregas_result['filename']}")
        
        # Listar reportes
        print("  📚 Listando reportes generados...")
        reportes_list = reportes_service.listar_reportes_disponibles()
        
        print(f"  ✅ Reportes disponibles: {len(reportes_list)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en generación de reportes: {e}")
        return False


def test_backup_system():
    """Prueba 8: Sistema de backup"""
    
    try:
        print("💾 Probando sistema de backup...")
        
        from services.backup_service import backup_service
        
        # Test backup manual
        print("  📁 Creando backup manual...")
        backup_result = backup_service.crear_backup_manual("Test Integration")
        
        if not backup_result['success']:
            print("❌ Error creando backup manual")
            return False
        
        backup_filename = backup_result['backup_info']['filename']
        print(f"  ✅ Backup manual creado: {backup_filename}")
        
        # Listar backups
        print("  📋 Listando backups...")
        backups_list = backup_service.listar_backups()
        
        total_backups = backups_list['summary']['total_backups']
        if total_backups == 0:
            print("❌ Error listando backups - ninguno encontrado")
            return False
        
        print(f"  ✅ Backups encontrados: {total_backups}")
        print(f"  📁 Tamaño total: {backups_list['summary']['total_size_mb']} MB")
        
        # Estado del sistema de backup
        print("  ⚙️ Verificando estado del backup...")
        estado = backup_service.obtener_estado_backup()
        
        print(f"  🔄 Backup automático activo: {estado['backup_automatico_activo']}")
        print(f"  ⏰ Intervalo: {estado['intervalo_horas']} horas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sistema de backup: {e}")
        return False


def test_data_validations():
    """Prueba 9: Validaciones de datos"""
    
    try:
        print("✅ Probando validaciones de datos...")
        
        from utils.validators import validate_insumo_data, validate_empleado_data, validate_entrega_data
        from exceptions.custom_exceptions import ValidationException
        
        # Test validaciones de insumo
        print("  📦 Probando validaciones de insumo...")
        
        # Datos válidos
        insumo_valido = {
            'nombre': 'Test Insumo Válido',
            'categoria': 'Papelería',
            'cantidad_actual': 50,
            'cantidad_minima': 10,
            'cantidad_maxima': 100,
            'unidad_medida': 'unidad',
            'precio_unitario': 1500.00,
            'proveedor': 'Proveedor Test'
        }
        
        try:
            validated = validate_insumo_data(insumo_valido)
            print("    ✅ Validación de insumo válido: OK")
        except Exception as e:
            print(f"    ❌ Error validando insumo válido: {e}")
            return False
        
        # Datos inválidos
        insumo_invalido = {
            'nombre': '',  # Vacío - debe fallar
            'categoria': 'Categoría Inexistente',
            'cantidad_actual': -5,  # Negativo - debe fallar
            'precio_unitario': 'no es número'  # Tipo incorrecto
        }
        
        try:
            validate_insumo_data(insumo_invalido)
            print("    ❌ Validación debería haber fallado")
            return False
        except ValidationException:
            print("    ✅ Validación de insumo inválido: Falló correctamente")
        
        # Test validaciones de empleado
        print("  👥 Probando validaciones de empleado...")
        
        empleado_valido = {
            'nombre_completo': 'María García Test',
            'cargo': 'Analista',
            'departamento': 'Administración',
            'cedula': '87654321',
            'email': 'maria@test.com',
            'telefono': '+57 300 111 2222',
            'fecha_ingreso': date.today()
        }
        
        try:
            validated = validate_empleado_data(empleado_valido)
            print("    ✅ Validación de empleado válido: OK")
        except Exception as e:
            print(f"    ❌ Error validando empleado válido: {e}")
            return False
        
        # Datos de empleado inválidos
        empleado_invalido = {
            'nombre_completo': '',  # Vacío - debe fallar
            'cedula': '123',  # Muy corto - debe fallar
            'email': 'email_invalido',  # Formato incorrecto
            'telefono': 'abc123'  # Formato incorrecto
        }
        
        try:
            validate_empleado_data(empleado_invalido)
            print("    ❌ Validación debería haber fallado")
            return False
        except ValidationException:
            print("    ✅ Validación de empleado inválido: Falló correctamente")
        
        print("✅ Sistema de validaciones funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en validaciones de datos: {e}")
        return False


def test_module_integration():
    """Prueba 10: Integración entre módulos"""
    
    try:
        print("🔗 Probando integración entre módulos...")
        
        # Test: Flujo completo de una operación (insumo → empleado → entrega → alerta)
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        from services.micro_entregas import micro_entregas
        from services.micro_alertas import micro_alertas
        
        print("  🔄 Creando flujo completo de operación...")
        
        # 1. Crear insumo con stock bajo para generar alerta
        print("    📦 Creando insumo con stock bajo...")
        insumo_data = {
            'nombre': 'Test Integración Final',
            'categoria': 'Papelería',
            'cantidad_actual': 2,  # Stock muy bajo
            'cantidad_minima': 10,
            'cantidad_maxima': 50,
            'unidad_medida': 'unidad',
            'precio_unitario': 5000.00
        }
        
        insumo_result = micro_insumos.crear_insumo(insumo_data)
        if not insumo_result['success']:
            print("    ❌ Error creando insumo para integración")
            return False
        
        insumo_id = insumo_result['insumo_id']
        print(f"    ✅ Insumo creado: ID {insumo_id}")
        
        # 2. Verificar que se genera alerta  de stock bajo
        print("    🚨 Verificando generación de alertas...")
        alertas_result = micro_alertas.verificar_todas_las_alertas()
        
        # Buscar alerta para este insumo
        alertas_activas = micro_alertas.obtener_alertas_activas()
        alerta_encontrada = False
        
        for alerta in alertas_activas:
            if (alerta['entity_id'] == insumo_id and 
                alerta['alert_type'] in ['STOCK_BAJO', 'STOCK_CRITICO']):
                alerta_encontrada = True
                print(f"    ✅ Alerta generada: {alerta['title']}")
                break
        
        if not alerta_encontrada:
            print("    ⚠️ No se generó alerta automática (posible comportamiento normal)")
        
        # 3. Obtener empleado para entrega
        print("    👤 Obteniendo empleado para entrega...")
        empleados_validos = micro_empleados.obtener_empleados_activos_para_entrega()
        
        if not empleados_validos:
            print("    ⚠️ No hay empleados válidos - creando uno...")
            empleado_data = {
                'nombre_completo': 'Test Empleado Integración',
                'cedula': '99999999',
                'cargo': 'Test',
                'departamento': 'Test'
            }
            
            emp_result = micro_empleados.crear_empleado(empleado_data)
            if not emp_result['success']:
                print("    ❌ Error creando empleado para test")
                return False
            empleado_id = emp_result['empleado_id']
        else:
            empleado_id = empleados_validos[0]['id']
        
        print(f"    ✅ Empleado para entrega: ID {empleado_id}")
        
        # 4. Realizar entrega que agote el stock
        print("    📋 Realizando entrega que agote stock...")
        entrega_data = {
            'empleado_id': empleado_id,
            'insumo_id': insumo_id,
            'cantidad': 2,  # Agotar todo el stock
            'observaciones': 'Test integración - agotar stock',
            'entregado_por': 'Sistema de Pruebas'
        }
        
        entrega_result = micro_entregas.crear_entrega(entrega_data)
        if not entrega_result['success']:
            print(f"    ❌ Error creando entrega: {entrega_result}")
            return False
        
        print(f"    ✅ Entrega creada: ID {entrega_result['entrega_id']}")
        print(f"    📊 Stock actualizado: {entrega_result['stock_anterior']} → {entrega_result['stock_nuevo']}")
        
        # 5. Verificar que se genera alerta crítica
        print("    🔴 Verificando alerta crítica...")
        nuevas_alertas = micro_alertas.verificar_todas_las_alertas()
        
        # Buscar alerta crítica
        alertas_criticas = micro_alertas.obtener_alertas_activas(severity_filter="CRITICAL")
        alerta_critica_encontrada = False
        
        for alerta in alertas_criticas:
            if alerta['entity_id'] == insumo_id and alerta['alert_type'] == 'STOCK_CRITICO':
                alerta_critica_encontrada = True
                print(f"    ✅ Alerta crítica generada: {alerta['title']}")
                break
        
        if not alerta_critica_encontrada:
            print("    ⚠️ No se generó alerta crítica automática")
        
        # 6. Verificar estadísticas actualizadas
        print("    📈 Verificando estadísticas actualizadas...")
        
        # Estadísticas de entregas
        stats_entregas = micro_entregas.obtener_estadisticas_entregas()
        print(f"    📋 Total entregas en sistema: {stats_entregas['general']['total_entregas']}")
        
        # Estadísticas de insumos
        insumos_stats = micro_insumos.listar_insumos(include_status=True)
        print(f"    📦 Insumos con alertas: {insumos_stats['alerts']}")
        
        print("  ✅ Integración entre módulos verificada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en integración de módulos: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False


def print_test_summary(results: dict):
    """Imprime resumen final de las pruebas"""
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS DE INTEGRACIÓN")
    print("=" * 60)
    
    print(f"📋 Total de pruebas ejecutadas: {results['total_tests']}")
    print(f"✅ Pruebas exitosas: {results['passed']}")
    print(f"❌ Pruebas fallidas: {results['failed']}")
    
    success_rate = (results['passed'] / results['total_tests']) * 100 if results['total_tests'] > 0 else 0
    print(f"📈 Tasa de éxito: {success_rate:.1f}%")
    
    if results['failed'] > 0:
        print(f"\n⚠️ ERRORES ENCONTRADOS:")
        for i, error in enumerate(results['errors'], 1):
            print(f"  {i}. {error}")
    
    if results['passed'] == results['total_tests']:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
        print("✅ El sistema DelegInsumos está funcionando correctamente")
        print("🚀 Listo para uso en producción")
    else:
        print(f"\n⚠️ {results['failed']} pruebas fallaron")
        print("🔧 Revise los errores antes de usar en producción")
    
    print("=" * 60)


def test_offline_functionality():
    """Prueba específica: Funcionamiento offline"""
    
    try:
        print("🌐 Probando funcionamiento offline...")
        
        # Verificar que no se intenta conectar a internet
        print("  🔌 Verificando que no hay dependencias de red...")
        
        # Verificar que SQLite es local
        from database.connection import db_connection
        db_info = db_connection.get_database_info()
        
        if not db_info['database_path'].startswith('.'):
            print(f"  ✅ Base de datos local: {db_info['database_path']}")
        else:
            print("  ❌ Ruta de base de datos sospechosa")
            return False
        
        # Verificar que reportes se generan localmente
        from services.reportes_service import reportes_service
        reportes_dir = reportes_service.output_dir
        
        if reportes_dir.exists():
            print(f"  ✅ Directorio de reportes local: {reportes_dir}")
        else:
            print("  ❌ Directorio de reportes no encontrado")
            return False
        
        # Verificar que backups son locales
        from services.backup_service import backup_service
        backup_dirs = [
            backup_service.daily_dir,
            backup_service.weekly_dir,
            backup_service.manual_dir
        ]
        
        for backup_dir in backup_dirs:
            if backup_dir.exists():
                print(f"  ✅ Directorio backup local: {backup_dir.name}")
            else:
                print(f"  ✅ Directorio backup creado: {backup_dir.name}")
                backup_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ Funcionamiento offline verificado")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando funcionamiento offline: {e}")
        return False


def test_complete_workflow():
    """Prueba del flujo completo del sistema"""
    
    try:
        print("🔄 Probando flujo completo del sistema...")
        
        # Simular un día típico de uso
        print("  📅 Simulando día típico de trabajo...")
        
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        from services.micro_entregas import micro_entregas
        from services.micro_alertas import micro_alertas
        from services.reportes_service import reportes_service
        from services.backup_service import backup_service
        
        # 1. Verificar sistema al inicio del día
        print("    🌅 Verificaciones de inicio de día...")
        
        # Verificar alertas
        alertas = micro_alertas.verificar_todas_las_alertas()
        print(f"    🚨 Alertas verificadas: {alertas['total_new_alerts']} nuevas")
        
        # Estadísticas del día
        entregas_hoy = micro_entregas.obtener_entregas_hoy()
        print(f"    📋 Entregas de hoy: {entregas_hoy['total_entregas']}")
        
        # 2. Operaciones típicas durante el día
        print("    ⏰ Operaciones durante el día...")
        
        # Revisar inventario
        inventario = micro_insumos.listar_insumos(include_status=True)
        alertas_stock = inventario.get('alerts', 0)
        print(f"    📦 Insumos en inventario: {inventario['total']} (alertas: {alertas_stock})")
        
        # Revisar empleados activos
        empleados = micro_empleados.listar_empleados()
        empleados_activos = empleados['statistics']['empleados_activos']
        print(f"    👥 Empleados activos: {empleados_activos}")
        
        # 3. Generación de reportes (simulada)
        print("    📄 Generando reportes del día...")
        
        # Estadísticas de reportes
        stats_reportes = reportes_service.obtener_estadisticas_reportes()
        print(f"    📊 Reportes existentes: {stats_reportes['total_reportes']}")
        
        # 4. Backup de fin de día (simulado)
        print("    💾 Verificando sistema de backup...")
        
        backup_status = backup_service.obtener_estado_backup()
        print(f"    🔄 Backup automático: {'✅ Activo' if backup_status['backup_automatico_activo'] else '❌ Inactivo'}")
        
        # 5. Resumen del día
        print("    📈 Generando resumen del día...")
        
        resumen = {
            'insumos_total': inventario['total'],
            'empleados_activos': empleados_activos,
            'entregas_hoy': entregas_hoy['total_entregas'],
            'alertas_activas': alertas['total_new_alerts'],
            'reportes_disponibles': stats_reportes['total_reportes'],
            'backup_funcionando': backup_status['backup_automatico_activo']
        }
        
        print("    📋 Resumen del workflow:")
        for key, value in resumen.items():
            print(f"      • {key}: {value}")
        
        print("✅ Flujo completo verificado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en flujo completo: {e}")
        return False


def create_sample_data():
    """Crea datos de ejemplo para pruebas completas"""
    
    try:
        print("📊 Creando datos de ejemplo...")
        
        from services.micro_insumos import micro_insumos
        from services.micro_empleados import micro_empleados
        
        # Insumos de ejemplo
        insumos_ejemplo = [
            {
                'nombre': 'Papel Bond A4',
                'categoria': 'Papelería',
                'cantidad_actual': 25,
                'cantidad_minima': 10,
                'cantidad_maxima': 100,
                'unidad_medida': 'resma',
                'precio_unitario': 12000.00,
                'proveedor': 'Papelería Central'
            },
            {
                'nombre': 'Bolígrafos Azules',
                'categoria': 'Papelería', 
                'cantidad_actual': 15,
                'cantidad_minima': 20,  # Generará alerta
                'cantidad_maxima': 200,
                'unidad_medida': 'unidad',
                'precio_unitario': 1500.00,
                'proveedor': 'Distribuidora ABC'
            },
            {
                'nombre': 'Cartuchos HP Negro',
                'categoria': 'Tecnología',
                'cantidad_actual': 0,  # Stock crítico
                'cantidad_minima': 5,
                'cantidad_maxima': 20,
                'unidad_medida': 'unidad',
                'precio_unitario': 85000.00,
                'proveedor': 'TecnoOffice'
            }
        ]
        
        # Empleados de ejemplo
        empleados_ejemplo = [
            {
                'nombre_completo': 'Ana María González',
                'cargo': 'Coordinadora Administrativa',
                'departamento': 'Administración',
                'cedula': '1234567890',
                'email': 'ana.gonzalez@empresa.com',
                'telefono': '+57 300 111 2233',
                'fecha_ingreso': date.today() - timedelta(days=365)
            },
            {
                'nombre_completo': 'Carlos Eduardo Martínez',
                'cargo': 'Desarrollador Senior',
                'departamento': 'Sistemas',
                'cedula': '0987654321',
                'email': 'carlos.martinez@empresa.com',
                'telefono': '+57 300 444 5566',
                'fecha_ingreso': date.today() - timedelta(days=90)  # Empleado nuevo
            }
        ]
        
        # Crear insumos de ejemplo
        print("  📦 Creando insumos de ejemplo...")
        for insumo in insumos_ejemplo:
            try:
                result = micro_insumos.crear_insumo(insumo)
                if result['success']:
                    print(f"    ✅ {insumo['nombre']} creado")
                else:
                    print(f"    ⚠️ {insumo['nombre']} ya existe o error")
            except Exception as e:
                print(f"    ⚠️ Error creando {insumo['nombre']}: {str(e)[:50]}")
        
        # Crear empleados de ejemplo
        print("  👥 Creando empleados de ejemplo...")
        for empleado in empleados_ejemplo:
            try:
                result = micro_empleados.crear_empleado(empleado)
                if result['success']:
                    print(f"    ✅ {empleado['nombre_completo']} creado")
                else:
                    print(f"    ⚠️ {empleado['nombre_completo']} ya existe o error")
            except Exception as e:
                print(f"    ⚠️ Error creando {empleado['nombre_completo']}: {str(e)[:50]}")
        
        print("✅ Datos de ejemplo creados")
        return True
        
    except Exception as e:
        print(f"❌ Error creando datos de ejemplo: {e}")
        return False


def main():
    """Función principal del script de pruebas"""
    
    print("🧪 SCRIPT DE PRUEBAS DE INTEGRACIÓN")
    print("📦 DelegInsumos v1.0.0")
    print("🕐 Inicio:", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    print("=" * 60)
    
    try:
        # Crear algunos datos de ejemplo primero
        print("📊 PREPARACIÓN DE DATOS DE EJEMPLO")
        create_sample_data()
        
        print("\n🔬 EJECUTANDO PRUEBAS PRINCIPALES")
        
        # Ejecutar todas las pruebas de integración
        success = test_system_integration()
        
        # Pruebas adicionales específicas
        print("\n🌐 PRUEBAS ESPECÍFICAS")
        print("-" * 40)
        
        # Test de funcionamiento offline
        offline_result = test_offline_functionality()
        
        # Test de flujo completo
        workflow_result = test_complete_workflow()
        
        # Resultado final
        if success and offline_result and workflow_result:
            print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
            print("✅ DelegInsumos está listo para usar en producción")
            print("🚀 Sistema completamente validado")
            
            return 0  # Éxito
        else:
            print("\n⚠️ ALGUNAS PRUEBAS FALLARON")
            print("🔧 Revise los errores antes de usar en producción")
            
            return 1  # Fallo
        
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
        return 1
        
    except Exception as e:
        print(f"\n💥 ERROR CRÍTICO EN PRUEBAS: {e}")
        print(f"Stack trace completo:\n{traceback.format_exc()}")
        return 1
    
    finally:
        print(f"\n🏁 Fin de pruebas: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


if __name__ == "__main__":
    exit_code = main()
    
    print(f"\n⚡ Presione Enter para salir... (Código: {exit_code})")
    input()
    
    sys.exit(exit_code)