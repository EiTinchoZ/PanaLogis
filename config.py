import os

try:
    import mysql.connector
except ImportError:  # pragma: no cover - optional in postgres-only deploys
    mysql = None

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - optional in mysql-only local setups
    psycopg2 = None
    RealDictCursor = None


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "panalogis-dev-secret-key")
    DB_URL = (
        os.getenv("PANALOGIS_DB_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL", "")
    )
    DB_ENGINE = (
        os.getenv("PANALOGIS_DB_ENGINE")
        or ("postgres" if DB_URL else "mysql")
    ).lower()
    DB_HOST = os.getenv("PANALOGIS_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("PANALOGIS_DB_PORT", "3306"))
    DB_USER = os.getenv("PANALOGIS_DB_USER", "root")
    DB_PASSWORD = os.getenv("PANALOGIS_DB_PASSWORD", "")
    DB_NAME = os.getenv("PANALOGIS_DB_NAME", "panalogis_db")
    DB_SSLMODE = os.getenv(
        "PANALOGIS_DB_SSLMODE",
        "require" if DB_ENGINE == "postgres" else "preferred",
    )
    AI_MODEL = os.getenv("PANALOGIS_AI_MODEL", "llama-3.3-70b-versatile")
    DEBUG = True


class DictionaryConnection:
    """Proxy that defaults cursors to dictionary mode."""

    def __init__(self, connection, engine):
        self._connection = connection
        self.engine = engine

    def cursor(self, *args, **kwargs):
        if self.engine == "postgres":
            kwargs.setdefault("cursor_factory", RealDictCursor)
        else:
            kwargs.setdefault("dictionary", True)
        return self._connection.cursor(*args, **kwargs)

    def is_connected(self):
        if self.engine == "postgres":
            return getattr(self._connection, "closed", 1) == 0
        return self._connection.is_connected()

    def __getattr__(self, item):
        return getattr(self._connection, item)


def get_db_engine():
    return "postgres" if Config.DB_ENGINE in {"postgres", "postgresql", "supabase"} else "mysql"


def get_db_connection():
    if get_db_engine() == "postgres":
        if psycopg2 is None:
            raise ConnectionError(
                "Falta psycopg2-binary para conectar PanaLogis a PostgreSQL/Supabase."
            )
        try:
            if Config.DB_URL:
                connection = psycopg2.connect(Config.DB_URL, sslmode=Config.DB_SSLMODE)
            else:
                connection = psycopg2.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    dbname=Config.DB_NAME,
                    sslmode=Config.DB_SSLMODE,
                )
        except psycopg2.Error as exc:
            raise ConnectionError(
                "No se pudo conectar a PostgreSQL/Supabase. Verifica la URL o credenciales cloud de PanaLogis."
            ) from exc

        if connection.closed:
            raise ConnectionError(
                "No se pudo establecer una conexion activa con PostgreSQL/Supabase."
            )

        return DictionaryConnection(connection, "postgres")

    if mysql is None:
        raise ConnectionError(
            "Falta mysql-connector-python para conectar PanaLogis a MariaDB."
        )

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

    return DictionaryConnection(connection, "mysql")
