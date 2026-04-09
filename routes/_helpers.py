import warnings
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash

from config import get_db_engine


def parse_text(value, upper=False):
    cleaned = (value or "").strip()
    return cleaned.upper() if upper else cleaned


def parse_int_field(raw_value, label, errors, minimum=None, maximum=None):
    value = parse_text(raw_value)
    if not value:
        errors.append(f"{label} es obligatorio.")
        return None
    try:
        parsed = int(value)
    except ValueError:
        errors.append(f"{label} debe ser numérico.")
        return None

    if minimum is not None and parsed < minimum:
        errors.append(f"{label} no puede ser menor que {minimum}.")
    if maximum is not None and parsed > maximum:
        errors.append(f"{label} no puede ser mayor que {maximum}.")
    return parsed


def parse_decimal_field(raw_value, label, errors, minimum=None):
    value = parse_text(raw_value)
    if not value:
        errors.append(f"{label} es obligatorio.")
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        errors.append(f"{label} debe ser un número válido.")
        return None

    if minimum is not None and parsed < minimum:
        errors.append(f"{label} no puede ser menor que {minimum}.")
    return parsed


def parse_date_field(raw_value, label, errors, required=True):
    value = parse_text(raw_value)
    if not value:
        if required:
            errors.append(f"{label} es obligatoria.")
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} debe usar el formato YYYY-MM-DD.")
        return None


def today_iso():
    return date.today().isoformat()


def require_confirmation(form, message="Debes confirmar la eliminación antes de continuar."):
    value = parse_text(form.get("confirmar"), upper=True)
    if value in {"SI", "SÍ", "1", "TRUE", "CONFIRMAR"}:
        return True
    flash(message, "error")
    return False


def handle_db_exception(exc):
    message = str(exc)
    errno = getattr(exc, "errno", None)
    pgcode = getattr(exc, "pgcode", None)

    if "45000" in message or "1644" in message or pgcode == "P0001":
        flash(message, "error")
        return True

    if errno == 1062 or pgcode == "23505":
        flash("Ya existe un registro con un valor único duplicado.", "error")
        return True

    if errno in {1451, 1452} or pgcode == "23503":
        flash(
            "La operación no puede completarse porque el registro tiene relaciones activas en la base de datos.",
            "error",
        )
        return True

    return False


def call_sp_crear_orden(cursor, orden):
    params = [
        orden["fecha_programada"],
        orden["id_cliente"],
        orden["id_ruta"],
        orden["id_vehiculo"],
        orden["id_conductor"],
        orden["id_tipo_carga"],
        orden["peso_kg"],
        orden["descripcion"] or None,
    ]

    if get_db_engine() == "postgres":
        cursor.execute(
            """
            SELECT numero_orden, mensaje
            FROM sp_crear_orden(%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params,
        )
        row = cursor.fetchone() or {}
        return row.get("numero_orden"), row.get("mensaje")

    resultado = cursor.callproc("sp_crear_orden", [*params, "", ""])
    if isinstance(resultado, dict):
        return resultado.get("sp_crear_orden_arg9"), resultado.get("sp_crear_orden_arg10")
    return resultado[8], resultado[9]


def fetch_sp_rentabilidad_ruta(cursor, anio, mes):
    if get_db_engine() == "postgres":
        cursor.execute(
            "SELECT * FROM sp_rentabilidad_ruta(%s, %s)",
            (anio, mes),
        )
        return cursor.fetchall()

    cursor.callproc("sp_rentabilidad_ruta", [anio, mes])
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


def call_create_order(cursor, orden):
    return call_sp_crear_orden(cursor, orden)


def fetch_rentabilidad_rows(cursor, anio, mes):
    return fetch_sp_rentabilidad_ruta(cursor, anio, mes)
