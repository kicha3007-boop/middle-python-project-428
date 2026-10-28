"""Перевод строк базы в формат ответов API (camelCase, время в UTC с Z, числа числами)."""

from datetime import UTC, datetime


def format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def present_city(row: dict, prefix: str = "") -> dict:
    return {
        "code": row[f"{prefix}code"],
        "name": row[f"{prefix}name"],
        "country": row[f"{prefix}country"],
    }


def present_flight(row: dict) -> dict:
    return {
        "id": row["id"],
        "flightNumber": row["flight_number"],
        "airline": {"code": row["airline_code"], "name": row["airline_name"]},
        "origin": present_city(row, "origin_"),
        "destination": present_city(row, "destination_"),
        "departureAt": format_datetime(row["departure_at"]),
        "arrivalAt": format_datetime(row["arrival_at"]),
        "durationMinutes": row["duration_minutes"],
        "price": {"amount": row["price_amount"], "currency": row["currency"]},
        "seatsAvailable": row["seats_available"],
    }


def present_passenger(row: dict) -> dict:
    return {
        "firstName": row["first_name"],
        "lastName": row["last_name"],
        "dateOfBirth": row["date_of_birth"].isoformat(),
        "documentNumber": row["document_number"],
    }


def present_booking(booking: dict, flight: dict, passengers: list[dict]) -> dict:
    return {
        "code": booking["code"],
        "status": booking["status"],
        "flight": present_flight(flight),
        "passengers": [present_passenger(p) for p in passengers],
        "contact": {"email": booking["contact_email"], "phone": booking["contact_phone"]},
        "totalPrice": {"amount": booking["total_amount"], "currency": booking["currency"]},
        "createdAt": format_datetime(booking["created_at"]),
    }
