"""Общие фикстуры: база с миграциями и данными, клиент поверх приложения целиком.

Тестам нужна PostgreSQL по DATABASE_URL. Каждый тест готовит свои данные сам: дату поиска
считает от сегодняшнего дня, рейс берёт из ответа поиска, бронь для просмотра создаёт свою.
"""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app
from app.migrations import migrate
from app.seed import seed

INDEX_HTML = "<!doctype html><html><body><div id='root'></div></body></html>"
ASSET_JS = "console.log('asset');"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail("Для тестов нужна PostgreSQL: задайте DATABASE_URL (см. README)")
    with connect(url) as conn:
        migrate(conn)
        seed(conn)
    return url


@pytest.fixture(scope="session")
def public_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Подменный каталог статики: тесты не зависят от того, выполнялся ли make build."""
    root = tmp_path_factory.mktemp("public")
    (root / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "app.js").write_text(ASSET_JS, encoding="utf-8")
    # Файл рядом с каталогом статики: выход вверх по директориям не должен его отдавать.
    (root.parent / "secret.txt").write_text("secret", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def client(database_url: str, public_dir: Path) -> Iterator[TestClient]:
    with TestClient(create_app(public_dir=public_dir)) as test_client:
        yield test_client


def iso_date(days_from_today: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days_from_today)).isoformat()


@pytest.fixture
def flight(client: TestClient) -> dict:
    response = client.get(
        "/api/flights", params={"origin": "MOW", "destination": "LED", "date": iso_date(3)}
    )
    assert response.status_code == 200
    flights = response.json()
    assert flights, "в окне данных нет рейсов MOW → LED"
    return flights[0]


def passenger(last_name: str = "Петров", **overrides: str) -> dict:
    return {
        "firstName": "Иван",
        "lastName": last_name,
        "dateOfBirth": "1990-05-20",
        "documentNumber": "4509 123456",
        **overrides,
    }


@pytest.fixture
def make_booking(client: TestClient, flight: dict) -> Callable[..., dict]:
    def create(*passengers: dict) -> dict:
        payload = {
            "flightId": flight["id"],
            "contact": {"email": "ivan@example.com", "phone": "+79991234567"},
            "passengers": list(passengers) or [passenger()],
        }
        response = client.post("/api/bookings", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create
