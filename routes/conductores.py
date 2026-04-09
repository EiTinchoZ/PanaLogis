from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import handle_db_exception, parse_date_field, parse_text, require_confirmation


conductores_bp = Blueprint("conductores", __name__)

CONDUCTOR_ESTADOS = ("ACTIVO", "INACTIVO", "SUSPENDIDO")


def _conductor_default():
    return {
        "cedula": "",
        "nombre": "",
        "apellido": "",
        "telefono": "",
        "email": "",
        "licencia": "",
        "categoria_licencia": "",
        "vences_licencia": "",
        "estado": "ACTIVO",
    }


def _obtener_conductor(connection, conductor_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_conductor,
                cedula,
                nombre,
                apellido,
                telefono,
                email,
                licencia,
                categoria_licencia,
                vences_licencia,
                estado
            FROM CONDUCTOR
            WHERE id_conductor = %s
            """,
            (conductor_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _obtener_ordenes_conductor(connection, conductor_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                o.id_orden,
                o.numero_orden,
                o.fecha_programada,
                o.estado,
                r.nombre AS ruta,
                c.razon_social AS cliente
            FROM ORDEN_SERVICIO o
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            INNER JOIN CLIENTE c ON c.id_cliente = o.id_cliente
            WHERE o.id_conductor = %s
            ORDER BY o.fecha_programada DESC, o.id_orden DESC
            LIMIT 10
            """,
            (conductor_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _validar_conductor(form):
    errors = []
    vences_licencia = parse_date_field(
        form.get("vences_licencia"),
        "La fecha de vencimiento de la licencia",
        errors,
    )
    estado = parse_text(form.get("estado"), upper=True)
    if estado not in CONDUCTOR_ESTADOS:
        errors.append("Debes seleccionar un estado válido para el conductor.")

    data = {
        "cedula": parse_text(form.get("cedula")),
        "nombre": parse_text(form.get("nombre")),
        "apellido": parse_text(form.get("apellido")),
        "telefono": parse_text(form.get("telefono")),
        "email": parse_text(form.get("email")),
        "licencia": parse_text(form.get("licencia"), upper=True),
        "categoria_licencia": parse_text(form.get("categoria_licencia"), upper=True),
        "vences_licencia": vences_licencia.isoformat() if vences_licencia else parse_text(form.get("vences_licencia")),
        "estado": estado or "ACTIVO",
    }

    for field, label in (
        ("cedula", "La cédula"),
        ("nombre", "El nombre"),
        ("apellido", "El apellido"),
        ("licencia", "La licencia"),
        ("categoria_licencia", "La categoría de licencia"),
    ):
        if not data[field]:
            errors.append(f"{label} es obligatoria.")

    return errors, data


@conductores_bp.get("/")
def listar_conductores():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                c.id_conductor,
                c.cedula,
                c.nombre,
                c.apellido,
                c.telefono,
                c.licencia,
                c.categoria_licencia,
                c.vences_licencia,
                c.estado,
                (
                    SELECT COUNT(*)
                    FROM ORDEN_SERVICIO o
                    WHERE o.id_conductor = c.id_conductor
                      AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
                ) AS ordenes_activas
            FROM CONDUCTOR c
            ORDER BY c.nombre, c.apellido
            """
        )
        conductores = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("conductores/lista.html", conductores=conductores)


@conductores_bp.get("/<int:conductor_id>")
def detalle_conductor(conductor_id):
    connection = get_db_connection()
    try:
        conductor = _obtener_conductor(connection, conductor_id)
        if not conductor:
            flash("El conductor solicitado no existe.", "error")
            return redirect(url_for("conductores.listar_conductores"))

        ordenes = _obtener_ordenes_conductor(connection, conductor_id)
        return render_template(
            "conductores/detalle.html",
            conductor=conductor,
            ordenes=ordenes,
        )
    finally:
        connection.close()


@conductores_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_conductor():
    connection = get_db_connection()
    try:
        conductor = _conductor_default()
        if request.method == "POST":
            errores, conductor = _validar_conductor(request.form)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO CONDUCTOR (
                            cedula,
                            nombre,
                            apellido,
                            telefono,
                            email,
                            licencia,
                            categoria_licencia,
                            vences_licencia,
                            estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            conductor["cedula"],
                            conductor["nombre"],
                            conductor["apellido"],
                            conductor["telefono"] or None,
                            conductor["email"] or None,
                            conductor["licencia"],
                            conductor["categoria_licencia"],
                            conductor["vences_licencia"],
                            conductor["estado"],
                        ),
                    )
                    connection.commit()
                    flash("Conductor registrado correctamente.", "success")
                    return redirect(url_for("conductores.listar_conductores"))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "conductores/form.html",
            conductor=conductor,
            estados=CONDUCTOR_ESTADOS,
            modo="nuevo",
        )
    finally:
        connection.close()


@conductores_bp.route("/<int:conductor_id>/editar", methods=["GET", "POST"])
def editar_conductor(conductor_id):
    connection = get_db_connection()
    try:
        conductor_db = _obtener_conductor(connection, conductor_id)
        if not conductor_db:
            flash("El conductor solicitado no existe.", "error")
            return redirect(url_for("conductores.listar_conductores"))

        conductor = {
            "cedula": conductor_db["cedula"],
            "nombre": conductor_db["nombre"],
            "apellido": conductor_db["apellido"],
            "telefono": conductor_db["telefono"] or "",
            "email": conductor_db["email"] or "",
            "licencia": conductor_db["licencia"],
            "categoria_licencia": conductor_db["categoria_licencia"],
            "vences_licencia": (
                conductor_db["vences_licencia"].isoformat()
                if conductor_db["vences_licencia"]
                else ""
            ),
            "estado": conductor_db["estado"],
        }

        if request.method == "POST":
            errores, conductor = _validar_conductor(request.form)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE CONDUCTOR
                        SET cedula = %s,
                            nombre = %s,
                            apellido = %s,
                            telefono = %s,
                            email = %s,
                            licencia = %s,
                            categoria_licencia = %s,
                            vences_licencia = %s,
                            estado = %s
                        WHERE id_conductor = %s
                        """,
                        (
                            conductor["cedula"],
                            conductor["nombre"],
                            conductor["apellido"],
                            conductor["telefono"] or None,
                            conductor["email"] or None,
                            conductor["licencia"],
                            conductor["categoria_licencia"],
                            conductor["vences_licencia"],
                            conductor["estado"],
                            conductor_id,
                        ),
                    )
                    connection.commit()
                    flash("Conductor actualizado correctamente.", "success")
                    return redirect(url_for("conductores.detalle_conductor", conductor_id=conductor_id))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "conductores/form.html",
            conductor=conductor,
            estados=CONDUCTOR_ESTADOS,
            modo="editar",
            conductor_id=conductor_id,
        )
    finally:
        connection.close()


@conductores_bp.post("/<int:conductor_id>/eliminar")
def eliminar_conductor(conductor_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación del conductor antes de continuar.",
    ):
        return redirect(url_for("conductores.detalle_conductor", conductor_id=conductor_id))

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM CONDUCTOR WHERE id_conductor = %s", (conductor_id,))
        if cursor.rowcount == 0:
            flash("El conductor solicitado no existe o ya fue eliminado.", "error")
            return redirect(url_for("conductores.listar_conductores"))
        connection.commit()
        flash("Conductor eliminado correctamente.", "success")
    except Exception as exc:
        connection.rollback()
        if not handle_db_exception(exc):
            raise exc
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("conductores.listar_conductores"))
