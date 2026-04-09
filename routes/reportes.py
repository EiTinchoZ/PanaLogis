import warnings
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import parse_text, require_confirmation


reportes_bp = Blueprint("reportes", __name__)


def _parse_optional_int(raw_value, minimum=None, maximum=None):
    value = parse_text(raw_value)
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if minimum is not None and parsed < minimum:
        return None
    if maximum is not None and parsed > maximum:
        return None
    return parsed


def _fetch_callproc_rows(cursor, procedure_name, params):
    cursor.callproc(procedure_name, params)
    stored_results = getattr(cursor, "stored_results")

    if callable(stored_results):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result_sets = list(stored_results())
    else:
        result_sets = list(stored_results)

    for result in result_sets:
        rows = result.fetchall()
        if rows:
            return rows
    return []


@reportes_bp.get("/")
def listar_reportes():
    today = date.today()
    anio = _parse_optional_int(request.args.get("anio"), minimum=2000, maximum=2100)
    mes = _parse_optional_int(request.args.get("mes"), minimum=1, maximum=12)

    filtros = {
        "anio": anio if anio is not None else today.year,
        "mes": mes if mes is not None else today.month,
    }

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Q1: Estado actual de la flota
        cursor.execute(
            """
            SELECT
                v.placa,
                v.marca,
                v.modelo,
                tv.descripcion AS tipo_vehiculo,
                v.estado,
                v.kilometraje
            FROM VEHICULO v
            INNER JOIN TIPO_VEHICULO tv ON tv.id_tipo_vehiculo = v.id_tipo_vehiculo
            ORDER BY v.estado, v.placa
            """
        )
        estado_flota = cursor.fetchall()

        # Q2: Conductores disponibles
        cursor.execute(
            """
            SELECT
                c.cedula,
                CONCAT(c.nombre, ' ', c.apellido) AS conductor,
                c.categoria_licencia,
                c.vences_licencia
            FROM CONDUCTOR c
            WHERE c.estado = 'ACTIVO'
              AND c.id_conductor NOT IN (
                  SELECT id_conductor
                  FROM ORDEN_SERVICIO
                  WHERE estado IN ('PENDIENTE', 'EN_TRANSITO')
              )
            ORDER BY conductor
            """
        )
        conductores_disponibles = cursor.fetchall()

        # Q3: Historial de servicios por cliente
        cursor.execute(
            """
            SELECT
                cl.razon_social,
                o.numero_orden,
                r.nombre AS ruta,
                o.fecha_programada,
                o.estado,
                IFNULL(CASE WHEN f.estado = 'ANULADA' THEN 0 ELSE f.total END, 0) AS monto_facturado
            FROM CLIENTE cl
            INNER JOIN ORDEN_SERVICIO o ON o.id_cliente = cl.id_cliente
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            LEFT JOIN FACTURA f ON f.id_orden = o.id_orden
            ORDER BY cl.razon_social, o.fecha_programada DESC
            """
        )
        historial_clientes = cursor.fetchall()

        # Q4: Rentabilidad por ruta
        rentabilidad_ruta = _fetch_callproc_rows(
            cursor,
            "sp_rentabilidad_ruta",
            [filtros["anio"], filtros["mes"]],
        )

        # Q5: Alertas de mantenimiento activo
        cursor.execute(
            """
            SELECT
                v.placa,
                v.marca,
                v.modelo,
                m.tipo,
                m.fecha_inicio,
                m.descripcion,
                m.taller
            FROM MANTENIMIENTO m
            INNER JOIN VEHICULO v ON v.id_vehiculo = m.id_vehiculo
            WHERE m.estado = 'EN_PROCESO'
            ORDER BY m.fecha_inicio
            """
        )
        alertas_mantenimiento = cursor.fetchall()

        # Q6: Conductores con más entregas
        cursor.execute(
            """
            SELECT
                CONCAT(c.nombre, ' ', c.apellido) AS conductor,
                COUNT(o.id_orden) AS entregas,
                SUM(f.total) AS valor_transportado
            FROM CONDUCTOR c
            INNER JOIN ORDEN_SERVICIO o
                ON o.id_conductor = c.id_conductor
               AND o.estado = 'ENTREGADO'
            INNER JOIN FACTURA f
                ON f.id_orden = o.id_orden
               AND f.estado <> 'ANULADA'
            GROUP BY c.id_conductor, conductor
            ORDER BY entregas DESC, valor_transportado DESC
            """
        )
        conductores_top = cursor.fetchall()

        # Q7: Consolidado de facturación mensual
        cursor.execute(
            """
            SELECT
                YEAR(f.fecha_emision) AS anio,
                MONTH(f.fecha_emision) AS mes,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN 1 ELSE 0 END) AS total_facturas,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN f.subtotal ELSE 0 END) AS ingresos_netos,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN f.impuesto ELSE 0 END) AS itbms,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN f.total ELSE 0 END) AS ingresos_totales,
                SUM(CASE WHEN f.estado = 'PAGADA' THEN f.total ELSE 0 END) AS cobrado,
                SUM(CASE WHEN f.estado = 'PENDIENTE' THEN f.total ELSE 0 END) AS por_cobrar
            FROM FACTURA f
            GROUP BY anio, mes
            ORDER BY anio DESC, mes DESC
            """
        )
        facturacion_mensual = cursor.fetchall()

        # Q8: Bitácora
        cursor.execute(
            """
            SELECT
                fecha_operacion,
                tabla_afectada,
                operacion,
                id_registro,
                descripcion
            FROM BITACORA
            ORDER BY fecha_operacion DESC
            LIMIT 50
            """
        )
        bitacora = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template(
        "reportes/lista.html",
        filtros=filtros,
        estado_flota=estado_flota,
        conductores_disponibles=conductores_disponibles,
        historial_clientes=historial_clientes,
        rentabilidad_ruta=rentabilidad_ruta,
        alertas_mantenimiento=alertas_mantenimiento,
        conductores_top=conductores_top,
        facturacion_mensual=facturacion_mensual,
        bitacora=bitacora,
    )


@reportes_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_reporte():
    flash("Los reportes se generan desde filtros y consultas predefinidas; no existe alta manual.", "info")
    return redirect(url_for("reportes.listar_reportes"))


@reportes_bp.route("/<string:reporte_id>/editar", methods=["GET", "POST"])
def editar_reporte(reporte_id):
    flash(
        f"El reporte '{reporte_id}' no se edita manualmente. Ajusta filtros desde el panel de reportes.",
        "info",
    )
    return redirect(url_for("reportes.listar_reportes"))


@reportes_bp.post("/<string:reporte_id>/eliminar")
def eliminar_reporte(reporte_id):
    if not require_confirmation(
        request.form,
        message="Confirma la acción si deseas limpiar un filtro de reporte.",
    ):
        return redirect(url_for("reportes.listar_reportes"))

    flash(
        f"El reporte '{reporte_id}' no se elimina porque forma parte del set funcional definido en el SQL.",
        "info",
    )
    return redirect(url_for("reportes.listar_reportes"))
