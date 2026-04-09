from flask import Blueprint, flash, redirect, render_template, request, url_for

from config import get_db_connection
from routes._helpers import handle_db_exception, parse_text, require_confirmation


clientes_bp = Blueprint("clientes", __name__)

CLIENTE_ESTADOS = ("ACTIVO", "INACTIVO")


def _cliente_default():
    return {
        "ruc": "",
        "razon_social": "",
        "contacto_nombre": "",
        "contacto_tel": "",
        "contacto_email": "",
        "direccion": "",
        "estado": "ACTIVO",
    }


def _obtener_cliente(connection, cliente_id):
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id_cliente,
                ruc,
                razon_social,
                contacto_nombre,
                contacto_tel,
                contacto_email,
                direccion,
                estado
            FROM CLIENTE
            WHERE id_cliente = %s
            """,
            (cliente_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()


def _obtener_historial_cliente(connection, cliente_id):
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
                IFNULL(f.total, 0) AS total_facturado
            FROM ORDEN_SERVICIO o
            INNER JOIN RUTA r ON r.id_ruta = o.id_ruta
            LEFT JOIN FACTURA f ON f.id_orden = o.id_orden
            WHERE o.id_cliente = %s
            ORDER BY o.fecha_programada DESC, o.id_orden DESC
            LIMIT 10
            """,
            (cliente_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def _validar_cliente(form):
    errors = []
    estado = parse_text(form.get("estado"), upper=True)
    if estado not in CLIENTE_ESTADOS:
        errors.append("Debes seleccionar un estado válido para el cliente.")

    data = {
        "ruc": parse_text(form.get("ruc")),
        "razon_social": parse_text(form.get("razon_social")),
        "contacto_nombre": parse_text(form.get("contacto_nombre")),
        "contacto_tel": parse_text(form.get("contacto_tel")),
        "contacto_email": parse_text(form.get("contacto_email")),
        "direccion": parse_text(form.get("direccion")),
        "estado": estado or "ACTIVO",
    }

    if not data["ruc"]:
        errors.append("El RUC es obligatorio.")
    if not data["razon_social"]:
        errors.append("La razón social es obligatoria.")

    return errors, data


@clientes_bp.get("/")
def listar_clientes():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                c.id_cliente,
                c.ruc,
                c.razon_social,
                c.contacto_nombre,
                c.contacto_tel,
                c.contacto_email,
                c.estado,
                COUNT(o.id_orden) AS total_ordenes
            FROM CLIENTE c
            LEFT JOIN ORDEN_SERVICIO o ON o.id_cliente = c.id_cliente
            GROUP BY
                c.id_cliente,
                c.ruc,
                c.razon_social,
                c.contacto_nombre,
                c.contacto_tel,
                c.contacto_email,
                c.estado
            ORDER BY c.razon_social
            """
        )
        clientes = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    return render_template("clientes/lista.html", clientes=clientes)


@clientes_bp.get("/<int:cliente_id>")
def detalle_cliente(cliente_id):
    connection = get_db_connection()
    try:
        cliente = _obtener_cliente(connection, cliente_id)
        if not cliente:
            flash("El cliente solicitado no existe.", "error")
            return redirect(url_for("clientes.listar_clientes"))

        historial = _obtener_historial_cliente(connection, cliente_id)
        return render_template(
            "clientes/detalle.html",
            cliente=cliente,
            historial=historial,
        )
    finally:
        connection.close()


@clientes_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo_cliente():
    connection = get_db_connection()
    try:
        cliente = _cliente_default()
        if request.method == "POST":
            errores, cliente = _validar_cliente(request.form)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO CLIENTE (
                            ruc,
                            razon_social,
                            contacto_nombre,
                            contacto_tel,
                            contacto_email,
                            direccion,
                            estado
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            cliente["ruc"],
                            cliente["razon_social"],
                            cliente["contacto_nombre"] or None,
                            cliente["contacto_tel"] or None,
                            cliente["contacto_email"] or None,
                            cliente["direccion"] or None,
                            cliente["estado"],
                        ),
                    )
                    connection.commit()
                    flash("Cliente registrado correctamente.", "success")
                    return redirect(url_for("clientes.listar_clientes"))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "clientes/form.html",
            cliente=cliente,
            estados=CLIENTE_ESTADOS,
            modo="nuevo",
        )
    finally:
        connection.close()


@clientes_bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    connection = get_db_connection()
    try:
        cliente_db = _obtener_cliente(connection, cliente_id)
        if not cliente_db:
            flash("El cliente solicitado no existe.", "error")
            return redirect(url_for("clientes.listar_clientes"))

        cliente = {
            "ruc": cliente_db["ruc"],
            "razon_social": cliente_db["razon_social"],
            "contacto_nombre": cliente_db["contacto_nombre"] or "",
            "contacto_tel": cliente_db["contacto_tel"] or "",
            "contacto_email": cliente_db["contacto_email"] or "",
            "direccion": cliente_db["direccion"] or "",
            "estado": cliente_db["estado"],
        }

        if request.method == "POST":
            errores, cliente = _validar_cliente(request.form)
            if errores:
                for error in errores:
                    flash(error, "error")
            else:
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        UPDATE CLIENTE
                        SET ruc = %s,
                            razon_social = %s,
                            contacto_nombre = %s,
                            contacto_tel = %s,
                            contacto_email = %s,
                            direccion = %s,
                            estado = %s
                        WHERE id_cliente = %s
                        """,
                        (
                            cliente["ruc"],
                            cliente["razon_social"],
                            cliente["contacto_nombre"] or None,
                            cliente["contacto_tel"] or None,
                            cliente["contacto_email"] or None,
                            cliente["direccion"] or None,
                            cliente["estado"],
                            cliente_id,
                        ),
                    )
                    connection.commit()
                    flash("Cliente actualizado correctamente.", "success")
                    return redirect(url_for("clientes.detalle_cliente", cliente_id=cliente_id))
                except Exception as exc:
                    connection.rollback()
                    if not handle_db_exception(exc):
                        raise exc
                finally:
                    cursor.close()

        return render_template(
            "clientes/form.html",
            cliente=cliente,
            estados=CLIENTE_ESTADOS,
            modo="editar",
            cliente_id=cliente_id,
        )
    finally:
        connection.close()


@clientes_bp.post("/<int:cliente_id>/eliminar")
def eliminar_cliente(cliente_id):
    if not require_confirmation(
        request.form,
        message="Confirma la eliminación del cliente antes de continuar.",
    ):
        return redirect(url_for("clientes.detalle_cliente", cliente_id=cliente_id))

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM CLIENTE WHERE id_cliente = %s", (cliente_id,))
        if cursor.rowcount == 0:
            flash("El cliente solicitado no existe o ya fue eliminado.", "error")
            return redirect(url_for("clientes.listar_clientes"))
        connection.commit()
        flash("Cliente eliminado correctamente.", "success")
    except Exception as exc:
        connection.rollback()
        if not handle_db_exception(exc):
            raise exc
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("clientes.listar_clientes"))
