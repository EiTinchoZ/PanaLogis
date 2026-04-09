import os
import shutil
import subprocess
import sys
import time
import unittest
import warnings
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app


SQL_FILE = ROOT / "database" / "panalogis.sql"
XAMPP_MYSQL_EXE = Path(r"C:\xampp\mysql\bin\mysql.exe")
XAMPP_MYSQL_START = Path(r"C:\xampp\mysql_start.bat")


def _resolve_mysql_exe():
    configured = os.getenv("PANALOGIS_MYSQL_EXE")
    if configured:
        candidate = Path(configured)
        if candidate.exists():
            return candidate

    which = shutil.which("mysql")
    if which:
        return Path(which)

    if XAMPP_MYSQL_EXE.exists():
        return XAMPP_MYSQL_EXE

    raise FileNotFoundError("No se encontro mysql.exe en PATH ni en C:\\xampp\\mysql\\bin.")


MYSQL_EXE = _resolve_mysql_exe()


def ensure_mariadb_running():
    try:
        conn = mysql.connector.connect(host="127.0.0.1", user="root", password="")
        conn.close()
        return
    except mysql.connector.Error:
        pass

    if XAMPP_MYSQL_START.exists():
        subprocess.run(
            ["cmd", "/c", str(XAMPP_MYSQL_START)],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        time.sleep(3)

    conn = mysql.connector.connect(host="127.0.0.1", user="root", password="")
    conn.close()


def reset_database():
    ensure_mariadb_running()
    with SQL_FILE.open("rb") as sql_file:
        subprocess.run(
            [str(MYSQL_EXE), "--default-character-set=utf8mb4", "-u", "root"],
            stdin=sql_file,
            cwd=str(ROOT),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )


def db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="panalogis_db",
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        use_unicode=True,
    )


class RuntimeSmokeTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        reset_database()
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.initial_orders = self.fetch_one("SELECT COUNT(*) AS total FROM ORDEN_SERVICIO")["total"]
        self.initial_facturas = self.fetch_one("SELECT COUNT(*) AS total FROM FACTURA")["total"]
        self.initial_mantenimientos = self.fetch_one("SELECT COUNT(*) AS total FROM MANTENIMIENTO")["total"]

    def fetch_one(self, query, params=()):
        conn = db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(query, params)
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()

    def fetch_all(self, query, params=()):
        conn = db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    def fetch_rentabilidad(self, anio=2026, mes=4):
        conn = db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.callproc("sp_rentabilidad_ruta", [anio, mes])
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                result_sets = list(cur.stored_results())
            for result in result_sets:
                rows = result.fetchall()
                if rows:
                    return rows
            return []
        finally:
            cur.close()
            conn.close()

    def first_available_resources(self):
        vehiculo = self.fetch_one(
            """
            SELECT v.id_vehiculo
            FROM VEHICULO v
            WHERE v.estado = 'ACTIVO'
              AND NOT EXISTS (
                SELECT 1
                FROM ORDEN_SERVICIO o
                WHERE o.id_vehiculo = v.id_vehiculo
                  AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
              )
            ORDER BY v.id_vehiculo
            LIMIT 1
            """
        )
        conductor = self.fetch_one(
            """
            SELECT c.id_conductor
            FROM CONDUCTOR c
            WHERE c.estado = 'ACTIVO'
              AND NOT EXISTS (
                SELECT 1
                FROM ORDEN_SERVICIO o
                WHERE o.id_conductor = c.id_conductor
                  AND o.estado IN ('PENDIENTE', 'EN_TRANSITO')
              )
            ORDER BY c.id_conductor
            LIMIT 1
            """
        )
        self.assertIsNotNone(vehiculo)
        self.assertIsNotNone(conductor)
        return vehiculo["id_vehiculo"], conductor["id_conductor"]

    def create_order(
        self,
        vehiculo_id=None,
        conductor_id=None,
        fecha_programada="2026-04-17",
        id_cliente="1",
        id_ruta="1",
        id_tipo_carga="1",
        peso_kg="450.00",
        descripcion="alta verificada por smoke test",
        observaciones="observacion persistida por smoke test",
    ):
        if vehiculo_id is None or conductor_id is None:
            vehiculo_id, conductor_id = self.first_available_resources()

        response = self.client.post(
            "/ordenes/nuevo",
            data={
                "fecha_programada": fecha_programada,
                "id_cliente": id_cliente,
                "id_ruta": id_ruta,
                "id_vehiculo": str(vehiculo_id),
                "id_conductor": str(conductor_id),
                "id_tipo_carga": id_tipo_carga,
                "peso_kg": peso_kg,
                "descripcion": descripcion,
                "estado": "PENDIENTE",
                "observaciones": observaciones,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/ordenes/")
        order = self.fetch_one(
            """
            SELECT id_orden, numero_orden, id_vehiculo, id_conductor, observaciones, estado
            FROM ORDEN_SERVICIO
            ORDER BY id_orden DESC
            LIMIT 1
            """
        )
        self.assertIsNotNone(order)
        return order

    def test_01_get_routes_render(self):
        for path in (
            "/dashboard",
            "/vehiculos/",
            "/conductores/",
            "/clientes/",
            "/ordenes/",
            "/mantenimiento/",
            "/facturas/",
            "/reportes/",
            "/vehiculos/nuevo",
            "/conductores/nuevo",
            "/clientes/nuevo",
            "/ordenes/nuevo",
            "/mantenimiento/nuevo",
            "/vehiculos/1",
            "/vehiculos/1/editar",
            "/conductores/1",
            "/conductores/1/editar",
            "/clientes/1",
            "/clientes/1/editar",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, path)

    def test_02_create_order_persists_observations(self):
        order = self.create_order()
        self.assertTrue(order["numero_orden"].startswith("ORD-2026-"))
        self.assertEqual(order["estado"], "PENDIENTE")
        self.assertEqual(order["observaciones"], "observacion persistida por smoke test")
        total = self.fetch_one("SELECT COUNT(*) AS total FROM ORDEN_SERVICIO")
        self.assertEqual(total["total"], self.initial_orders + 1)

    def test_03_order_to_entregado_generates_factura(self):
        order = self.create_order()
        response = self.client.post(
            f"/ordenes/{order['id_orden']}/editar",
            data={
                "fecha_programada": "2026-04-17",
                "id_cliente": "1",
                "id_ruta": "1",
                "id_vehiculo": str(order["id_vehiculo"]),
                "id_conductor": str(order["id_conductor"]),
                "id_tipo_carga": "1",
                "peso_kg": "450.00",
                "descripcion": "alta verificada por smoke test",
                "estado": "ENTREGADO",
                "observaciones": "orden entregada por smoke test",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), f"/ordenes/{order['id_orden']}")

        order_db = self.fetch_one(
            "SELECT estado, observaciones FROM ORDEN_SERVICIO WHERE id_orden = %s",
            (order["id_orden"],),
        )
        factura = self.fetch_one(
            "SELECT numero_factura, estado, total FROM FACTURA WHERE id_orden = %s",
            (order["id_orden"],),
        )

        self.assertEqual(order_db["estado"], "ENTREGADO")
        self.assertEqual(order_db["observaciones"], "orden entregada por smoke test")
        self.assertIsNotNone(factura)
        self.assertTrue(factura["numero_factura"].startswith("FAC-2026-"))
        self.assertEqual(factura["estado"], "PENDIENTE")
        self.assertGreater(float(factura["total"]), 0)
        total_facturas = self.fetch_one("SELECT COUNT(*) AS total FROM FACTURA")
        self.assertEqual(total_facturas["total"], self.initial_facturas + 1)

    def test_04_factura_can_be_marked_paid(self):
        order = self.create_order()
        self.client.post(
            f"/ordenes/{order['id_orden']}/editar",
            data={
                "fecha_programada": "2026-04-17",
                "id_cliente": "1",
                "id_ruta": "1",
                "id_vehiculo": str(order["id_vehiculo"]),
                "id_conductor": str(order["id_conductor"]),
                "id_tipo_carga": "1",
                "peso_kg": "450.00",
                "descripcion": "alta verificada por smoke test",
                "estado": "ENTREGADO",
                "observaciones": "orden entregada por smoke test",
            },
            follow_redirects=False,
        )
        factura = self.fetch_one("SELECT id_factura FROM FACTURA WHERE id_orden = %s", (order["id_orden"],))
        self.assertIsNotNone(factura)

        response = self.client.post(
            f"/facturas/{factura['id_factura']}/editar",
            data={"estado": "PAGADA", "fecha_pago": "2026-04-18"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), f"/facturas/{factura['id_factura']}")

        factura_db = self.fetch_one(
            "SELECT estado, fecha_pago FROM FACTURA WHERE id_factura = %s",
            (factura["id_factura"],),
        )
        self.assertEqual(factura_db["estado"], "PAGADA")
        self.assertEqual(str(factura_db["fecha_pago"]), "2026-04-18")

    def test_05_maintenance_triggers_vehicle_state(self):
        response = self.client.post(
            "/mantenimiento/nuevo",
            data={
                "id_vehiculo": "5",
                "tipo": "PREVENTIVO",
                "fecha_inicio": "2026-04-08",
                "fecha_fin": "",
                "descripcion": "mantenimiento smoke test",
                "costo": "125.50",
                "taller": "Taller Central",
                "estado": "EN_PROCESO",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/mantenimiento/")

        mant = self.fetch_one(
            """
            SELECT id_mantenimiento, estado, fecha_fin
            FROM MANTENIMIENTO
            ORDER BY id_mantenimiento DESC
            LIMIT 1
            """
        )
        vehiculo = self.fetch_one("SELECT estado FROM VEHICULO WHERE id_vehiculo = 5")
        self.assertEqual(mant["estado"], "EN_PROCESO")
        self.assertEqual(vehiculo["estado"], "MANTENIMIENTO")

        response = self.client.post(
            f"/mantenimiento/{mant['id_mantenimiento']}/editar",
            data={
                "id_vehiculo": "5",
                "tipo": "PREVENTIVO",
                "fecha_inicio": "2026-04-08",
                "fecha_fin": "2026-04-09",
                "descripcion": "mantenimiento smoke test",
                "costo": "125.50",
                "taller": "Taller Central",
                "estado": "COMPLETADO",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), f"/mantenimiento/{mant['id_mantenimiento']}")

        mant_db = self.fetch_one(
            "SELECT estado, fecha_fin FROM MANTENIMIENTO WHERE id_mantenimiento = %s",
            (mant["id_mantenimiento"],),
        )
        vehiculo_db = self.fetch_one("SELECT estado FROM VEHICULO WHERE id_vehiculo = 5")
        self.assertEqual(mant_db["estado"], "COMPLETADO")
        self.assertEqual(str(mant_db["fecha_fin"]), "2026-04-09")
        self.assertEqual(vehiculo_db["estado"], "ACTIVO")
        total_mant = self.fetch_one("SELECT COUNT(*) AS total FROM MANTENIMIENTO")
        self.assertEqual(total_mant["total"], self.initial_mantenimientos + 1)

    def test_06_delete_guards_hold(self):
        order = self.create_order()

        response = self.client.post(
            "/mantenimiento/nuevo",
            data={
                "id_vehiculo": "5",
                "tipo": "PREVENTIVO",
                "fecha_inicio": "2026-04-08",
                "fecha_fin": "",
                "descripcion": "mantenimiento smoke test",
                "costo": "125.50",
                "taller": "Taller Central",
                "estado": "EN_PROCESO",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Mantenimiento registrado correctamente.".encode("utf-8"),
            response.data,
        )
        mant = self.fetch_one("SELECT id_mantenimiento FROM MANTENIMIENTO ORDER BY id_mantenimiento DESC LIMIT 1")

        response = self.client.post(
            f"/mantenimiento/{mant['id_mantenimiento']}/eliminar",
            data={"confirmar": "1"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No se puede eliminar un mantenimiento en proceso".encode("utf-8"),
            response.data,
        )
        mant_db = self.fetch_one(
            "SELECT id_mantenimiento FROM MANTENIMIENTO WHERE id_mantenimiento = %s",
            (mant["id_mantenimiento"],),
        )
        self.assertIsNotNone(mant_db)

        self.client.post(
            f"/ordenes/{order['id_orden']}/editar",
            data={
                "fecha_programada": "2026-04-17",
                "id_cliente": "1",
                "id_ruta": "1",
                "id_vehiculo": str(order["id_vehiculo"]),
                "id_conductor": str(order["id_conductor"]),
                "id_tipo_carga": "1",
                "peso_kg": "450.00",
                "descripcion": "alta verificada por smoke test",
                "estado": "ENTREGADO",
                "observaciones": "orden entregada por smoke test",
            },
            follow_redirects=False,
        )
        response = self.client.post(
            f"/ordenes/{order['id_orden']}/eliminar",
            data={"confirmar": "1"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("relaciones activas en la base de datos".encode("utf-8"), response.data)
        order_db = self.fetch_one(
            "SELECT id_orden FROM ORDEN_SERVICIO WHERE id_orden = %s",
            (order["id_orden"],),
        )
        self.assertIsNotNone(order_db)

    def test_07_reportes_render(self):
        order = self.create_order()
        self.client.post(
            f"/ordenes/{order['id_orden']}/editar",
            data={
                "fecha_programada": "2026-04-17",
                "id_cliente": "1",
                "id_ruta": "1",
                "id_vehiculo": "1",
                "id_conductor": "1",
                "id_tipo_carga": "1",
                "peso_kg": "450.00",
                "descripcion": "alta verificada por smoke test",
                "estado": "ENTREGADO",
                "observaciones": "orden entregada por smoke test",
            },
            follow_redirects=False,
        )
        response = self.client.get("/reportes/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rentabilidad por ruta".encode("utf-8"), response.data)
        self.assertIn("Consolidado de facturación mensual".encode("utf-8"), response.data)

    def test_08_order_rejects_unavailable_resources_server_side(self):
        vehiculo_id, conductor_id = self.first_available_resources()
        self.create_order(vehiculo_id=vehiculo_id, conductor_id=conductor_id)

        response = self.client.post(
            "/ordenes/nuevo",
            data={
                "fecha_programada": "2026-04-18",
                "id_cliente": "1",
                "id_ruta": "1",
                "id_vehiculo": str(vehiculo_id),
                "id_conductor": str(conductor_id),
                "id_tipo_carga": "1",
                "peso_kg": "300.00",
                "descripcion": "intento duplicado sobre recursos ocupados",
                "estado": "PENDIENTE",
                "observaciones": "debe fallar por disponibilidad",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("El vehículo seleccionado no está disponible.".encode("utf-8"), response.data)
        self.assertIn("El conductor seleccionado no está disponible.".encode("utf-8"), response.data)

        total = self.fetch_one("SELECT COUNT(*) AS total FROM ORDEN_SERVICIO")
        self.assertEqual(total["total"], self.initial_orders + 1)

    def test_09_delete_nonexistent_order_shows_error(self):
        response = self.client.post(
            "/ordenes/9999/eliminar",
            data={"confirmar": "1"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("La orden solicitada no existe o ya fue eliminada.".encode("utf-8"), response.data)

    def test_10_annulled_invoice_is_excluded_from_financial_reports(self):
        order = self.create_order(
            fecha_programada="2026-11-17",
            id_ruta="3",
            id_tipo_carga="3",
            descripcion="orden de noviembre para validar anulación",
            observaciones="se anulará la factura en prueba",
        )
        self.client.post(
            f"/ordenes/{order['id_orden']}/editar",
            data={
                "fecha_programada": "2026-11-17",
                "id_cliente": "1",
                "id_ruta": "3",
                "id_vehiculo": str(order["id_vehiculo"]),
                "id_conductor": str(order["id_conductor"]),
                "id_tipo_carga": "3",
                "peso_kg": "450.00",
                "descripcion": "orden de noviembre para validar anulación",
                "estado": "ENTREGADO",
                "observaciones": "orden anulada en prueba",
            },
            follow_redirects=False,
        )
        factura = self.fetch_one("SELECT id_factura FROM FACTURA WHERE id_orden = %s", (order["id_orden"],))
        self.assertIsNotNone(factura)

        response = self.client.post(
            f"/facturas/{factura['id_factura']}/editar",
            data={"estado": "ANULADA", "fecha_pago": ""},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        rentabilidad = self.fetch_rentabilidad(2026, 11)
        consolidado = self.fetch_one(
            """
            SELECT
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN 1 ELSE 0 END) AS total_facturas,
                SUM(CASE WHEN f.estado <> 'ANULADA' THEN f.total ELSE 0 END) AS ingresos_totales
            FROM FACTURA f
            WHERE f.id_factura = %s
            """,
            (factura["id_factura"],),
        )

        self.assertEqual(rentabilidad, [])
        self.assertEqual(consolidado["total_facturas"], 0)
        self.assertEqual(float(consolidado["ingresos_totales"] or 0), 0.0)

    def test_11_editing_maintenance_cannot_change_vehicle(self):
        response = self.client.post(
            "/mantenimiento/nuevo",
            data={
                "id_vehiculo": "5",
                "tipo": "PREVENTIVO",
                "fecha_inicio": "2026-04-08",
                "fecha_fin": "",
                "descripcion": "mantenimiento smoke test",
                "costo": "125.50",
                "taller": "Taller Central",
                "estado": "EN_PROCESO",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

        mant = self.fetch_one(
            "SELECT id_mantenimiento, id_vehiculo FROM MANTENIMIENTO ORDER BY id_mantenimiento DESC LIMIT 1"
        )
        self.assertEqual(mant["id_vehiculo"], 5)

        response = self.client.post(
            f"/mantenimiento/{mant['id_mantenimiento']}/editar",
            data={
                "id_vehiculo": "7",
                "tipo": "PREVENTIVO",
                "fecha_inicio": "2026-04-08",
                "fecha_fin": "",
                "descripcion": "mantenimiento smoke test",
                "costo": "125.50",
                "taller": "Taller Central",
                "estado": "EN_PROCESO",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No puedes reasignar un mantenimiento a otro vehículo desde edición".encode("utf-8"),
            response.data,
        )

        mant_db = self.fetch_one(
            "SELECT id_vehiculo FROM MANTENIMIENTO WHERE id_mantenimiento = %s",
            (mant["id_mantenimiento"],),
        )
        self.assertEqual(mant_db["id_vehiculo"], 5)

    def test_12_ai_briefing_endpoint_returns_operational_payload(self):
        response = self.client.get("/api/ai/briefing")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn(payload["mode"], {"local", "groq"})
        self.assertTrue(payload["provider"])
        self.assertTrue(payload["summary"])
        self.assertIsInstance(payload["bullets"], list)
        self.assertIsInstance(payload["actions"], list)

        ask_response = self.client.post(
            "/api/ai/ask",
            json={"question": "Resume la facturación actual."},
        )
        self.assertEqual(ask_response.status_code, 200)
        ask_payload = ask_response.get_json()
        self.assertTrue(ask_payload["summary"])
        self.assertIn("snapshot", ask_payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
