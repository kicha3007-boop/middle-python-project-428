"""Справочник городов, поиск рейсов и рейс по идентификатору."""

import re

from fastapi.testclient import TestClient

from tests.conftest import iso_date

ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EXPECTED_CITIES = ["MOW", "LED", "AER", "KZN", "SVX", "OVB", "KGD"]


def test_cities_list_with_moscow_and_petersburg_first(client: TestClient) -> None:
    response = client.get("/api/cities")
    assert response.status_code == 200
    cities = response.json()
    assert [city["code"] for city in cities] == EXPECTED_CITIES
    assert cities[0] == {"code": "MOW", "name": "Москва", "country": "Россия"}
    assert cities[1]["name"] == "Санкт-Петербург"


def test_search_returns_flights_in_contract_format(client: TestClient) -> None:
    date = iso_date(2)
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": date, "passengers": 2},
    )
    assert response.status_code == 200
    flights = response.json()
    assert 2 <= len(flights) <= 3
    for flight in flights:
        assert flight["origin"]["code"] == "MOW"
        assert flight["destination"] == {
            "code": "LED",
            "name": "Санкт-Петербург",
            "country": "Россия",
        }
        assert flight["departureAt"].startswith(date)
        assert ISO_UTC.match(flight["departureAt"])
        assert ISO_UTC.match(flight["arrivalAt"])
        assert isinstance(flight["price"]["amount"], int)
        assert flight["price"]["currency"] == "RUB"
        assert 3000 <= flight["price"]["amount"] <= 8500
        assert 80 <= flight["durationMinutes"] <= 280
        assert flight["seatsAvailable"] >= 2
        assert re.match(r"^[A-Z0-9]{2}\d+$", flight["flightNumber"])
        assert flight["airline"]["code"] in {"SU", "DP", "S7", "U6"}


def test_search_has_flights_for_today(client: TestClient) -> None:
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "LED", "date": iso_date(0)}
    )
    assert response.status_code == 200
    assert response.json()


def test_search_filters_by_free_seats(client: TestClient) -> None:
    response = client.get(
        "/api/flights",
        params={"origin": "MOW", "destination": "LED", "date": iso_date(3), "passengers": 91},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_same_city_returns_empty_list(client: TestClient) -> None:
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "MOW", "date": iso_date(3)}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_outside_data_window_returns_empty_list(client: TestClient) -> None:
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "LED", "date": iso_date(60)}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_without_date_is_validation_error(client: TestClient) -> None:
    response = client.get("/api/flights", params={"origin": "MOW", "destination": "LED"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert "date" in body["message"]


def test_search_with_malformed_params_is_validation_error(client: TestClient) -> None:
    bad_params = [
        {"origin": "MOW", "destination": "LED", "date": "завтра"},
        {"origin": "MOW", "destination": "LED", "date": iso_date(1), "passengers": "два"},
        {"origin": "MOW", "destination": "LED", "date": iso_date(1), "passengers": 0},
        {"origin": "", "destination": "LED", "date": iso_date(1)},
    ]
    for params in bad_params:
        response = client.get("/api/flights", params=params)
        assert response.status_code == 400, params
        assert response.json()["code"] == "validation_error"


def test_get_flight_by_id_matches_search_result(client: TestClient, flight: dict) -> None:
    response = client.get(f"/api/flights/{flight['id']}")
    assert response.status_code == 200
    assert response.json() == flight


def test_get_unknown_flight_is_not_found(client: TestClient) -> None:
    response = client.get("/api/flights/NOPE")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
