from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import handle_db_exception, parse_date_field, parse_text, require_confirmation


facturas_bp = Blueprint("facturas", __name__)

FACTURA_ESTADOS = ("PENDIENTE", "PAGADA", "ANULADA")


def _obtener_factura(connection, factura_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                f.id_factura,
                f.numero_factura,
                f.id_orden,
                f.fecha_emision,
                f.subtotal,
                f.impuesto,
                f.total,
                f.estado,
                f.fecha_pago,
                o.numero_orden,
                o.fecha_programada,
                c.razon_social AS cliente,
                r.nombre AS ruta
            FROM FACTURA f
            INNER JOIN ORDEN_SERVICIO o ON o.id_orden = f.id_orden
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            WHERE f.id_factura = %s
            """,
            (factura_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


@facturas_bp.get("/")
def listar_facturas():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                f.id_factura,
                f.numero_factura,
                f.fecha_emision,
                f.total,
                f.estado,
                f.fecha_pago,
                o.numero_orden,
                c.razon_social AS cliente
            FROM FACTURA f
            INNER JOIN ORDEN_SERVICIO o ON o.id_orden = f.id_orden
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            ORDER BY f.fecha_emision DESC, f.id_factura DESC
            """
        )
        facturas = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("facturas/lista.html", facturas=facturas)


@facturas_bp.get("/<int:factura_id>")
def detalle_factura(factura_id):
    connection = get_db_connection()
    try:
        factura = _obtener_factura(connection, factura_id)
        if not factura:
            flash("La factura solicitada no existe.", "error")
            return redirect(url_for("facturas.listar_facturas"))

        return render_template("facturas/detalle.html", factura=factura)
    finally:
        connection.close()


@facturas_bp.route("/nuevo", methods=["GET", "POST"])
def nueva_factura():
    flash(
        "Las facturas se generan automáticamente al entregar órdenes. Este módulo opera en modo de solo lectura operativa.",
        "info",
    )
    return redirect(url_for("facturas.listar_facturas"))


@facturas_bp.route("/<int:factura_id>/editar", methods=["GET", "POST"])
def editar_factura(factura_id):
    connection = get_db_connection()
    try:
        factura_db = _obtener_factura(connection, factura_id)
        if not factura_db:
            flash("La factura solicitada no existe.", "error")
            return redirect(url_for("facturas.listar_facturas"))

        factura = {
            "estado": factura_db["estado"],
            "fecha_pago": factura_db["fecha_pago"].isoformat() if factura_db["fecha_pago"] else "",
        }

        if request.method == "POST":
            errores = []
            estado = parse_text(request.form.get("estado"), upper=True)
            fecha_pago = parse_date_field(
                request.form.get("fecha_pago"),
                "La fecha de pago",
                errores,
                required=False,
            )
            if estado not in FACTURA_ESTADOS:
                errores.append("Debes seleccionar un estado válido para la factura.")

            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE FACTURA
                        SET estado = %s,
                            fecha_pago = %s
                        WHERE id_factura = %s
                        """,
                        (
                            estado,
                            fecha_pago.isoformat() if fecha_pago else None,
                            factura_id,
                        ),
                    )
                    connection.commit()
                    flash("Factura actualizada correctamente.", "success")
                    return redirect(url_for("facturas.detalle_factura", factura_id=factura_id))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

                factura = {
                    "estado": estado,
                    "fecha_pago": fecha_pago.isoformat() if fecha_pago else "",
                }

        return render_template(
            "facturas/form.html",
            factura=factura,
            factura_base=factura_db,
            estados=FACTURA_ESTADOS,
            modo="editar",
            factura_id=factura_id,
        )
    finally:
        connection.close()


@facturas_bp.post("/<int:factura_id>/eliminar")
def eliminar_factura(factura_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación de la factura antes de continuar.",
    ):
        return redirect(url_for("facturas.detalle_factura", factura_id=factura_id))

    flash(
        "Las facturas son registros contables y no se eliminan desde la aplicación.",
        "error",
    )
    return redirect(url_for("facturas.detalle_factura", factura_id=factura_id))
