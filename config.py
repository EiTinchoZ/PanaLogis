import os

import mysql.connector


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "panalogis-dev-secret-key")
    DB_HOST = os.getenv("PANALOGIS_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("PANALOGIS_DB_PORT", "3306"))
    DB_USER = os.getenv("PANALOGIS_DB_USER", "root")
    DB_PASSWORD = os.getenv("PANALOGIS_DB_PASSWORD", "")
    DB_NAME = os.getenv("PANALOGIS_DB_NAME", "panalogis_db")
    AI_MODEL = os.getenv("PANALOGIS_AI_MODEL", "llama-3.3-70b-versatile")
    DEBUG = True


class DictionaryConnection:
    """Proxy that defaults cursors to dictionary mode."""

    def __init__(self, connection):
        self._connection = connection

    def cursor(self, *args, **kwargs):
        kwargs.setdefault("dictionary", True)
        return self._connection.cursor(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._connection, item)


def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            use_unicode=True,
        )
    except mysql.connector.Error as exc:
        raise ConnectionError(
            "No se pudo conectar a MariaDB. Verifica XAMPP y las credenciales de PanaLogis."
        ) from exc

    if not connection.is_connected():
        raise ConnectionError("No se pudo establecer una conexion activa con MariaDB.")

    return DictionaryConnection(connection)
