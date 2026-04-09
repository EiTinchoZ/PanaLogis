from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import (
    handle_db_exception,
    parse_decimal_field,
    parse_int_field,
    parse_text,
    require_confirmation,
)


vehiculos_bp = Blueprint("vehiculos", __name__)

VEHICULO_ESTADOS = ("ACTIVO", "MANTENIMIENTO", "INACTIVO")


def _vehiculo_default():
    return {
        "placa": "",
        "marca": "",
        "modelo": "",
        "anio": date.today().year,
        "id_tipo_vehiculo": "",
        "estado": "ACTIVO",
        "kilometraje": "0.00",
    }


def _obtener_tipos_vehiculo(connection):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT id_tipo_vehiculo, descripcion, capacidad_ton
            FROM TIPO_VEHICULO
            ORDER BY descripcion
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _obtener_vehiculo(connection, vehiculo_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                v.id_vehiculo,
                v.placa,
                v.marca,
                v.modelo,
                v.anio,
                v.id_tipo_vehiculo,
                v.estado,
                v.kilometraje,
                tv.descripcion AS tipo_vehiculo,
                tv.capacidad_ton
            FROM VEHICULO v
            INNER JOIN TIPO_VEHICULO tv
                ON tv.id_tipo_vehiculo = v.id_tipo_vehiculo
            WHERE v.id_vehiculo = %s
            """,
            (vehiculo_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _obtener_mantenimientos(connection, vehiculo_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_mantenimiento,
                tipo,
                fecha_inicio,
                fecha_fin,
                estado,
                taller,
                costo,
                descripcion
            FROM MANTENIMIENTO
            WHERE id_vehiculo = %s
            ORDER BY fecha_inicio DESC, id_mantenimiento DESC
            LIMIT 10
            """,
            (vehiculo_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _tiene_mantenimiento_en_proceso(connection, vehiculo_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM MANTENIMIENTO
            WHERE id_vehiculo = %s
              AND estado = 'EN_PROCESO'
            """,
            (vehiculo_id,),
        )
        row = cursor.fetchone()
        return bool(row and row["total"])
    finally:
        cursor.close()


def _validar_vehiculo(form, tipos_vehiculo):
    errors = []
    tipos_validos = {str(tipo["id_tipo_vehiculo"]) for tipo in tipos_vehiculo}

    anio = parse_int_field(
        form.get("anio"),
        "El año del vehículo",
        errors,
        minimum=1980,
        maximum=date.today().year + 1,
    )
    kilometraje = parse_decimal_field(
        form.get("kilometraje"),
        "El kilometraje",
        errors,
        minimum=Decimal("0"),
    )
    estado = parse_text(form.get("estado"), upper=True)

    if estado not in VEHICULO_ESTADOS:
        errors.append("Debes seleccionar un estado válido para el vehículo.")

    id_tipo_vehiculo = parse_text(form.get("id_tipo_vehiculo"))
    if id_tipo_vehiculo not in tipos_validos:
        errors.append("Debes seleccionar un tipo de vehículo válido.")

    data = {
        "placa": parse_text(form.get("placa"), upper=True),
        "marca": parse_text(form.get("marca")),
        "modelo": parse_text(form.get("modelo")),
        "anio": anio if anio is not None else parse_text(form.get("anio")),
        "id_tipo_vehiculo": id_tipo_vehiculo,
        "estado": estado or "ACTIVO",
        "kilometraje": (
            str(kilometraje.quantize(Decimal("0.01")))
            if kilometraje is not None
            else parse_text(form.get("kilometraje"))
        ),
    }

    if not data["placa"]:
        errors.append("La placa es obligatoria.")
    if not data["marca"]:
        errors.append("La marca es obligatoria.")
    if not data["modelo"]:
        errors.append("El modelo es obligatorio.")

    return errors, data


@vehiculos_bp.get("/")
def listar_vehiculos():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                v.id_vehiculo,
                v.placa,
                v.marca,
                v.modelo,
                v.anio,
                v.estado,
                v.kilometraje,
                tv.descripcion AS tipo_vehiculo,
                tv.capacidad_ton
            FROM VEHICULO v
            INNER JOIN TIPO_VEHICULO tv
                ON tv.id_tipo_vehiculo = v.id_tipo_vehiculo
            ORDER BY v.estado, v.placa
            """
        )
        vehiculos = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("vehiculos/lista.html", vehiculos=vehiculos)


@vehiculos_bp.get("/<int:vehiculo_id>")
def detalle_vehiculo(vehiculo_id):
    connection = get_db_connection()
    try:
        vehiculo = _obtener_vehiculo(connection, vehiculo_id)
        if not vehiculo:
            flash("El vehículo solicitado no existe.", "error")
            return redirect(url_for("vehiculos.listar_vehiculos"))

        mantenimientos = _obtener_mantenimientos(connection, vehiculo_id)
        return render_template(
            "vehiculos/detalle.html",
            vehiculo=vehiculo,
            mantenimientos=mantenimientos,
        )
    finally:
        connection.close()


@vehiculos_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_vehiculo():
    connection = get_db_connection()
    try:
        tipos_vehiculo = _obtener_tipos_vehiculo(connection)
        vehiculo = _vehiculo_default()

        if request.method == "POST":
            errores, vehiculo = _validar_vehiculo(request.form, tipos_vehiculo)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO VEHICULO (
                            placa,
                            marca,
                            modelo,
                            anio,
                            id_tipo_vehiculo,
                            estado,
                            kilometraje
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            vehiculo["placa"],
                            vehiculo["marca"],
                            vehiculo["modelo"],
                            vehiculo["anio"],
                            vehiculo["id_tipo_vehiculo"],
                            vehiculo["estado"],
                            vehiculo["kilometraje"],
                        ),
                    )
                    connection.commit()
                    flash("Vehículo registrado correctamente.", "success")
                    return redirect(url_for("vehiculos.listar_vehiculos"))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "vehiculos/form.html",
            vehiculo=vehiculo,
            tipos_vehiculo=tipos_vehiculo,
            estados=VEHICULO_ESTADOS,
            modo="nuevo",
        )
    finally:
        connection.close()


@vehiculos_bp.route("/<int:vehiculo_id>/editar", methods=["GET", "POST"])
def editar_vehiculo(vehiculo_id):
    connection = get_db_connection()
    try:
        vehiculo_db = _obtener_vehiculo(connection, vehiculo_id)
        if not vehiculo_db:
            flash("El vehículo solicitado no existe.", "error")
            return redirect(url_for("vehiculos.listar_vehiculos"))

        tipos_vehiculo = _obtener_tipos_vehiculo(connection)
        vehiculo = {
            "placa": vehiculo_db["placa"],
            "marca": vehiculo_db["marca"],
            "modelo": vehiculo_db["modelo"],
            "anio": vehiculo_db["anio"],
            "id_tipo_vehiculo": str(vehiculo_db["id_tipo_vehiculo"]),
            "estado": vehiculo_db["estado"],
            "kilometraje": str(vehiculo_db["kilometraje"]),
        }

        if request.method == "POST":
            errores, vehiculo = _validar_vehiculo(request.form, tipos_vehiculo)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE VEHICULO
                        SET placa = %s,
                            marca = %s,
                            modelo = %s,
                            anio = %s,
                            id_tipo_vehiculo = %s,
                            estado = %s,
                            kilometraje = %s
                        WHERE id_vehiculo = %s
                        """,
                        (
                            vehiculo["placa"],
                            vehiculo["marca"],
                            vehiculo["modelo"],
                            vehiculo["anio"],
                            vehiculo["id_tipo_vehiculo"],
                            vehiculo["estado"],
                            vehiculo["kilometraje"],
                            vehiculo_id,
                        ),
                    )
                    connection.commit()
                    flash("Vehículo actualizado correctamente.", "success")
                    return redirect(url_for("vehiculos.detalle_vehiculo", vehiculo_id=vehiculo_id))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "vehiculos/form.html",
            vehiculo=vehiculo,
            tipos_vehiculo=tipos_vehiculo,
            estados=VEHICULO_ESTADOS,
            modo="editar",
            vehiculo_id=vehiculo_id,
        )
    finally:
        connection.close()


@vehiculos_bp.post("/<int:vehiculo_id>/eliminar")
def eliminar_vehiculo(vehiculo_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación del vehículo antes de continuar.",
    ):
        return redirect(url_for("vehiculos.detalle_vehiculo", vehiculo_id=vehiculo_id))

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM VEHICULO WHERE id_vehiculo = %s", (vehiculo_id,))
        if cursor.rowcount == 0:
            flash("El vehículo solicitado no existe o ya fue eliminado.", "error")
            return redirect(url_for("vehiculos.listar_vehiculos"))
        connection.commit()
        flash("Vehículo eliminado correctamente.", "success")
    except Exception as exc:
        connection.rollback()
        if not handle_db_exception(exc):
            raise exc
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("vehiculos.listar_vehiculos"))
