"""Сценарии API поверх слоя базы: поиск рейсов, оформление, просмотр и отмена брони."""

from datetime import date

import psycopg
from psycopg import errors as pg_errors

from app import repository
from app.booking_code import generate_booking_code, normalize_booking_code
from app.errors import NotFoundError, ValidationError
from app.presenter import present_booking, present_city, present_flight
from app.schemas import CreateBookingIn

BOOKING_NOT_FOUND = "Бронь не найдена: проверьте код и фамилию"
CODE_ATTEMPTS = 10


def normalize_last_name(last_name: str) -> str:
    return last_name.strip().casefold()


def list_cities(conn: psycopg.Connection) -> list[dict]:
    return [present_city(row) for row in repository.list_cities(conn)]


def search_flights(
    conn: psycopg.Connection, origin: str, destination: str, day: date, passengers: int
) -> list[dict]:
    rows = repository.search_flights(conn, origin.upper(), destination.upper(), day, passengers)
    return [present_flight(row) for row in rows]


def get_flight(conn: psycopg.Connection, flight_id: str) -> dict:
    row = repository.find_flight(conn, flight_id)
    if row is None:
        raise NotFoundError("Рейс не найден")
    return present_flight(row)


def load_booking(conn: psycopg.Connection, booking_id: int) -> dict:
    booking = repository.get_booking(conn, booking_id)
    flight = repository.find_flight(conn, booking["flight_id"])
    passengers = repository.list_passengers(conn, booking_id)
    return present_booking(booking, flight, passengers)


def create_booking(conn: psycopg.Connection, payload: CreateBookingIn) -> dict:
    flight = repository.find_flight(conn, payload.flight_id)
    if flight is None:
        raise ValidationError("Рейс с таким flightId не найден")

    # Стоимость считает сервер: цена рейса за одного пассажира × число пассажиров.
    total_amount = flight["price_amount"] * len(payload.passengers)
    passengers = [
        {
            "first_name": p.first_name,
            "last_name": p.last_name,
            "last_name_key": normalize_last_name(p.last_name),
            "date_of_birth": p.date_of_birth,
            "document_number": p.document_number,
        }
        for p in payload.passengers
    ]

    for _ in range(CODE_ATTEMPTS):
        try:
            # Бронь и пассажиры — одна транзакция (точка сохранения внутри транзакции запроса):
            # при совпадении кода откатывается только эта попытка, и вставка повторяется.
            with conn.transaction():
                booking_id = repository.insert_booking(
                    conn,
                    code=generate_booking_code(),
                    flight_id=flight["id"],
                    email=payload.contact.email,
                    phone=payload.contact.phone,
                    total_amount=total_amount,
                    currency=flight["currency"],
                )
                repository.insert_passengers(conn, booking_id, passengers)
        except pg_errors.UniqueViolation:
            continue
        return load_booking(conn, booking_id)

    raise RuntimeError("Не удалось подобрать уникальный код брони")


def find_booking_id(conn: psycopg.Connection, code: str, last_name: str | None) -> int:
    # Неверный код, неверная и отсутствующая фамилия дают один и тот же ответ.
    if not last_name or not last_name.strip():
        raise NotFoundError(BOOKING_NOT_FOUND)
    booking_id = repository.find_booking_id(
        conn, normalize_booking_code(code), normalize_last_name(last_name)
    )
    if booking_id is None:
        raise NotFoundError(BOOKING_NOT_FOUND)
    return booking_id


def get_booking(conn: psycopg.Connection, code: str, last_name: str | None) -> dict:
    return load_booking(conn, find_booking_id(conn, code, last_name))


def cancel_booking(conn: psycopg.Connection, code: str, last_name: str | None) -> dict:
    booking_id = find_booking_id(conn, code, last_name)
    # Бронь не удаляется — меняется статус. Повторная отмена снова даёт cancelled.
    repository.cancel_booking(conn, booking_id)
    return load_booking(conn, booking_id)
