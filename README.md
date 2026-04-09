<div align="center">

<br/>

```
██████╗  █████╗ ███╗   ██╗ █████╗ ██╗      ██████╗  ██████╗ ██╗███████╗
██╔══██╗██╔══██╗████╗  ██║██╔══██╗██║     ██╔═══██╗██╔════╝ ██║██╔════╝
██████╔╝███████║██╔██╗ ██║███████║██║     ██║   ██║██║  ███╗██║███████╗
██╔═══╝ ██╔══██║██║╚██╗██║██╔══██║██║     ██║   ██║██║   ██║██║╚════██║
██║     ██║  ██║██║ ╚████║██║  ██║███████╗╚██████╔╝╚██████╔╝██║███████║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚══════╝
```

**Sistema de Gestión de Operaciones para Empresas de Transporte de Carga**

*Prototipo funcional de base de datos relacional — Bases de Datos I, ITSE 2026*

<br/>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.x-003545?style=for-the-badge&logo=mariadb&logoColor=white)](https://mariadb.org)
[![Vercel](https://img.shields.io/badge/Vercel-Deploy-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-D97706?style=for-the-badge)](LICENSE)

[![Status](https://img.shields.io/badge/Status-Production%20Ready-22c55e?style=flat-square)](https://github.com/EiTinchoZ/PanaLogis)
[![SQL](https://img.shields.io/badge/SQL-MariaDB%2FMySQL-blue?style=flat-square&logo=mysql)](database/panalogis.sql)
[![Tests](https://img.shields.io/badge/Tests-12%2F12%20Passing-22c55e?style=flat-square)](tests/runtime_smoke.py)
[![Triggers](https://img.shields.io/badge/Triggers-6%20Active-D97706?style=flat-square)](database/panalogis.sql)
[![Stored%20Procs](https://img.shields.io/badge/Stored%20Procs-2-D97706?style=flat-square)](database/panalogis.sql)

<br/>

[**Live Demo**](https://panalogis.vercel.app) · [**Informe Técnico**](output/informe_final.html) · [**Manual de Usuario**](output/manual_usuario.html) · [**Script SQL**](database/panalogis.sql)

<br/>

</div>

---

## ¿Qué es PanaLogis?

PanaLogis es un **sistema de gestión operativa** para empresas de transporte de carga terrestre en Panamá. Centraliza el control de flota, conductores, clientes, órdenes de servicio, mantenimiento y facturación en una base de datos relacional normalizada hasta 3FN, con una interfaz web que expone esa lógica de forma operativa.

La característica técnica central del proyecto es que **toda la lógica de negocio crítica vive en la base de datos** — no en el código de la aplicación. Seis triggers y dos stored procedures garantizan integridad transaccional, generación automática de facturas y trazabilidad de operaciones, sin importar qué interfaz acceda al sistema.

> *"La base de datos es el único punto de verdad de la operación."*

---

## Features

```
┌─────────────────────────────────────────────────────────────────┐
│  MÓDULOS DEL SISTEMA                                            │
├────────────────────┬────────────────────────────────────────────┤
│  Dashboard          │  KPIs en tiempo real, copiloto IA,         │
│                    │  bitácora, radar financiero                 │
├────────────────────┼────────────────────────────────────────────┤
│  Flota             │  Gestión de vehículos + tipos de unidad    │
│  Conductores       │  Control de licencias y disponibilidad     │
│  Mantenimiento     │  Ciclo preventivo/correctivo con triggers  │
├────────────────────┼────────────────────────────────────────────┤
│  Clientes          │  Directorio comercial con historial        │
│  Órdenes           │  Alta via stored procedure transaccional   │
│  Facturación       │  Generación automática al entregar orden   │
├────────────────────┼────────────────────────────────────────────┤
│  Reportes          │  8 reportes — flota, rentabilidad,        │
│                    │  conductores, financiero, bitácora         │
└────────────────────┴────────────────────────────────────────────┘
```

**Automatización en la BD:**

| Trigger | Qué hace |
|---------|----------|
| `trg_check_conductor_libre` | Bloquea conductor con orden activa (BEFORE INSERT) |
| `trg_check_vehiculo_disponible` | Bloquea vehículo en mantenimiento (BEFORE INSERT) |
| `trg_generar_factura` | Genera factura al entregar una orden (AFTER UPDATE) |
| `trg_bitacora_orden` | Auditoría automática de cambios de estado (AFTER UPDATE) |
| `trg_vehiculo_a_mantenimiento` | Cambia estado del vehículo al abrir mantenimiento (AFTER INSERT) |
| `trg_vehiculo_liberado` | Restaura vehículo al completar mantenimiento (AFTER UPDATE) |

| Stored Procedure | Función |
|-----------------|---------|
| `sp_crear_orden(...)` | Transacción completa con EXIT HANDLER, genera número ORD-AAAA-NNNNNN |
| `sp_rentabilidad_ruta(anio, mes)` | Reporte financiero por ruta, excluye facturas ANULADA |

---

## Stack

```
┌──────────────────────────────────────────────────┐
│                   CLIENTE                        │
│         HTML · CSS (INK/AMBER/SLATE)             │
│         Space Grotesk · Space Mono · Doto        │
└─────────────────────┬────────────────────────────┘
                      │ HTTP
┌─────────────────────▼────────────────────────────┐
│               FLASK (Python 3.10+)               │
│   8 Blueprints · Jinja2 · WTForms-free forms     │
│   AI Service (Groq llama-3.3-70b / local)       │
└─────────────────────┬────────────────────────────┘
                      │ mysql-connector-python
┌─────────────────────▼────────────────────────────┐
│              MariaDB 10.x / MySQL 8.x            │
│   12 tablas · 6 triggers · 2 stored procedures   │
│   3FN · utf8mb4 · 3 niveles de usuario           │
└──────────────────────────────────────────────────┘
```

**Deployment:**
- **Frontend + Backend:** Vercel (Python serverless)
- **Base de datos cloud:** Supabase Postgres (adapter de deploy)
- **Local:** XAMPP (MariaDB) + Python

---

## Arquitectura de la BD

```
TIPO_VEHICULO ──< VEHICULO ──< MANTENIMIENTO
                    │
                    └──────────────────────┐
CONDUCTOR ─────────────────────────────┐  │
CLIENTE ────────────────────────────┐  │  │
RUTA ───────────────────────────┐   │  │  │
TIPO_CARGA ─────────────────┐   │   │  │  │
                            ▼   ▼   ▼  ▼  │
                        ORDEN_SERVICIO ───┘
                              │
                              │ (trigger AFTER UPDATE)
                              ▼
                           FACTURA (1:1)

ROL_USUARIO ──< USUARIO ──< BITACORA
                                ▲
                        (trigger AFTER UPDATE en ORDEN_SERVICIO)
```

**Normalización:** 3FN en todas las tablas. BITACORA en 2FN (justificado: propósito de auditoría requiere texto descriptivo sin joins adicionales).

---

## Quick Start — Local

### Requisitos

- Python 3.10+
- XAMPP con MariaDB activo (puerto 3306)

### Setup

```bash
# 1. Clonar el repositorio
git clone https://github.com/EiTinchoZ/PanaLogis.git
cd PanaLogis

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Importar la base de datos
mysql -u root -p --default-character-set=utf8mb4 < database/panalogis.sql

# 4. Levantar Flask
python app.py

# 5. Abrir en el navegador
# http://localhost:5000
```

### Variables de entorno (opcional)

Crea un archivo `.env` para sobrescribir los valores por defecto:

```env
PANALOGIS_DB_HOST=127.0.0.1
PANALOGIS_DB_PORT=3306
PANALOGIS_DB_USER=root
PANALOGIS_DB_PASSWORD=
PANALOGIS_DB_NAME=panalogis_db
SECRET_KEY=tu-clave-secreta
GROQ_API_KEY=tu-groq-api-key          # Opcional — activa el copiloto IA
PANALOGIS_AI_MODEL=llama-3.3-70b-versatile
```

### Ejecutar tests

```bash
python tests/runtime_smoke.py
# Expected: 12/12 tests OK
```

---

## Deploy en Vercel

PanaLogis está configurado para desplegarse en Vercel con Supabase como base de datos cloud gratuita. El proyecto mantiene MariaDB/MySQL como base oficial local y usa PostgreSQL solo como adapter de hosting para la demo online.

### 1. Crear la base en Supabase

1. Crear cuenta en [supabase.com](https://supabase.com) → plan gratuito
2. Crear un proyecto nuevo y esperar a que la base quede activa
3. Abrir **SQL Editor**
4. Ejecutar completo el archivo `database/supabase_postgres.sql`
5. Ir a **Project Settings → Database** y copiar la connection string o los datos de host/port/user/password/database

### 2. Deploy en Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/EiTinchoZ/PanaLogis)

O manualmente:

```bash
# Instalar Vercel CLI
npm i -g vercel

# Desde la carpeta del proyecto
vercel

# Configurar variables de entorno en vercel.com → Project → Settings → Environment Variables:
# PANALOGIS_DB_ENGINE   → postgres
# PANALOGIS_DB_URL      → connection string de Supabase (recomendado)
# PANALOGIS_DB_SSLMODE  → require
# SECRET_KEY            → cualquier string largo y aleatorio
#
# Alternativa sin URL:
# PANALOGIS_DB_HOST
# PANALOGIS_DB_PORT
# PANALOGIS_DB_USER
# PANALOGIS_DB_PASSWORD
# PANALOGIS_DB_NAME
# SECRET_KEY            → cualquier string largo y aleatorio
```

### 3. Verificar

Después del deploy, visitar la URL de Vercel. El sistema carga el dashboard con los datos de prueba incluidos en `database/panalogis.sql`.

---

## Estructura del proyecto

```
PanaLogis/
├── api/
│   └── index.py              ← Entry point para Vercel
├── database/
│   └── panalogis.sql         ← Script SQL completo (DDL + triggers + SPs + demo data)
├── output/
│   ├── informe_final.html    ← Informe técnico académico (imprimible a PDF)
│   └── manual_usuario.html   ← Manual de usuario completo
├── routes/
│   ├── _helpers.py           ← Utilidades compartidas (manejo de errores, triggers)
│   ├── vehiculos.py          ← CRUD flota
│   ├── conductores.py        ← CRUD conductores
│   ├── clientes.py           ← CRUD clientes
│   ├── ordenes.py            ← Órdenes via sp_crear_orden
│   ├── mantenimiento.py      ← Mantenimiento + control de estado vehículo
│   ├── facturas.py           ← Facturación (solo lectura + estado de pago)
│   ├── reportes.py           ← 8 reportes operativos
│   └── ai.py                 ← Copiloto IA (Groq + motor local)
├── services/
│   └── ai_service.py         ← Análisis operativo + integración Groq
├── static/
│   ├── css/panalogis.css     ← Design system INK/AMBER/SLATE
│   └── js/main.js            ← Interactividad, animaciones, copiloto
├── templates/
│   ├── base.html             ← Layout principal (sidebar + topbar)
│   ├── dashboard.html        ← Dashboard con KPIs y copiloto IA
│   ├── _macros.html          ← Componentes reutilizables Jinja2
│   ├── vehiculos/            ← lista.html, detalle.html, form.html
│   ├── conductores/
│   ├── clientes/
│   ├── ordenes/
│   ├── mantenimiento/
│   ├── facturas/
│   └── reportes/
├── tests/
│   └── runtime_smoke.py      ← Suite de 12 tests automatizados
├── app.py                    ← Entry point Flask (local)
├── config.py                 ← Configuración DB + DictionaryConnection
├── requirements.txt
├── vercel.json               ← Configuración de deploy Vercel
└── CLAUDE.md                 ← Instrucciones del agente de desarrollo
```

---

## Base de datos

### Tablas (12)

| Tabla | Descripción | Filas demo |
|-------|-------------|-----------|
| `TIPO_VEHICULO` | Clasificación y capacidad de unidades | 4 |
| `VEHICULO` | Flota con placa, marca, modelo, estado | 7 |
| `CONDUCTOR` | Personal con licencias y categorías | 5 |
| `CLIENTE` | Empresas con RUC y datos de contacto | 5 |
| `TIPO_CARGA` | Clasificación de mercancías | 5 |
| `RUTA` | Rutas con distancia, tiempo y tarifa base | 5 |
| `ROL_USUARIO` | Niveles de acceso (ADMIN/OPERADOR/CONSULTOR) | 3 |
| `USUARIO` | Cuentas del sistema | 1 |
| `ORDEN_SERVICIO` | Tabla central — ciclo operativo completo | 6 |
| `MANTENIMIENTO` | Historial de intervenciones técnicas | 2 |
| `FACTURA` | Generadas automáticamente por trigger | 3 |
| `BITACORA` | Auditoría automática de cambios de estado | 5+ |

### Usuarios de BD

| Usuario | Permisos | Contraseña demo |
|---------|----------|----------------|
| `pana_admin` | ALL PRIVILEGES | `Admin2026!` |
| `pana_operador` | SELECT, INSERT, UPDATE | `Oper2026!` |
| `pana_consultor` | SELECT | `Cons2026!` |

### Importar la BD

```bash
# Con XAMPP
mysql -u root -p --default-character-set=utf8mb4 < database/panalogis.sql

# Verificar triggers
mysql -u root panalogis_db -e "SHOW TRIGGERS;"

# Verificar stored procedures
mysql -u root panalogis_db -e "SHOW PROCEDURE STATUS WHERE Db = 'panalogis_db';"
```

---

## Consultas de ejemplo

```sql
-- Estado actual de la flota
SELECT v.placa, v.marca, v.modelo, tv.descripcion, v.estado, v.kilometraje
FROM VEHICULO v
JOIN TIPO_VEHICULO tv ON tv.id_tipo_vehiculo = v.id_tipo_vehiculo
ORDER BY v.estado, v.placa;

-- Rentabilidad por ruta (mes actual)
CALL sp_rentabilidad_ruta(YEAR(CURDATE()), MONTH(CURDATE()));

-- Conductores disponibles (sin orden activa)
SELECT CONCAT(c.nombre,' ',c.apellido) AS conductor, c.categoria_licencia, c.vences_licencia
FROM CONDUCTOR c
WHERE c.estado = 'ACTIVO'
  AND c.id_conductor NOT IN (
    SELECT id_conductor FROM ORDEN_SERVICIO
    WHERE estado IN ('PENDIENTE','EN_TRANSITO'));

-- Consolidado de facturación
SELECT
    YEAR(f.fecha_emision) AS anio,
    SUM(CASE WHEN f.estado='PAGADA'    THEN f.total ELSE 0 END) AS cobrado,
    SUM(CASE WHEN f.estado='PENDIENTE' THEN f.total ELSE 0 END) AS por_cobrar
FROM FACTURA f
GROUP BY anio;
```

---

## Copiloto IA

El dashboard incluye un copiloto operativo que analiza el estado actual de la BD y genera lecturas de turno, alertas y recomendaciones de acción.

**Funciona en dos modos:**
- **Motor local** — siempre disponible, análisis basado en reglas con datos reales
- **Groq IA** — análisis con lenguaje natural via `llama-3.3-70b-versatile`, activado con `GROQ_API_KEY`

```bash
# Para activar Groq, agregar al .env o a las variables de entorno de Vercel:
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Decisiones técnicas

**¿Por qué la lógica de negocio en la BD?**

Los triggers y stored procedures garantizan integridad sin importar qué interfaz acceda al sistema. Si en el futuro se agrega una app móvil, una API REST o una integración externa, las reglas (no asignar conductor ocupado, generar factura al entregar) siguen aplicándose porque viven en la BD, no en la aplicación.

**¿Por qué MariaDB/MySQL y no PostgreSQL?**

El stack fue definido por los requerimientos académicos (XAMPP + MariaDB). Por eso el archivo oficial del proyecto sigue siendo `database/panalogis.sql` y el flujo local usa MySQL/MariaDB. PostgreSQL aparece solo como adapter de deploy para Supabase, con un script paralelo (`database/supabase_postgres.sql`) que permite publicar la demo gratis sin alterar la rúbrica académica del proyecto.

**¿Por qué Flask y no FastAPI/Django?**

Flask permite mantener el proyecto ligero y entendible para propósitos académicos. La arquitectura de blueprints escala correctamente y el código de cada módulo es directo y sin abstracciones innecesarias.

**¿Por qué un design system propio?**

El sistema visual INK/AMBER/SLATE fue construido a medida (CSS puro, ~1200 líneas) para evitar dependencias de frameworks como Bootstrap que aumentan el peso y reducen el control sobre la UI. Space Grotesk + Space Mono dan una estética técnica consistente con el dominio del sistema.

---

## Documentación académica

Este proyecto fue desarrollado como entrega final de **Bases de Datos I** en el ITSE (Instituto Técnico Superior de Educación), Escuela de Innovación Digital — T.S. en Inteligencia Artificial.

| Documento | Descripción |
|-----------|-------------|
| [`output/informe_final.html`](output/informe_final.html) | Informe técnico completo siguiendo el formato del profesor (Lic. Arturo F. González R.) — secciones I a IX |
| [`output/manual_usuario.html`](output/manual_usuario.html) | Manual de usuario con instrucciones paso a paso para cada módulo |
| [`database/panalogis.sql`](database/panalogis.sql) | Script SQL completo con DDL, triggers, SPs y datos de demo |
| [`AGENTS.md`](AGENTS.md) | Log de sesiones de desarrollo — arquitectura y decisiones |

---

## Equipo

<table>
<tr>
<td align="center">
<b>Martín Bundy</b><br/>
<sub>8-954-1319</sub><br/>
<sub>Líder técnico · Developer principal</sub><br/>
<sub>Arquitectura · Frontend · Backend · Integración IA</sub>
</td>
<td align="center">
<b>Miguel Herrera Briceño</b><br/>
<sub>8-819-1613</sub><br/>
<sub>Analista SQL · QA</sub><br/>
<sub>Diseño BD · Testing funcional · Investigación SQL avanzado</sub>
</td>
<td align="center">
<b>Jesús De León</b><br/>
<sub>Documentador · Presentación</sub><br/>
<sub>Manual de usuario · Sustentación oral</sub>
</td>
</tr>
</table>

---

## Para el CV

Si encontraste este proyecto y quieres usarlo como referencia de lo que se puede construir con Flask + MariaDB en un contexto académico:

- **Lo interesante técnicamente:** el uso de triggers para automatizar lógica de negocio, el stored procedure transaccional con manejo de errores SQL, y el copiloto IA integrado directamente en el dashboard con datos reales de la BD.
- **Stack completo:** Python/Flask · MariaDB/MySQL · Jinja2 · CSS puro · JS vanilla · Vercel · Groq API
- **Patterns usados:** Blueprint architecture · Repository pattern (via `_helpers.py`) · DictionaryConnection proxy · Graceful degradation (AI fallback)

---

## License

MIT — ver [LICENSE](LICENSE) para detalles.

---

<div align="center">

**ITSE · Bases de Datos I · 1Q-2026**

*Bundy · Herrera · De León*

</div>
