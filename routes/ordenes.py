from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import (
    call_sp_crear_orden,
    handle_db_exception,
    parse_date_field,
    parse_decimal_field,
    parse_int_field,
    parse_text,
    require_confirmation,
)


ordenes_bp = Blueprint("ordenes", __name__)

ORDEN_ESTADOS = ("PENDIENTE", "EN_TRANSITO", "ENTREGADO", "CANCELADO")


def _orden_default():
    return {
        "fecha_programada": "",
        "id_cliente": "",
        "id_ruta": "",
        "id_vehiculo": "",
        "id_conductor": "",
        "id_tipo_carga": "",
        "peso_kg": "",
        "descripcion": "",
        "estado": "PENDIENTE",
        "observaciones": "",
    }


def _obtener_catalogos(connection, orden_id=None):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT id_cliente, razon_social, estado
            FROM CLIENTE
            ORDER BY razon_social
            """
        )
        clientes = cursor.fetchall()

        cursor.execute(
            """
            SELECT id_ruta, nombre, origen, destino, tarifa_base
            FROM RUTA
            ORDER BY nombre
            """
        )
        rutas = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                v.id_vehiculo,
                v.placa,
                v.marca,
                v.modelo,
                v.estado,
                CASE
                    WHEN v.estado = 'ACTIVO' AND NOT EXISTS (
                        SELECT 1
                        FROM ORDEN_SERVICIO o
                        WHERE o.id_vehiculo = v.id_vehiculo
                          AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
                          AND (%s IS NULL OR o.id_orden <> %s)
                    ) THEN 1
                    ELSE 0
                END AS disponible,
                CASE
                    WHEN v.estado <> 'ACTIVO' THEN v.estado
                    WHEN EXISTS (
                        SELECT 1
                        FROM ORDEN_SERVICIO o
                        WHERE o.id_vehiculo = v.id_vehiculo
                          AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
                          AND (%s IS NULL OR o.id_orden <> %s)
                    ) THEN 'OCUPADO'
                    ELSE 'DISPONIBLE'
                END AS disponibilidad
            FROM VEHICULO v
            ORDER BY v.placa
            """,
            (orden_id, orden_id, orden_id, orden_id),
        )
        vehiculos = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                c.id_conductor,
                c.cedula,
                c.nombre,
                c.apellido,
                c.estado,
                CASE
                    WHEN c.estado = 'ACTIVO' AND NOT EXISTS (
                        SELECT 1
                        FROM ORDEN_SERVICIO o
                        WHERE o.id_conductor = c.id_conductor
                          AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
                          AND (%s IS NULL OR o.id_orden <> %s)
                    ) THEN 1
                    ELSE 0
                END AS disponible,
                CASE
                    WHEN c.estado <> 'ACTIVO' THEN c.estado
                    WHEN EXISTS (
                        SELECT 1
                        FROM ORDEN_SERVICIO o
                        WHERE o.id_conductor = c.id_conductor
                          AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
                          AND (%s IS NULL OR o.id_orden <> %s)
                    ) THEN 'OCUPADO'
                    ELSE 'DISPONIBLE'
                END AS disponibilidad
            FROM CONDUCTOR c
            ORDER BY c.nombre, c.apellido
            """,
            (orden_id, orden_id, orden_id, orden_id),
        )
        conductores = cursor.fetchall()

        cursor.execute(
            """
            SELECT id_tipo_carga, nombre, refrigeracion, es_peligrosa
            FROM TIPO_CARGA
            ORDER BY nombre
            """
        )
        tipos_carga = cursor.fetchall()

        return {
            "clientes": clientes,
            "rutas": rutas,
            "vehiculos": vehiculos,
            "conductores": conductores,
            "tipos_carga": tipos_carga,
        }
    finally:
        cursor.close()


def _obtener_orden(connection, orden_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                o.id_orden,
                o.numero_orden,
                o.fecha_creacion,
                o.fecha_programada,
                o.id_cliente,
                o.id_ruta,
                o.id_vehiculo,
                o.id_conductor,
                o.id_tipo_carga,
                o.peso_kg,
                o.descripcion,
                o.estado,
                o.observaciones,
                c.razon_social AS cliente,
                r.nombre AS ruta,
                r.origen,
                r.destino,
                v.placa,
                v.marca,
                v.modelo,
                CONCAT(d.nombre, ' ', d.apellido) AS conductor,
                tc.nombre AS tipo_carga
            FROM ORDEN_SERVICIO o
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            INNER JOIN VEHICULO v ON v.id_vehiculo = o.id_vehiculo
            INNER JOIN CONDUCTOR d ON d.id_conductor = o.id_conductor
            INNER JOIN TIPO_CARGA tc ON tc.id_tipo_carga = o.id_tipo_carga
            WHERE o.id_orden = %s
            """,
            (orden_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _obtener_factura_orden(connection, orden_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_factura,
                numero_factura,
                fecha_emision,
                subtotal,
                impuesto,
                total,
                estado,
                fecha_pago
            FROM FACTURA
            WHERE id_orden = %s
            """,
            (orden_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _obtener_bitacora_orden(connection, orden_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_bitacora,
                fecha_operacion,
                operacion,
                descripcion
            FROM BITACORA
            WHERE tabla_afectada = 'ORDEN_SERVICIO'
              AND id_registro = %s
            ORDER BY fecha_operacion DESC
            LIMIT 15
            """,
            (orden_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _validar_orden(form):
    errors = []
    fecha_programada = parse_date_field(
        form.get("fecha_programada"),
        "La fecha programada",
        errors,
    )
    id_cliente = parse_int_field(form.get("id_cliente"), "El cliente", errors, minimum=1)
    id_ruta = parse_int_field(form.get("id_ruta"), "La ruta", errors, minimum=1)
    id_vehiculo = parse_int_field(form.get("id_vehiculo"), "El vehículo", errors, minimum=1)
    id_conductor = parse_int_field(form.get("id_conductor"), "El conductor", errors, minimum=1)
    id_tipo_carga = parse_int_field(form.get("id_tipo_carga"), "El tipo de carga", errors, minimum=1)
    peso_kg = parse_decimal_field(form.get("peso_kg"), "El peso en kg", errors, minimum=Decimal("0.01"))
    estado = parse_text(form.get("estado"), upper=True) or "PENDIENTE"

    if estado not in ORDEN_ESTADOS:
        errors.append("Debes seleccionar un estado válido para la orden.")

    return errors, {
        "fecha_programada": fecha_programada.isoformat() if fecha_programada else parse_text(form.get("fecha_programada")),
        "id_cliente": id_cliente if id_cliente is not None else parse_text(form.get("id_cliente")),
        "id_ruta": id_ruta if id_ruta is not None else parse_text(form.get("id_ruta")),
        "id_vehiculo": id_vehiculo if id_vehiculo is not None else parse_text(form.get("id_vehiculo")),
        "id_conductor": id_conductor if id_conductor is not None else parse_text(form.get("id_conductor")),
        "id_tipo_carga": id_tipo_carga if id_tipo_carga is not None else parse_text(form.get("id_tipo_carga")),
        "peso_kg": str(peso_kg.quantize(Decimal("0.01"))) if peso_kg is not None else parse_text(form.get("peso_kg")),
        "descripcion": parse_text(form.get("descripcion")),
        "estado": estado,
        "observaciones": parse_text(form.get("observaciones")),
    }


def _validar_disponibilidad_orden(data, catalogos):
    errors = []
    clientes = {item["id_cliente"]: item for item in catalogos["clientes"]}
    rutas = {item["id_ruta"]: item for item in catalogos["rutas"]}
    vehiculos = {item["id_vehiculo"]: item for item in catalogos["vehiculos"]}
    conductores = {item["id_conductor"]: item for item in catalogos["conductores"]}
    tipos_carga = {item["id_tipo_carga"]: item for item in catalogos["tipos_carga"]}

    cliente = clientes.get(data["id_cliente"])
    if not cliente:
        errors.append("El cliente seleccionado no existe.")
    elif cliente["estado"] != "ACTIVO":
        errors.append("El cliente seleccionado no está activo.")

    if data["id_ruta"] not in rutas:
        errors.append("La ruta seleccionada no existe.")

    vehiculo = vehiculos.get(data["id_vehiculo"])
    if not vehiculo:
        errors.append("El vehículo seleccionado no existe.")
    elif not vehiculo["disponible"]:
        errors.append("El vehículo seleccionado no está disponible.")

    conductor = conductores.get(data["id_conductor"])
    if not conductor:
        errors.append("El conductor seleccionado no existe.")
    elif not conductor["disponible"]:
        errors.append("El conductor seleccionado no está disponible.")

    if data["id_tipo_carga"] not in tipos_carga:
        errors.append("El tipo de carga seleccionado no existe.")

    return errors


@ordenes_bp.get("/")
def listar_ordenes():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                o.id_orden,
                o.numero_orden,
                o.fecha_programada,
                o.estado,
                o.peso_kg,
                c.razon_social AS cliente,
                r.nombre AS ruta,
                v.placa AS vehiculo,
                CONCAT(d.nombre, ' ', d.apellido) AS conductor,
                COALESCE(f.total, 0) AS monto_facturado
            FROM ORDEN_SERVICIO o
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            INNER JOIN VEHICULO v ON v.id_vehiculo = o.id_vehiculo
            INNER JOIN CONDUCTOR d ON d.id_conductor = o.id_conductor
            LEFT JOIN FACTURA f ON f.id_orden = o.id_orden
            ORDER BY o.fecha_programada DESC, o.id_orden DESC
            """
        )
        ordenes = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("ordenes/lista.html", ordenes=ordenes)


@ordenes_bp.get("/<int:orden_id>")
def detalle_orden(orden_id):
    connection = get_db_connection()
    try:
        orden = _obtener_orden(connection, orden_id)
        if not orden:
            flash("La orden solicitada no existe.", "error")
            return redirect(url_for("ordenes.listar_ordenes"))

        factura = _obtener_factura_orden(connection, orden_id)
        bitacora = _obtener_bitacora_orden(connection, orden_id)
        return render_template(
            "ordenes/detalle.html",
            orden=orden,
            factura=factura,
            bitacora=bitacora,
        )
    finally:
        connection.close()


@ordenes_bp.route("/nuevo", methods=["GET", "POST"])
def nueva_orden():
    connection = get_db_connection()
    try:
        catalogos = _obtener_catalogos(connection)
        orden = _orden_default()

        if request.method == "POST":
            errores, orden = _validar_orden(request.form)
            errores.extend(_validar_disponibilidad_orden(orden, catalogos))
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    numero_orden, mensaje = call_sp_crear_orden(cursor, orden)
                    if numero_orden and orden["observaciones"]:
                        cursor.execute(
                            """
                            UPDATE ORDEN_SERVICIO
                            SET observaciones = %s
                            WHERE numero_orden = %s
                            """,
                            (orden["observaciones"], numero_orden),
                        )
                        connection.commit()
                    elif numero_orden:
                        connection.commit()
                    flash(mensaje or "Orden creada correctamente.", "success")
                    if numero_orden:
                        return redirect(url_for("ordenes.listar_ordenes"))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "ordenes/form.html",
            orden=orden,
            estados=ORDEN_ESTADOS,
            modo="nuevo",
            **catalogos,
        )
    finally:
        connection.close()


@ordenes_bp.route("/<int:orden_id>/editar", methods=["GET", "POST"])
def editar_orden(orden_id):
    connection = get_db_connection()
    try:
        orden_db = _obtener_orden(connection, orden_id)
        if not orden_db:
            flash("La orden solicitada no existe.", "error")
            return redirect(url_for("ordenes.listar_ordenes"))

        catalogos = _obtener_catalogos(connection, orden_id=orden_id)
        orden = {
            "fecha_programada": (
                orden_db["fecha_programada"].isoformat() if orden_db["fecha_programada"] else ""
            ),
            "id_cliente": str(orden_db["id_cliente"]),
            "id_ruta": str(orden_db["id_ruta"]),
            "id_vehiculo": str(orden_db["id_vehiculo"]),
            "id_conductor": str(orden_db["id_conductor"]),
            "id_tipo_carga": str(orden_db["id_tipo_carga"]),
            "peso_kg": str(orden_db["peso_kg"]),
            "descripcion": orden_db["descripcion"] or "",
            "estado": orden_db["estado"],
            "observaciones": orden_db["observaciones"] or "",
        }

        if request.method == "POST":
            errores, orden = _validar_orden(request.form)
            errores.extend(_validar_disponibilidad_orden(orden, catalogos))
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE ORDEN_SERVICIO
                        SET fecha_programada = %s,
                            id_cliente = %s,
                            id_ruta = %s,
                            id_vehiculo = %s,
                            id_conductor = %s,
                            id_tipo_carga = %s,
                            peso_kg = %s,
                            descripcion = %s,
                            estado = %s,
                            observaciones = %s
                        WHERE id_orden = %s
                        """,
                        (
                            orden["fecha_programada"],
                            orden["id_cliente"],
                            orden["id_ruta"],
                            orden["id_vehiculo"],
                            orden["id_conductor"],
                            orden["id_tipo_carga"],
                            orden["peso_kg"],
                            orden["descripcion"] or None,
                            orden["estado"],
                            orden["observaciones"] or None,
                            orden_id,
                        ),
                    )
                    connection.commit()
                    flash("Orden actualizada correctamente.", "success")
                    return redirect(url_for("ordenes.detalle_orden", orden_id=orden_id))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "ordenes/form.html",
            orden=orden,
            estados=ORDEN_ESTADOS,
            modo="editar",
            orden_id=orden_id,
            numero_orden=orden_db["numero_orden"],
            **catalogos,
        )
    finally:
        connection.close()


@ordenes_bp.post("/<int:orden_id>/eliminar")
def eliminar_orden(orden_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación de la orden antes de continuar.",
    ):
        return redirect(url_for("ordenes.detalle_orden", orden_id=orden_id))

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM ORDEN_SERVICIO WHERE id_orden = %s", (orden_id,))
        if cursor.rowcount == 0:
            connection.rollback()
            flash("La orden solicitada no existe o ya fue eliminada.", "error")
            return redirect(url_for("ordenes.listar_ordenes"))
        connection.commit()
        flash("Orden eliminada correctamente.", "success")
    except Exception as exc:
        connection.rollback()
        if not handle_db_exception(exc):
            raise exc
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("ordenes.listar_ordenes"))
