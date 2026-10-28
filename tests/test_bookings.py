"""Оформление, просмотр и отмена брони."""

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.conftest import passenger

CODE = re.compile(r"^[A-Z0-9]{6}$")
CONTACT = {"email": "ivan@example.com", "phone": "+79991234567"}


def test_create_booking_with_one_passenger(make_booking: Callable[..., dict], flight: dict) -> None:
    booking = make_booking(passenger(documentNumber="1"))
    assert CODE.match(booking["code"])
    assert booking["status"] == "confirmed"
    assert booking["flight"] == flight
    assert booking["contact"] == CONTACT
    assert booking["passengers"] == [passenger(documentNumber="1")]
    assert booking["totalPrice"] == flight["price"]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", booking["createdAt"])


def test_total_price_is_multiplied_by_passengers(
    make_booking: Callable[..., dict], flight: dict
) -> None:
    booking = make_booking(passenger("Петров"), passenger("Сидорова", firstName="Анна"))
    assert len(booking["passengers"]) == 2
    assert booking["totalPrice"] == {
        "amount": flight["price"]["amount"] * 2,
        "currency": "RUB",
    }


def test_booking_codes_are_unique(make_booking: Callable[..., dict]) -> None:
    codes = {make_booking()["code"] for _ in range(5)}
    assert len(codes) == 5


def test_client_total_price_is_ignored(client: TestClient, flight: dict) -> None:
    payload = {
        "flightId": flight["id"],
        "contact": CONTACT,
        "passengers": [passenger()],
        "totalPrice": {"amount": 1, "currency": "RUB"},
    }
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 201
    assert response.json()["totalPrice"]["amount"] == flight["price"]["amount"]


@pytest.mark.parametrize(
    ("description", "change"),
    [
        ("пустой список пассажиров", lambda p: p.update(passengers=[])),
        ("нет пассажиров", lambda p: p.pop("passengers")),
        ("нет контакта", lambda p: p.pop("contact")),
        ("пустой email", lambda p: p["contact"].update(email="")),
        ("пустой телефон из пробелов", lambda p: p["contact"].update(phone="   ")),
        ("пустая фамилия", lambda p: p["passengers"][0].update(lastName="")),
        ("нет номера документа", lambda p: p["passengers"][0].pop("documentNumber")),
        ("дата рождения не дата", lambda p: p["passengers"][0].update(dateOfBirth="вчера")),
        ("неизвестный рейс", lambda p: p.update(flightId="NOPE")),
        ("пустой flightId", lambda p: p.update(flightId="")),
    ],
)
def test_invalid_booking_is_validation_error(
    client: TestClient, flight: dict, description: str, change: Callable[[dict], None]
) -> None:
    payload = {"flightId": flight["id"], "contact": dict(CONTACT), "passengers": [passenger()]}
    change(payload)
    response = client.post("/api/bookings", json=payload)
    assert response.status_code == 400, description
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"]


def test_malformed_json_is_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/bookings", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_booking_is_found_by_code_and_last_name(
    client: TestClient, make_booking: Callable[..., dict]
) -> None:
    booking = make_booking(passenger("Петров"), passenger("Сидорова"))
    response = client.get(f"/api/bookings/{booking['code']}", params={"lastName": "Сидорова"})
    assert response.status_code == 200
    assert response.json() == booking


def test_last_name_comparison_ignores_case_and_spaces(
    client: TestClient, make_booking: Callable[..., dict]
) -> None:
    booking = make_booking(passenger("Петров"))
    response = client.get(f"/api/bookings/{booking['code']}", params={"lastName": "  пЕТРОВ "})
    assert response.status_code == 200
    assert response.json()["code"] == booking["code"]


def test_booking_code_is_case_insensitive(
    client: TestClient, make_booking: Callable[..., dict]
) -> None:
    booking = make_booking(passenger("Петров"))
    response = client.get(f"/api/bookings/{booking['code'].lower()}", params={"lastName": "Петров"})
    assert response.status_code == 200


def test_lookup_failures_give_identical_404(
    client: TestClient, make_booking: Callable[..., dict]
) -> None:
    booking = make_booking(passenger("Петров"))
    responses = [
        client.get("/api/bookings/ZZZZZZ", params={"lastName": "Петров"}),
        client.get(f"/api/bookings/{booking['code']}", params={"lastName": "Иванов"}),
        client.get(f"/api/bookings/{booking['code']}"),
        client.get(f"/api/bookings/{booking['code']}", params={"lastName": ""}),
    ]
    for response in responses:
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
    assert len({response.text for response in responses}) == 1


def test_cancel_returns_cancelled_booking(
    client: TestClient, make_booking: Callable[..., dict]
) -> None:
    booking = make_booking(passenger("Петров"))
    response = client.post(f"/api/bookings/{booking['code']}/cancel", json={"lastName": "петров"})
    assert response.status_code == 200
    cancelled = response.json()
    assert cancelled["status"] == "cancelled"
    assert cancelled["code"] == booking["code"]
    assert cancelled["passengers"] == booking["passengers"]

    # Бронь не удалена: она находится и после отмены, уже со статусом cancelled.
    found = client.get(f"/api/bookings/{booking['code']}", params={"lastName": "Петров"})
    assert found.status_code == 200
    assert found.json()["status"] == "cancelled"


def test_repeated_cancel_is_ok(client: TestClient, make_booking: Callable[..., dict]) -> None:
    booking = make_booking(passenger("Петров"))
    url = f"/api/bookings/{booking['code']}/cancel"
    assert client.post(url, json={"lastName": "Петров"}).status_code == 200
    response = client.post(url, json={"lastName": "Петров"})
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_failures_give_404(client: TestClient, make_booking: Callable[..., dict]) -> None:
    booking = make_booking(passenger("Петров"))
    url = f"/api/bookings/{booking['code']}/cancel"
    responses = [
        client.post(url, json={"lastName": "Иванов"}),
        client.post(url, json={}),
        client.post(url),
        client.post("/api/bookings/ZZZZZZ/cancel", json={"lastName": "Петров"}),
    ]
    for response in responses:
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    still_confirmed = client.get(url.removesuffix("/cancel"), params={"lastName": "Петров"})
    assert still_confirmed.json()["status"] == "confirmed"
