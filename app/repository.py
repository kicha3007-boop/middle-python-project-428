"""Слой работы с базой: все SQL-запросы приложения собраны здесь.

Значения передаются только параметрами (%s), строки запросов не склеиваются со входными данными.
Функции возвращают строки базы как словари; в формат API их переводит app.presenter.
"""

from datetime import UTC, date, datetime, time, timedelta

import psycopg

FLIGHT_SELECT = """
    SELECT
        f.id,
        f.flight_number,
        f.departure_at,
        f.arrival_at,
        f.duration_minutes,
        f.price_amount,
        f.currency,
        f.seats_available,
        a.code AS airline_code,
        a.name AS airline_name,
        o.code AS origin_code,
        o.name AS origin_name,
        o.country AS origin_country,
        d.code AS destination_code,
        d.name AS destination_name,
        d.country AS destination_country
    FROM flights f
    JOIN airlines a ON a.code = f.airline_code
    JOIN cities o ON o.code = f.origin_code
    JOIN cities d ON d.code = f.destination_code
"""


def list_cities(conn: psycopg.Connection) -> list[dict]:
    return conn.execute("SELECT code, name, country FROM cities ORDER BY position").fetchall()


def search_flights(
    conn: psycopg.Connection, origin: str, destination: str, day: date, passengers: int
) -> list[dict]:
    # День вылета считается в UTC — в том же поясе, в котором отдаётся departureAt.
    day_start = datetime.combine(day, time(), tzinfo=UTC)
    return conn.execute(
        FLIGHT_SELECT
        + """
        WHERE f.origin_code = %s
          AND f.destination_code = %s
          AND f.departure_at >= %s
          AND f.departure_at < %s
          AND f.seats_available >= %s
        ORDER BY f.departure_at, f.id
        """,
        (origin, destination, day_start, day_start + timedelta(days=1), passengers),
    ).fetchall()


def find_flight(conn: psycopg.Connection, flight_id: str) -> dict | None:
    return conn.execute(FLIGHT_SELECT + " WHERE f.id = %s", (flight_id,)).fetchone()


def insert_booking(
    conn: psycopg.Connection,
    *,
    code: str,
    flight_id: str,
    email: str,
    phone: str,
    total_amount: int,
    currency: str,
) -> int:
    row = conn.execute(
        """
        INSERT INTO bookings (code, flight_id, contact_email, contact_phone, total_amount, currency)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (code, flight_id, email, phone, total_amount, currency),
    ).fetchone()
    return row["id"]


def insert_passengers(conn: psycopg.Connection, booking_id: int, passengers: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO booking_passengers (
                booking_id, position, first_name, last_name, last_name_key,
                date_of_birth, document_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    booking_id,
                    position,
                    p["first_name"],
                    p["last_name"],
                    p["last_name_key"],
                    p["date_of_birth"],
                    p["document_number"],
                )
                for position, p in enumerate(passengers)
            ],
        )


def find_booking_id(conn: psycopg.Connection, code: str, last_name_key: str) -> int | None:
    """Бронь находится, только если совпали код и фамилия любого её пассажира."""
    row = conn.execute(
        """
        SELECT b.id
        FROM bookings b
        WHERE b.code = %s
          AND EXISTS (
              SELECT 1 FROM booking_passengers p
              WHERE p.booking_id = b.id AND p.last_name_key = %s
          )
        """,
        (code, last_name_key),
    ).fetchone()
    return row["id"] if row else None


def get_booking(conn: psycopg.Connection, booking_id: int) -> dict:
    return conn.execute(
        """
        SELECT id, code, status, flight_id, contact_email, contact_phone,
               total_amount, currency, created_at
        FROM bookings
        WHERE id = %s
        """,
        (booking_id,),
    ).fetchone()


def list_passengers(conn: psycopg.Connection, booking_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT first_name, last_name, date_of_birth, document_number
        FROM booking_passengers
        WHERE booking_id = %s
        ORDER BY position
        """,
        (booking_id,),
    ).fetchall()


def cancel_booking(conn: psycopg.Connection, booking_id: int) -> None:
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
