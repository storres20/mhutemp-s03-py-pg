import os
import psycopg

from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL no está definido como variable de entorno"
    )


# =========================================================
# CONEXIÓN
# =========================================================

def get_connection():

    return psycopg.connect(
        DATABASE_URL
    )


# =========================================================
# PRUEBA DE CONEXIÓN
# =========================================================

def test_connection():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                "SELECT 1;"
            )

            cur.fetchone()

    print(
        "✓ PostgreSQL conectado correctamente"
    )


# =========================================================
# CREAR TABLA
# =========================================================

def init_database():

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS measurements (

                    id BIGSERIAL PRIMARY KEY,

                    username VARCHAR(100) NOT NULL,

                    ds_temperature DOUBLE PRECISION,

                    temperature DOUBLE PRECISION,

                    humidity DOUBLE PRECISION,

                    datetime TIMESTAMPTZ,

                    door_status VARCHAR(20),

                    received_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()

                );
                """
            )

            conn.commit()

    print(
        "✓ Tabla measurements lista"
    )


# =========================================================
# INSERTAR MEDICIÓN
# =========================================================

def insert_measurement(data):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO measurements (
                    username,
                    ds_temperature,
                    temperature,
                    humidity,
                    datetime,
                    door_status,
                    received_at
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,

                (
                    data.get("username"),
                    data.get("dsTemperature"),
                    data.get("temperature"),
                    data.get("humidity"),
                    data.get("datetime"),
                    data.get("doorStatus"),
                    data.get("receivedAt")
                )
            )

            conn.commit()


# =========================================================
# OBTENER ÚLTIMAS MEDICIONES
# =========================================================

def get_measurements(
    username=None,
    limit=20
):

    with get_connection() as conn:

        with conn.cursor() as cur:

            if username:

                cur.execute(
                    """
                    SELECT
                        username,
                        ds_temperature,
                        temperature,
                        humidity,
                        datetime,
                        door_status,
                        received_at

                    FROM measurements

                    WHERE username = %s

                    ORDER BY received_at DESC

                    LIMIT %s;
                    """,

                    (
                        username,
                        limit
                    )
                )

            else:

                cur.execute(
                    """
                    SELECT
                        username,
                        ds_temperature,
                        temperature,
                        humidity,
                        datetime,
                        door_status,
                        received_at

                    FROM measurements

                    ORDER BY received_at DESC

                    LIMIT %s;
                    """,

                    (
                        limit,
                    )
                )


            rows = cur.fetchall()


    results = []


    for row in rows:

        results.append(
            {
                "username": row[0],
                "dsTemperature": row[1],
                "temperature": row[2],
                "humidity": row[3],
                "datetime":
                    row[4].isoformat()
                    if row[4]
                    else None,
                "doorStatus": row[5],
                "receivedAt":
                    row[6].isoformat()
                    if row[6]
                    else None
            }
        )


    return results