from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash


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

    if "45000" in message or "1644" in message:
        flash(message, "error")
        return True

    if errno == 1062:
        flash("Ya existe un registro con un valor único duplicado.", "error")
        return True

    if errno in {1451, 1452}:
        flash(
            "La operación no puede completarse porque el registro tiene relaciones activas en la base de datos.",
            "error",
        )
        return True

    return False
