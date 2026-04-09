from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import (
    handle_db_exception,
    parse_date_field,
    parse_decimal_field,
    parse_int_field,
    parse_text,
    require_confirmation,
    today_iso,
)


mantenimiento_bp = Blueprint("mantenimiento", __name__)

MANTENIMIENTO_TIPOS = ("PREVENTIVO", "CORRECTIVO", "REVISION")
MANTENIMIENTO_ESTADOS = ("EN_PROCESO", "COMPLETADO")


def _mantenimiento_default():
    return {
        "id_vehiculo": "",
        "tipo": "PREVENTIVO",
        "fecha_inicio": today_iso(),
        "fecha_fin": "",
        "descripcion": "",
        "costo": "",
        "taller": "",
        "estado": "EN_PROCESO",
    }


def _obtener_vehiculos(connection):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_vehiculo,
                placa,
                marca,
                modelo,
                estado
            FROM VEHICULO
            ORDER BY placa
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _obtener_mantenimiento(connection, mantenimiento_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                m.id_mantenimiento,
                m.id_vehiculo,
                m.tipo,
                m.fecha_inicio,
                m.fecha_fin,
                m.descripcion,
                m.costo,
                m.taller,
                m.estado,
                v.placa,
                v.marca,
                v.modelo,
                v.estado AS estado_vehiculo
            FROM MANTENIMIENTO m
            INNER JOIN VEHICULO v ON v.id_vehiculo = m.id_vehiculo
            WHERE m.id_mantenimiento = %s
            """,
            (mantenimiento_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _validar_mantenimiento(form):
    errors = []
    id_vehiculo = parse_int_field(form.get("id_vehiculo"), "El vehículo", errors, minimum=1)
    fecha_inicio = parse_date_field(form.get("fecha_inicio"), "La fecha de inicio", errors)
    fecha_fin = parse_date_field(form.get("fecha_fin"), "La fecha de fin", errors, required=False)
    costo = parse_decimal_field(form.get("costo"), "El costo", errors, minimum=Decimal("0")) if parse_text(form.get("costo")) else None
    tipo = parse_text(form.get("tipo"), upper=True)
    estado = parse_text(form.get("estado"), upper=True)

    if tipo not in MANTENIMIENTO_TIPOS:
        errors.append("Debes seleccionar un tipo de mantenimiento válido.")
    if estado not in MANTENIMIENTO_ESTADOS:
        errors.append("Debes seleccionar un estado válido para el mantenimiento.")
    if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
        errors.append("La fecha de fin no puede ser menor que la fecha de inicio.")

    descripcion = parse_text(form.get("descripcion"))
    if not descripcion:
        errors.append("La descripción del mantenimiento es obligatoria.")

    return errors, {
        "id_vehiculo": id_vehiculo if id_vehiculo is not None else parse_text(form.get("id_vehiculo")),
        "tipo": tipo,
        "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else parse_text(form.get("fecha_inicio")),
        "fecha_fin": fecha_fin.isoformat() if fecha_fin else "",
        "descripcion": descripcion,
        "costo": str(costo.quantize(Decimal("0.01"))) if costo is not None else "",
        "taller": parse_text(form.get("taller")),
        "estado": estado,
    }


@mantenimiento_bp.get("/")
def listar_mantenimientos():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                m.id_mantenimiento,
                m.tipo,
                m.fecha_inicio,
                m.fecha_fin,
                m.estado,
                m.costo,
                m.taller,
                v.placa,
                v.marca,
                v.modelo
            FROM MANTENIMIENTO m
            INNER JOIN VEHICULO v ON v.id_vehiculo = m.id_vehiculo
            ORDER BY m.fecha_inicio DESC, m.id_mantenimiento DESC
            """
        )
        mantenimientos = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("mantenimiento/lista.html", mantenimientos=mantenimientos)


@mantenimiento_bp.get("/<int:mantenimiento_id>")
def detalle_mantenimiento(mantenimiento_id):
    connection = get_db_connection()
    try:
        mantenimiento = _obtener_mantenimiento(connection, mantenimiento_id)
        if not mantenimiento:
            flash("El mantenimiento solicitado no existe.", "error")
            return redirect(url_for("mantenimiento.listar_mantenimientos"))

        return render_template(
            "mantenimiento/detalle.html",
            mantenimiento=mantenimiento,
        )
    finally:
        connection.close()


@mantenimiento_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_mantenimiento():
    connection = get_db_connection()
    try:
        vehiculos = _obtener_vehiculos(connection)
        mantenimiento = _mantenimiento_default()

        if request.method == "POST":
            errores, mantenimiento = _validar_mantenimiento(request.form)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO MANTENIMIENTO (
                            id_vehiculo,
                            tipo,
                            fecha_inicio,
                            fecha_fin,
                            descripcion,
                            costo,
                            taller,
                            estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            mantenimiento["id_vehiculo"],
                            mantenimiento["tipo"],
                            mantenimiento["fecha_inicio"],
                            mantenimiento["fecha_fin"] or None,
                            mantenimiento["descripcion"],
                            mantenimiento["costo"] or None,
                            mantenimiento["taller"] or None,
                            mantenimiento["estado"],
                        ),
                    )
                    connection.commit()
                    flash("Mantenimiento registrado correctamente.", "success")
                    return redirect(url_for("mantenimiento.listar_mantenimientos"))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "mantenimiento/form.html",
            mantenimiento=mantenimiento,
            vehiculos=vehiculos,
            tipos=MANTENIMIENTO_TIPOS,
            estados=MANTENIMIENTO_ESTADOS,
            modo="nuevo",
        )
    finally:
        connection.close()


@mantenimiento_bp.route("/<int:mantenimiento_id>/editar", methods=["GET", "POST"])
def editar_mantenimiento(mantenimiento_id):
    connection = get_db_connection()
    try:
        mantenimiento_db = _obtener_mantenimiento(connection, mantenimiento_id)
        if not mantenimiento_db:
            flash("El mantenimiento solicitado no existe.", "error")
            return redirect(url_for("mantenimiento.listar_mantenimientos"))

        vehiculos = _obtener_vehiculos(connection)
        mantenimiento = {
            "id_vehiculo": str(mantenimiento_db["id_vehiculo"]),
            "tipo": mantenimiento_db["tipo"],
            "fecha_inicio": (
                mantenimiento_db["fecha_inicio"].isoformat() if mantenimiento_db["fecha_inicio"] else ""
            ),
            "fecha_fin": (
                mantenimiento_db["fecha_fin"].isoformat() if mantenimiento_db["fecha_fin"] else ""
            ),
            "descripcion": mantenimiento_db["descripcion"],
            "costo": str(mantenimiento_db["costo"]) if mantenimiento_db["costo"] is not None else "",
            "taller": mantenimiento_db["taller"] or "",
            "estado": mantenimiento_db["estado"],
        }

        if request.method == "POST":
            errores, mantenimiento = _validar_mantenimiento(request.form)
            if str(mantenimiento_db["id_vehiculo"]) != str(mantenimiento["id_vehiculo"]):
                errores.append(
                    "No puedes reasignar un mantenimiento a otro vehículo desde edición; crea un registro nuevo si hace falta."
                )
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE MANTENIMIENTO
                        SET id_vehiculo = %s,
                            tipo = %s,
                            fecha_inicio = %s,
                            fecha_fin = %s,
                            descripcion = %s,
                            costo = %s,
                            taller = %s,
                            estado = %s
                        WHERE id_mantenimiento = %s
                        """,
                        (
                            mantenimiento["id_vehiculo"],
                            mantenimiento["tipo"],
                            mantenimiento["fecha_inicio"],
                            mantenimiento["fecha_fin"] or None,
                            mantenimiento["descripcion"],
                            mantenimiento["costo"] or None,
                            mantenimiento["taller"] or None,
                            mantenimiento["estado"],
                            mantenimiento_id,
                        ),
                    )
                    connection.commit()
                    flash("Mantenimiento actualizado correctamente.", "success")
                    return redirect(
                        url_for("mantenimiento.detalle_mantenimiento", mantenimiento_id=mantenimiento_id)
                    )
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "mantenimiento/form.html",
            mantenimiento=mantenimiento,
            vehiculos=vehiculos,
            tipos=MANTENIMIENTO_TIPOS,
            estados=MANTENIMIENTO_ESTADOS,
            modo="editar",
            mantenimiento_id=mantenimiento_id,
        )
    finally:
        connection.close()


@mantenimiento_bp.post("/<int:mantenimiento_id>/eliminar")
def eliminar_mantenimiento(mantenimiento_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación del mantenimiento antes de continuar.",
    ):
        return redirect(
            url_for("mantenimiento.detalle_mantenimiento", mantenimiento_id=mantenimiento_id)
        )

    connection = get_db_connection()
    try:
        mantenimiento = _obtener_mantenimiento(connection, mantenimiento_id)
        if not mantenimiento:
            flash("El mantenimiento solicitado no existe.", "error")
            return redirect(url_for("mantenimiento.listar_mantenimientos"))

        if mantenimiento["estado"] == "EN_PROCESO":
            flash(
                "No se puede eliminar un mantenimiento en proceso. Complétalo primero para que el vehículo recupere su estado operativo.",
                "error",
            )
            return redirect(
                url_for("mantenimiento.detalle_mantenimiento", mantenimiento_id=mantenimiento_id)
            )

        cursor = connection.cursor()
        try:
            cursor.execute(
                "DELETE FROM MANTENIMIENTO WHERE id_mantenimiento = %s",
                (mantenimiento_id,),
            )
            connection.commit()
            flash("Mantenimiento eliminado correctamente.", "success")
        except Exception as exc:
            connection.rollback()
            if not handle_db_exception(exc):
                raise exc
        finally:
            cursor.close()
    finally:
        connection.close()

    return redirect(url_for("mantenimiento.listar_mantenimientos"))
