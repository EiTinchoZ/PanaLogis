import os

from flask import Flask, redirect, render_template, url_for

from config import Config, get_db_connection
from routes.ai import ai_bp
from routes.clientes import clientes_bp
from routes.conductores import conductores_bp
from routes.facturas import facturas_bp
from routes.mantenimiento import mantenimiento_bp
from routes.ordenes import ordenes_bp
from routes.reportes import reportes_bp
from routes.vehiculos import vehiculos_bp


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config["SECRET_KEY"]

app.register_blueprint(vehiculos_bp, url_prefix="/vehiculos")
app.register_blueprint(conductores_bp, url_prefix="/conductores")
app.register_blueprint(clientes_bp, url_prefix="/clientes")
app.register_blueprint(ordenes_bp, url_prefix="/ordenes")
app.register_blueprint(mantenimiento_bp, url_prefix="/mantenimiento")
app.register_blueprint(facturas_bp, url_prefix="/facturas")
app.register_blueprint(reportes_bp, url_prefix="/reportes")
app.register_blueprint(ai_bp, url_prefix="/api/ai")


@app.get("/")
def index():
    return redirect(url_for("dashboard"))


@app.get("/dashboard")
def dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # KPIs de vehículos
        cur.execute("SELECT COUNT(*) AS total FROM VEHICULO")
        row = cur.fetchone()
        vehiculos_total = row["total"] if row else 0

        cur.execute("SELECT COUNT(*) AS n FROM VEHICULO WHERE estado = 'ACTIVO'")
        row = cur.fetchone()
        vehiculos_activos = row["n"] if row else 0

        cur.execute("SELECT COUNT(*) AS n FROM VEHICULO WHERE estado = 'MANTENIMIENTO'")
        row = cur.fetchone()
        vehiculos_mantenimiento = row["n"] if row else 0

        cur.execute("SELECT COUNT(*) AS n FROM VEHICULO WHERE estado = 'INACTIVO'")
        row = cur.fetchone()
        vehiculos_inactivos = row["n"] if row else 0

        # KPIs de órdenes
        cur.execute("SELECT COUNT(*) AS n FROM ORDEN_SERVICIO WHERE estado = 'EN_TRANSITO'")
        row = cur.fetchone()
        ordenes_activas = row["n"] if row else 0

        cur.execute("SELECT COUNT(*) AS n FROM ORDEN_SERVICIO WHERE estado = 'PENDIENTE'")
        row = cur.fetchone()
        ordenes_pendientes = row["n"] if row else 0

        # KPIs de conductores
        cur.execute("SELECT COUNT(*) AS total FROM CONDUCTOR")
        row = cur.fetchone()
        conductores_total = row["total"] if row else 0

        cur.execute("SELECT COUNT(*) AS n FROM CONDUCTOR WHERE estado = 'ACTIVO'")
        row = cur.fetchone()
        conductores_activos = row["n"] if row else 0

        kpis = {
            "vehiculos_total": vehiculos_total,
            "vehiculos_activos": vehiculos_activos,
            "vehiculos_mantenimiento": vehiculos_mantenimiento,
            "vehiculos_inactivos": vehiculos_inactivos,
            "ordenes_activas": ordenes_activas,
            "ordenes_pendientes": ordenes_pendientes,
            "conductores_total": conductores_total,
            "conductores_activos": conductores_activos,
        }

        # Últimas 8 órdenes
        cur.execute("""
            SELECT o.id_orden, o.numero_orden, r.nombre AS ruta,
                   r.origen, r.destino, o.estado, o.fecha_creacion,
                   c.razon_social AS cliente
            FROM ORDEN_SERVICIO o
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            ORDER BY o.fecha_creacion DESC
            LIMIT 8
        """)
        ordenes_recientes = cur.fetchall()

        # Vehículos en mantenimiento (para el panel de flota)
        cur.execute("""
            SELECT v.placa, v.marca, v.modelo
            FROM VEHICULO v
            WHERE v.estado = 'MANTENIMIENTO'
            ORDER BY v.placa
        """)
        vehiculos_mant = cur.fetchall()

        # Facturas pendientes (últimas 6)
        cur.execute("""
            SELECT f.id_factura, f.numero_factura, f.id_orden, f.total,
                   f.fecha_emision, c.razon_social AS nombre_cliente
            FROM FACTURA f
            LEFT JOIN ORDEN_SERVICIO o ON f.id_orden = o.id_orden
            LEFT JOIN CLIENTE c ON o.id_cliente = c.id_cliente
            WHERE f.estado = 'PENDIENTE'
            ORDER BY f.fecha_emision ASC
            LIMIT 6
        """)
        facturas_pendientes = cur.fetchall()

        cur.execute(
            """
            SELECT estado, COUNT(*) AS total
            FROM ORDEN_SERVICIO
            GROUP BY estado
            """
        )
        order_state_rows = cur.fetchall()
        order_state_map = {
            "PENDIENTE": {"label": "Pendientes", "tone": "amber"},
            "EN_TRANSITO": {"label": "En tránsito", "tone": "sky"},
            "ENTREGADO": {"label": "Entregadas", "tone": "green"},
            "CANCELADO": {"label": "Canceladas", "tone": "red"},
        }
        ordenes_estado = []
        max_ordenes_estado = 1
        for key in ("PENDIENTE", "EN_TRANSITO", "ENTREGADO", "CANCELADO"):
            total = next((row["total"] for row in order_state_rows if row["estado"] == key), 0)
            ordenes_estado.append(
                {
                    "key": key,
                    "label": order_state_map[key]["label"],
                    "tone": order_state_map[key]["tone"],
                    "total": total,
                }
            )
            max_ordenes_estado = max(max_ordenes_estado, total)

        cur.execute(
            """
            SELECT estado, COUNT(*) AS total_facturas, SUM(total) AS monto
            FROM FACTURA
            GROUP BY estado
            """
        )
        invoice_rows = cur.fetchall()
        invoice_map = {
            "PENDIENTE": {"label": "Pendiente", "tone": "amber"},
            "PAGADA": {"label": "Pagada", "tone": "green"},
            "ANULADA": {"label": "Anulada", "tone": "red"},
        }
        facturacion_estado = []
        max_facturacion_monto = 1.0
        for key in ("PENDIENTE", "PAGADA", "ANULADA"):
            total_facturas = next((row["total_facturas"] for row in invoice_rows if row["estado"] == key), 0)
            monto = float(next((row["monto"] for row in invoice_rows if row["estado"] == key), 0) or 0)
            facturacion_estado.append(
                {
                    "key": key,
                    "label": invoice_map[key]["label"],
                    "tone": invoice_map[key]["tone"],
                    "total_facturas": total_facturas,
                    "monto": monto,
                }
            )
            max_facturacion_monto = max(max_facturacion_monto, monto)

        cur.execute(
            """
            SELECT
                r.nombre AS ruta,
                r.origen,
                r.destino,
                COUNT(o.id_orden) AS servicios,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN f.total ELSE 0 END) AS ingresos
            FROM RUTA r
            LEFT JOIN ORDEN_SERVICIO o ON o.id_ruta = r.id_ruta
            LEFT JOIN FACTURA f ON f.id_orden = o.id_orden
            GROUP BY r.id_ruta, r.nombre, r.origen, r.destino
            ORDER BY servicios DESC, ingresos DESC, ruta ASC
            LIMIT 5
            """
        )
        rutas_heatmap = cur.fetchall()

        cur.execute(
            """
            SELECT fecha_operacion, operacion, descripcion
            FROM BITACORA
            ORDER BY fecha_operacion DESC
            LIMIT 4
            """
        )
        bitacora_reciente = cur.fetchall()

        ai_prompt_suggestions = [
            "Dame el resumen del turno.",
            "¿Qué riesgo operativo atiendo primero?",
            "Explícame la cobranza en simple.",
            "Lee la flota y el taller.",
        ]

        cur.close()
        conn.close()

    except Exception:
        app.logger.exception("No se pudieron cargar los datos del dashboard.")
        kpis = {
            "vehiculos_total": 0, "vehiculos_activos": 0,
            "vehiculos_mantenimiento": 0, "vehiculos_inactivos": 0,
            "ordenes_activas": 0, "ordenes_pendientes": 0,
            "conductores_total": 0, "conductores_activos": 0,
        }
        ordenes_recientes = []
        vehiculos_mant = []
        facturas_pendientes = []
        ordenes_estado = []
        facturacion_estado = []
        rutas_heatmap = []
        bitacora_reciente = []
        max_ordenes_estado = 1
        max_facturacion_monto = 1.0
        ai_prompt_suggestions = [
            "Dame el resumen del turno.",
            "¿Qué riesgo operativo atiendo primero?",
        ]

    return render_template(
        "dashboard.html",
        kpis=kpis,
        ordenes_recientes=ordenes_recientes,
        vehiculos_mantenimiento=vehiculos_mant,
        facturas_pendientes=facturas_pendientes,
        ordenes_estado=ordenes_estado,
        facturacion_estado=facturacion_estado,
        rutas_heatmap=rutas_heatmap,
        bitacora_reciente=bitacora_reciente,
        max_ordenes_estado=max_ordenes_estado,
        max_facturacion_monto=max_facturacion_monto,
        ai_prompt_suggestions=ai_prompt_suggestions,
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
