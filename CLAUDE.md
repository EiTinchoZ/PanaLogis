# CLAUDE.md — PanaLogis Dev System

> Archivo de instrucciones del proyecto para Claude Code.
> Leído automáticamente al iniciar cada sesión de trabajo.
> Última actualización: abril 2026

---

## 1. CONTEXTO DEL PROYECTO

**Nombre:** PanaLogis — Sistema de Gestión de Operaciones para Empresas de Transporte de Carga
**Materia:** Bases de Datos I — ITSE (Técnico Superior en Inteligencia Artificial)
**Entrega final:** 18 de abril de 2026
**Stack:** Python / Flask + MariaDB 10.x (XAMPP) + HTML/CSS/JS

### Equipo humano

| Integrante | Rol |
|---|---|
| Martín Bundy (Tín) | Product Owner / Líder Técnico / Developer Principal |
| Miguel Herrera | Analista SQL / QA / Testing |
| Jesús De León | Documentador / Presentación oral |

### Agentes de desarrollo

| Agente | Responsabilidad asignada |
|---|---|
| **Claude Code** | Arquitectura del sistema, todo lo gráfico y de diseño frontend (HTML, CSS, componentes visuales, layouts, UX), revisión de código, documentación técnica, coordinación entre agentes, asignación de tareas a Codex |
| **Codex (OpenAI)** | Generación de código backend repetitivo (rutas Flask, consultas SQL parametrizadas, formularios, validaciones), scaffolding de módulos, generación de tests unitarios |

> **Regla de oro:** Claude Code es el agente principal y asigna dinámicamente subtareas a Codex. Codex no toma decisiones de arquitectura ni de diseño visual. Todo output de Codex pasa por revisión de Claude Code antes de integrarse.

---

## 2. ARQUITECTURA DEL PROYECTO

```
PanaLogis/
├── CLAUDE.md               ← Instrucciones del proyecto (este archivo)
├── AGENTS.md               ← Log vivo de progreso por sesión
├── app.py                  ← Entry point Flask
├── config.py               ← Configuración DB y variables de entorno
├── database/
│   └── panalogis.sql       ← Script SQL completo (DDL + triggers + SPs + datos)
├── routes/
│   ├── __init__.py
│   ├── vehiculos.py
│   ├── conductores.py
│   ├── clientes.py
│   ├── ordenes.py
│   ├── mantenimiento.py
│   ├── facturas.py
│   └── reportes.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── vehiculos/
│   ├── conductores/
│   ├── clientes/
│   ├── ordenes/
│   ├── mantenimiento/
│   ├── facturas/
│   └── reportes/
└── static/
    ├── css/
    │   └── panalogis.css
    └── js/
        └── main.js
```

---

## 3. ESQUEMA DE BASE DE DATOS

**SGBD:** MariaDB 10.x sobre XAMPP
**Base de datos:** `panalogis_db`
**Normalización:** 3FN en tablas principales. BITACORA en 2FN (decisión documentada).

### ENUMs críticos

```sql
-- VEHICULO: estado ENUM('ACTIVO','MANTENIMIENTO','INACTIVO')
-- CONDUCTOR: estado ENUM('ACTIVO','INACTIVO','SUSPENDIDO')
-- CLIENTE: estado ENUM('ACTIVO','INACTIVO')
-- ORDEN_SERVICIO: estado ENUM('PENDIENTE','EN_TRANSITO','ENTREGADO','CANCELADO')
-- MANTENIMIENTO: tipo ENUM('PREVENTIVO','CORRECTIVO','REVISION')
--                estado ENUM('EN_PROCESO','COMPLETADO')
-- FACTURA: estado ENUM('PENDIENTE','PAGADA','ANULADA')
-- USUARIO: estado ENUM('ACTIVO','INACTIVO')
-- ROL_USUARIO: 'ADMINISTRADOR', 'OPERADOR', 'CONSULTOR'
```

### Triggers activos (NO reimplementar en app layer)

| Trigger | Acción |
|---------|--------|
| `trg_check_conductor_libre` | Bloquea conductor con orden activa |
| `trg_check_vehiculo_disponible` | Bloquea vehículo en MANTENIMIENTO |
| `trg_generar_factura` | Genera factura al cambiar orden a ENTREGADO |
| `trg_bitacora_orden` | Auditoría automática de cambios de estado |
| `trg_vehiculo_a_mantenimiento` | Cambia estado vehículo al abrir mantenimiento |
| `trg_vehiculo_liberado` | Restaura vehículo al completar mantenimiento |

### Stored Procedures

| SP | Uso |
|----|-----|
| `sp_crear_orden(...)` | Crea orden con transacción y manejo de errores |
| `sp_rentabilidad_ruta(p_anio, p_mes)` | Reporte de rentabilidad por ruta |

### Manejo de errores de triggers en Flask

```python
except Exception as e:
    if '45000' in str(e) or '1644' in str(type(e).__name__):
        flash(str(e), 'error')
    else:
        raise e
```

---

## 4. DESIGN SYSTEM — PALETA INK/AMBER/SLATE

```css
:root {
  --ink:       #0F172A;   /* Fondo oscuro principal */
  --slate:     #1E293B;   /* Fondo secciones / navbar / sidebar */
  --amber:     #D97706;   /* Acento principal / CTA */
  --amber-lt:  #FEF3C7;   /* Fondo suave amber */
  --sky:       #0369A1;   /* Acento secundario / info */
  --sky-lt:    #E0F2FE;   /* Fondo suave sky */
  --steel:     #475569;   /* Texto secundario */
  --mist:      #F1F5F9;   /* Fondo alternativo filas */
  --rule:      #CBD5E1;   /* Bordes y líneas */
  --white:     #FFFFFF;
}
```

**Tipografía:** Inter, Arial, sans-serif.
**Estilo general:** Dark sidebar + content area clara. Tablas con alternado MIST/WHITE. CTAs en amber.
**Toda pantalla nueva pasa por las skills `frontend-design` + `taste-skill` + `ui-ux-pro-max` antes de implementarse.**

---

## 5. MÓDULOS DEL SISTEMA

| # | Módulo | Ruta blueprint | Plantillas |
|---|--------|---------------|-----------|
| 1 | Flota (Vehículos) | `/vehiculos` | lista, detalle, form |
| 2 | Conductores | `/conductores` | lista, detalle, form |
| 3 | Clientes | `/clientes` | lista, detalle, form |
| 4 | Órdenes de Servicio | `/ordenes` | lista, detalle, form (usa sp_crear_orden) |
| 5 | Mantenimiento | `/mantenimiento` | lista, detalle, form |
| 6 | Facturación | `/facturas` | lista, detalle |
| 7 | Reportes | `/reportes` | dashboard de 8 consultas |
| 8 | Dashboard | `/` | KPIs + resumen operativo |

---

## 6. REGLAS DE TRABAJO

### Claude Code siempre debe:
1. Leer `AGENTS.md` al inicio de cada sesión
2. Analizar la solicitud antes de actuar
3. Presentar plan detallado y esperar aprobación explícita de Tín
4. Trabajar módulo por módulo, con checkpoint entre cada uno
5. Ante cualquier duda técnica: preguntar primero, no asumir
6. Respetar los ENUMs y el esquema. No inventar estados, tablas ni campos
7. Usar skills antes de cualquier trabajo visual

### Regla de ENUM/esquema:
```
[ALERTA DE CONTEXTO] La funcionalidad solicitada requiere modificar el esquema 
relacional documentado. ¿Deseas la instrucción DDL para actualizar la BD 
o prefieres adaptar el requerimiento a las tablas existentes?
```

---

## 7. ESTADO DEL PROYECTO

**Progreso actual: [██░░░░░░░░] 15%**

| Módulo / Entregable | Estado |
|--------------------|--------|
| Script SQL completo | ✅ Listo (pendiente de ubicar en /database) |
| Informe Fase 1 y 2 | ✅ Entregado al profesor |
| Estructura de carpetas | ✅ Creada |
| CLAUDE.md + AGENTS.md | ✅ Creados |
| config.py | ⏳ Pendiente |
| app.py + blueprints | ⏳ Pendiente |
| Módulo Flota | ⏳ Pendiente |
| Módulo Conductores | ⏳ Pendiente |
| Módulo Clientes | ⏳ Pendiente |
| Módulo Órdenes | ⏳ Pendiente |
| Módulo Mantenimiento | ⏳ Pendiente |
| Módulo Facturación | ⏳ Pendiente |
| Módulo Reportes (8 queries) | ⏳ Pendiente |
| Dashboard KPIs | ⏳ Pendiente |
| Design system CSS | ⏳ Pendiente |
| base.html + navegación | ⏳ Pendiente |
| Testing funcional (Miguel) | ⏳ Pendiente |
| Manual de usuario (Jesús) | ⏳ Pendiente |
| Presentación sustentación | ⏳ Pendiente |

---

## 8. COMANDOS DE REFERENCIA

```bash
# Instalar dependencias
pip install flask mysql-connector-python

# Levantar Flask
cd PanaLogis/
python app.py

# Importar BD (XAMPP corriendo en puerto 3306)
mysql -u root -p < database/panalogis.sql

# Verificar triggers
mysql -u root panalogis_db -e "SHOW TRIGGERS;"
```

---

*Este archivo es el contrato de trabajo del proyecto PanaLogis.*
*Claude Code debe leerlo completo al inicio de CADA sesión antes de actuar.*
