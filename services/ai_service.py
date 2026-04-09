import json
import os
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

from flask import current_app

from config import get_db_connection


ORDER_STATES = ("PENDIENTE", "EN_TRANSITO", "ENTREGADO", "CANCELADO")
VEHICLE_STATES = ("ACTIVO", "MANTENIMIENTO", "INACTIVO")
INVOICE_STATES = ("PENDIENTE", "PAGADA", "ANULADA")


def _fetch_snapshot():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT estado, COUNT(*) AS total
            FROM ORDEN_SERVICIO
            GROUP BY estado
            """
        )
        order_rows = cursor.fetchall()
        order_counts = {state: 0 for state in ORDER_STATES}
        for row in order_rows:
            order_counts[row["estado"]] = row["total"]

        cursor.execute(
            """
            SELECT estado, COUNT(*) AS total
            FROM VEHICULO
            GROUP BY estado
            """
        )
        vehicle_rows = cursor.fetchall()
        vehicle_counts = {state: 0 for state in VEHICLE_STATES}
        for row in vehicle_rows:
            vehicle_counts[row["estado"]] = row["total"]

        cursor.execute(
            """
            SELECT estado, COUNT(*) AS total_facturas, SUM(total) AS monto
            FROM FACTURA
            GROUP BY estado
            """
        )
        invoice_rows = cursor.fetchall()
        invoice_counts = {
            state: {"total_facturas": 0, "monto": 0.0}
            for state in INVOICE_STATES
        }
        for row in invoice_rows:
            invoice_counts[row["estado"]] = {
                "total_facturas": row["total_facturas"],
                "monto": float(row["monto"] or 0),
            }

        cursor.execute(
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
        route_load = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                v.placa,
                v.marca,
                v.modelo,
                m.tipo,
                m.fecha_inicio,
                m.taller
            FROM MANTENIMIENTO m
            INNER JOIN VEHICULO v ON v.id_vehiculo = m.id_vehiculo
            WHERE m.estado = 'EN_PROCESO'
            ORDER BY m.fecha_inicio ASC
            LIMIT 3
            """
        )
        active_maintenance = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                CONCAT(c.nombre, ' ', c.apellido) AS conductor,
                c.vences_licencia
            FROM CONDUCTOR c
            WHERE c.estado = 'ACTIVO'
            ORDER BY c.vences_licencia ASC
            LIMIT 3
            """
        )
        licence_watch = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    pending_amount = invoice_counts["PENDIENTE"]["monto"]
    paid_amount = invoice_counts["PAGADA"]["monto"]
    cancelled_amount = invoice_counts["ANULADA"]["monto"]

    return {
        "orders": order_counts,
        "vehicles": vehicle_counts,
        "invoices": invoice_counts,
        "routes": route_load,
        "maintenance": active_maintenance,
        "licences": licence_watch,
        "money": {
            "pending": pending_amount,
            "paid": paid_amount,
            "cancelled": cancelled_amount,
            "total_valid": pending_amount + paid_amount,
        },
    }


def _top_route_line(snapshot):
    routes = snapshot["routes"]
    if not routes:
        return "No hay rutas con actividad suficiente para priorizar."

    top_route = routes[0]
    return (
        f"La ruta {top_route['ruta']} concentra {top_route['servicios']} servicios "
        f"y ${top_route['ingresos'] or 0:,.2f} en ingresos válidos."
    )


def _build_health_index(snapshot):
    total_vehicles = max(sum(snapshot["vehicles"].values()), 1)
    pending_orders = snapshot["orders"]["PENDIENTE"]
    active_orders = snapshot["orders"]["EN_TRANSITO"]
    maintenance = snapshot["vehicles"]["MANTENIMIENTO"]
    inactive = snapshot["vehicles"]["INACTIVO"]
    pending_money = snapshot["money"]["pending"]

    score = 100
    score -= min(30, pending_orders * 7)
    score -= min(24, maintenance * 12)
    score -= min(16, inactive * 6)
    if pending_money > 0:
        score -= 10
    if active_orders == 0 and pending_orders > 0:
        score -= 8
    score = max(32, min(score, 99))

    if score >= 84:
        status = "ESTABLE"
        label = "Pulso estable"
    elif score >= 68:
        status = "ATENCION"
        label = "Atención moderada"
    else:
        status = "CRITICO"
        label = "Intervención operativa"

    return {
        "score": score,
        "status": status,
        "status_label": label,
        "maintenance_ratio": round((maintenance / total_vehicles) * 100),
    }


def _build_actions(snapshot):
    actions = []

    if snapshot["orders"]["PENDIENTE"]:
        actions.append(
            f"Despacha {snapshot['orders']['PENDIENTE']} orden(es) pendientes antes de abrir nuevas asignaciones."
        )
    if snapshot["vehicles"]["MANTENIMIENTO"]:
        actions.append(
            f"Coordina salida de taller para {snapshot['vehicles']['MANTENIMIENTO']} vehículo(s) en mantenimiento."
        )
    if snapshot["money"]["pending"] > 0:
        actions.append(
            f"Empuja cobranza por ${snapshot['money']['pending']:,.2f} todavía pendiente."
        )

    if not actions:
        actions.append("La operación está estable; mantén monitoreo sobre órdenes y licencias.")

    return actions[:3]


def _build_local_response(snapshot, question=""):
    normalized = (question or "").strip().lower()
    mode = "general"
    health = _build_health_index(snapshot)

    if any(keyword in normalized for keyword in ("factura", "cobro", "pago", "caja")):
        mode = "facturacion"
    elif any(keyword in normalized for keyword in ("mantenimiento", "taller", "vehiculo", "flota")):
        mode = "flota"
    elif any(keyword in normalized for keyword in ("orden", "ruta", "entrega", "despacho")):
        mode = "operacion"

    if mode == "facturacion":
        title = "Lectura de caja operativa"
        summary = (
            f"Hay ${snapshot['money']['pending']:,.2f} pendientes y "
            f"${snapshot['money']['paid']:,.2f} ya cobrados."
        )
        bullets = [
            f"Facturas pendientes: {snapshot['invoices']['PENDIENTE']['total_facturas']}",
            f"Facturas pagadas: {snapshot['invoices']['PAGADA']['total_facturas']}",
            f"Facturas anuladas fuera de cálculo: {snapshot['invoices']['ANULADA']['total_facturas']}",
        ]
    elif mode == "flota":
        title = "Lectura de flota"
        summary = (
            f"La flota tiene {snapshot['vehicles']['ACTIVO']} unidades activas, "
            f"{snapshot['vehicles']['MANTENIMIENTO']} en taller y "
            f"{snapshot['vehicles']['INACTIVO']} inactivas."
        )
        bullets = [
            _top_route_line(snapshot),
            f"Mantenimientos abiertos: {len(snapshot['maintenance'])}",
            f"Órdenes en tránsito: {snapshot['orders']['EN_TRANSITO']}",
        ]
    else:
        title = "Resumen del turno"
        summary = (
            f"Operación con {snapshot['orders']['EN_TRANSITO']} orden(es) en tránsito, "
            f"{snapshot['orders']['PENDIENTE']} pendiente(s) y "
            f"{snapshot['vehicles']['MANTENIMIENTO']} vehículo(s) fuera de servicio."
        )
        bullets = [
            _top_route_line(snapshot),
            f"Cobranza por resolver: ${snapshot['money']['pending']:,.2f}",
            (
                f"Próxima licencia a vigilar: {snapshot['licences'][0]['conductor']}"
                if snapshot["licences"]
                else "Sin alertas de licencia inmediatas."
            ),
        ]

    maintenance_lines = [
        f"{item['placa']} · {item['tipo'].title()} en {item['taller'] or 'taller no especificado'}"
        for item in snapshot["maintenance"]
    ]
    if maintenance_lines:
        bullets.extend(maintenance_lines[:2])

    return {
        "mode": "local",
        "provider": "Motor local",
        "status": health["status"],
        "status_label": health["status_label"],
        "score": health["score"],
        "title": title,
        "summary": summary,
        "bullets": bullets[:5],
        "actions": _build_actions(snapshot),
        "timestamp": datetime.now().strftime("%H:%M"),
    }


def _build_groq_response(snapshot, question):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    if current_app and current_app.config.get("TESTING"):
        return None

    model = os.getenv("PANALOGIS_AI_MODEL", "llama-3.3-70b-versatile")
    snapshot_text = {
        "orders": snapshot["orders"],
        "vehicles": snapshot["vehicles"],
        "money": snapshot["money"],
        "routes": [
            {
                "ruta": item["ruta"],
                "origen": item["origen"],
                "destino": item["destino"],
                "servicios": item["servicios"],
                "ingresos": float(item["ingresos"] or 0),
            }
            for item in snapshot["routes"]
        ],
        "maintenance": [
            {
                "placa": item["placa"],
                "tipo": item["tipo"],
                "taller": item["taller"],
            }
            for item in snapshot["maintenance"]
        ],
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un analista operativo para una empresa de transporte de carga. "
                    "Responde en español, sin inventar datos, y prioriza decisiones accionables."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Estructura la salida en líneas breves: 1 resumen, hasta 4 hallazgos y hasta 3 acciones.\n"
                    f"Pregunta del operador: {question or 'Dame el resumen del turno.'}\n"
                    f"Snapshot operativo: {snapshot_text}"
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 320,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "python-panalogis/1.0",
        "Accept": "application/json",
    }
    url = "https://api.groq.com/openai/v1/chat/completions"

    try:
        if _USE_REQUESTS:
            resp = _requests.post(url, json=body, headers=headers, timeout=20)
            if not resp.ok:
                return None
            payload = resp.json()
        else:
            request = Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError, Exception):
        return None

    output_text = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not output_text:
        return None

    lines = [line.strip("-• ").strip() for line in output_text.splitlines() if line.strip()]
    health = _build_health_index(snapshot)

    return {
        "mode": "groq",
        "provider": f"Groq · {model}",
        "status": health["status"],
        "status_label": health["status_label"],
        "score": health["score"],
        "title": "Copiloto IA",
        "summary": lines[0],
        "bullets": lines[1:4] or [output_text],
        "actions": (lines[4:7] if len(lines) > 4 else _build_actions(snapshot))[:3],
        "timestamp": datetime.now().strftime("%H:%M"),
    }


def get_copilot_response(question=""):
    snapshot = _fetch_snapshot()
    response = None
    groq_configured = bool(os.getenv("GROQ_API_KEY"))

    if question is not None:
        try:
            response = _build_groq_response(snapshot, question)
        except Exception:
            response = None

    if response is None:
        response = _build_local_response(snapshot, question)
        if groq_configured:
            response["provider"] = "Motor local · fallback Groq"
            response["bullets"] = [
                "Groq no respondió correctamente en este entorno y se activó el análisis local."
            ] + response["bullets"]
            response["bullets"] = response["bullets"][:5]

    response["snapshot"] = snapshot
    return response
