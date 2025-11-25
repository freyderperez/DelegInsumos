# DelegInsumos - Diagramas Arquitectónicos

## 1. Arquitectura General del Sistema

```mermaid
graph TB
    subgraph "DelegInsumos Desktop Application"
        subgraph "UI Layer - Tkinter/ttkbootstrap"
            UI1[Dashboard Tab]
            UI2[Insumos Tab]
            UI3[Empleados Tab]
            UI4[Entregas Tab]
            UI5[Reportes Tab]
        end
        
        subgraph "Services Layer - Business Logic"
            SVC1[Micro Insumos Service]
            SVC2[Micro Empleados Service]
            SVC3[Micro Entregas Service]
            SVC4[Micro Alertas Service]
            SVC5[Reportes Service]
        end
        
        subgraph "Database Layer - SQLite Operations"
            DB1[Connection Manager]
            DB2[CRUD Operations]
        end
        
        subgraph "Models Layer - Domain Entities"
            MDL1[Insumo Model]
            MDL2[Empleado Model]
            MDL3[Entrega Model]
        end
        
        subgraph "Storage Layer"
            SQLite[(SQLite Database)]
            FILES[Report Files PDF/Excel]
            BACKUP[Backup Files]
        end
    end
    
    UI1 --> SVC1
    UI2 --> SVC1
    UI3 --> SVC2
    UI4 --> SVC3
    UI5 --> SVC5
    
    SVC1 --> DB2
    SVC2 --> DB2
    SVC3 --> DB2
    SVC4 --> DB2
    SVC5 --> DB2
    
    DB2 --> DB1
    DB1 --> SQLite
    
    SVC1 -.-> MDL1
    SVC2 -.-> MDL2
    SVC3 -.-> MDL3
    
    SVC5 --> FILES
    SVC1 --> BACKUP
    
    style SQLite fill:#e1f5fe
    style FILES fill:#f3e5f5
    style BACKUP fill:#e8f5e8
```

## 2. Esquema de Base de Datos Relacional

```mermaid
erDiagram
    INSUMOS {
        int id PK
        varchar nombre
        varchar categoria
        int cantidad_actual
        int cantidad_minima
        int cantidad_maxima
        varchar unidad_medida
        varchar proveedor
        timestamp fecha_creacion
        timestamp fecha_actualizacion
        boolean activo
    }
    
    EMPLEADOS {
        int id PK
        varchar nombre_completo
        varchar cargo
        varchar departamento
        varchar cedula UK
        varchar email
        varchar telefono
        date fecha_ingreso
        timestamp fecha_creacion
        boolean activo
    }
    
    ENTREGAS {
        int id PK
        int empleado_id FK
        int insumo_id FK
        int cantidad
        timestamp fecha_entrega
        text observaciones
        varchar entregado_por
    }
    
    INSUMOS ||--o{ ENTREGAS : "se entrega en"
    EMPLEADOS ||--o{ ENTREGAS : "recibe"
```

## 3. Flujo de Comunicación entre Componentes

```mermaid
sequenceDiagram
    participant UI as UI Tab
    participant SVC as Service Layer
    participant DB as Database Operations
    participant SQLite as SQLite DB
    participant RPT as Report Generator
    
    Note over UI,SQLite: Flujo típico de operación CRUD
    
    UI->>+SVC: Request operation with data
    SVC->>+DB: Execute database operation
    DB->>+SQLite: SQL Query/Command
    SQLite-->>-DB: Result set
    DB-->>-SVC: Processed data
    SVC-->>-UI: Formatted response
    
    Note over UI,RPT: Flujo de generación de reportes
    
    UI->>+SVC: Request report generation
    SVC->>+DB: Fetch report data
    DB->>+SQLite: Complex query
    SQLite-->>-DB: Data for report
    DB-->>-SVC: Structured data
    SVC->>+RPT: Generate PDF/Excel
    RPT-->>-SVC: File path
    SVC-->>-UI: Report ready notification
```

## 4. Arquitectura de Microservicios Internos

```mermaid
graph LR
    subgraph "Internal Microservices Architecture"
        subgraph "Core Services"
            MS1[Insumos Service]
            MS2[Empleados Service] 
            MS3[Entregas Service]
        end
        
        subgraph "Support Services"
            MS4[Alertas Service]
            MS5[Reportes Service]
            MS6[Backup Service]
        end
        
        subgraph "Shared Components"
            VALID[Input Validator]
            LOG[Logger]
            CONFIG[Config Manager]
            CACHE[Cache Manager]
        end
    end
    
    MS1 --> VALID
    MS2 --> VALID
    MS3 --> VALID
    
    MS1 --> LOG
    MS2 --> LOG
    MS3 --> LOG
    MS4 --> LOG
    MS5 --> LOG
    MS6 --> LOG
    
    MS4 --> MS1
    MS5 --> MS1
    MS5 --> MS2
    MS5 --> MS3
    
    MS6 --> CONFIG
    MS5 --> CACHE
    
    style MS1 fill:#bbdefb
    style MS2 fill:#c8e6c9
    style MS3 fill:#ffccbc
    style MS4 fill:#f8bbd9
    style MS5 fill:#e1bee7
    style MS6 fill:#fff3e0
```

## 5. Sistema de Alertas y Notificaciones

```mermaid
flowchart TD
    START[Sistema Iniciado] --> CHECK[Verificar Stock]
    
    CHECK --> EVAL{Evaluar Niveles}
    
    EVAL -->|cantidad_actual < cantidad_minima| LOW[Alerta Stock Bajo]
    EVAL -->|cantidad_actual <= 0| CRIT[Alerta Stock Crítico]
    EVAL -->|cantidad_actual > cantidad_maxima| HIGH[Alerta Stock Exceso]
    EVAL -->|Normal| OK[Sin Alertas]
    
    LOW --> NOTIF[Generar Notificación]
    CRIT --> NOTIF
    HIGH --> NOTIF
    
    NOTIF --> UI_ALERT[Mostrar en Dashboard]
    NOTIF --> LOG_ALERT[Registrar en Log]
    NOTIF --> REPORT_ALERT[Incluir en Reporte]
    
    OK --> WAIT[Esperar Próxima Verificación]
    UI_ALERT --> WAIT
    LOG_ALERT --> WAIT
    REPORT_ALERT --> WAIT
    
    WAIT --> CHECK
    
    style CRIT fill:#ffcdd2
    style LOW fill:#ffe0b2
    style HIGH fill:#e8f5e8
    style OK fill:#e8f5e8
```

## 6. Flujo de Generación de Reportes

```mermaid
flowchart LR
    subgraph "Report Generation Flow"
        START[Usuario Solicita Reporte] --> SELECT[Seleccionar Tipo]
        
        SELECT --> INV[Reporte de Inventario]
        SELECT --> HIST[Histórico de Entregas]
        SELECT --> EMP[Empleados Activos]
        SELECT --> ALERT[Alertas de Stock]
        
        INV --> QUERY1[Query: SELECT * FROM insumos]
        HIST --> QUERY2[Query: JOIN entregas+empleados+insumos]
        EMP --> QUERY3[Query: SELECT * FROM empleados]
        ALERT --> QUERY4[Query: insumos WHERE cantidad < minima]
        
        QUERY1 --> PROCESS[Procesar Datos]
        QUERY2 --> PROCESS
        QUERY3 --> PROCESS
        QUERY4 --> PROCESS
        
        PROCESS --> FORMAT{Formato Seleccionado}
        
        FORMAT -->|PDF| PDF_GEN[Generar con ReportLab]
        FORMAT -->|Excel| EXCEL_GEN[Generar con OpenPyXL]
        
        PDF_GEN --> SAVE[Guardar en /reportes]
        EXCEL_GEN --> SAVE
        
        SAVE --> NOTIFY[Notificar Usuario]
    end
    
    style START fill:#e3f2fd
    style SAVE fill:#e8f5e8
    style NOTIFY fill:#f3e5f5
```

## 7. Arquitectura de Backup y Recuperación

```mermaid
graph TB
    subgraph "Backup Strategy"
        TRIGGER[Backup Trigger] --> TYPE{Tipo de Backup}
        
        TYPE -->|Automático Diario| AUTO_DAILY[Daily Backup]
        TYPE -->|Automático Semanal| AUTO_WEEKLY[Weekly Backup]
        TYPE -->|Manual Usuario| MANUAL[Manual Backup]
        TYPE -->|Pre-Actualización| PRE_UPDATE[Pre-Update Backup]
        
        AUTO_DAILY --> DAILY_FOLDER[/backups/daily/]
        AUTO_WEEKLY --> WEEKLY_FOLDER[/backups/weekly/]
        MANUAL --> MANUAL_FOLDER[/backups/manual/]
        PRE_UPDATE --> UPDATE_FOLDER[/backups/updates/]
        
        DAILY_FOLDER --> VALIDATE[Validar Integridad]
        WEEKLY_FOLDER --> VALIDATE
        MANUAL_FOLDER --> VALIDATE
        UPDATE_FOLDER --> VALIDATE
        
        VALIDATE -->|Éxito| SUCCESS[Backup Completado]
        VALIDATE -->|Error| ERROR[Error - Reintentar]
        
        ERROR --> RETRY[Reintento Backup]
        RETRY --> TYPE
        
        SUCCESS --> CLEANUP[Limpiar Backups Antiguos]
        CLEANUP --> FINISH[Proceso Terminado]
    end
    
    style SUCCESS fill:#c8e6c9
    style ERROR fill:#ffcdd2
    style FINISH fill:#e8f5e8
```

---

## Notas Técnicas de los Diagramas:

### Leyenda de Colores:
- **Azul claro**: Componentes de UI y entrada de usuario
- **Verde claro**: Procesos exitosos y estados normales
- **Naranja claro**: Alertas y advertencias
- **Rosa claro**: Errores y estados críticos
- **Violeta claro**: Procesos de salida y reportes

### Convenciones:
- **Líneas sólidas**: Flujo de datos principal
- **Líneas punteadas**: Dependencias o referencias
- **Flechas gruesas**: Procesos críticos del sistema
- **Subgrafos**: Agrupación lógica de componentes relacionados

### Patrones Arquitectónicos Implementados:
1. **Layered Architecture**: Separación clara entre UI, Services, Database
2. **Repository Pattern**: Encapsulación del acceso a datos
3. **Service Layer**: Lógica de negocio centralizada
4. **Event-Driven**: Sistema de alertas basado en eventos
5. **Strategy Pattern**: Múltiples formatos de reporte