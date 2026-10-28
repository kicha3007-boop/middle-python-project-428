"""Миграции и справочные данные: повторный запуск не ломается и не создаёт дублей."""

from datetime import UTC, datetime, timedelta

from app.db import connect
from app.migrations import migrate
from app.seed import CITIES, DAYS_AHEAD, generate_flights, seed


def test_generated_flights_follow_data_rules() -> None:
    start = datetime.now(UTC).date()
    flights = generate_flights(start)
    pairs = len(CITIES) * (len(CITIES) - 1)
    per_day: dict[tuple[str, str, object], int] = {}
    for flight in flights:
        assert flight.origin_code != flight.destination_code
        assert 80 <= flight.duration_minutes <= 280
        assert 3000 <= flight.price_amount <= 8500
        assert 10 <= flight.seats_available <= 90
        assert flight.arrival_at - flight.departure_at == timedelta(minutes=flight.duration_minutes)
        assert flight.flight_number.startswith(flight.airline_code)
        key = (flight.origin_code, flight.destination_code, flight.departure_at.date())
        per_day[key] = per_day.get(key, 0) + 1
    assert len(per_day) == pairs * DAYS_AHEAD
    assert set(per_day.values()) <= {2, 3}
    assert min(day for _, _, day in per_day) == start


def test_generation_is_deterministic() -> None:
    start = datetime.now(UTC).date()
    assert generate_flights(start, days=2) == generate_flights(start, days=2)


def test_migrate_and_seed_are_repeatable(database_url: str) -> None:
    with connect(database_url) as conn:
        before = conn.execute("SELECT count(*) AS n FROM flights").fetchone()["n"]
        assert migrate(conn) == []
        seed(conn)
        after = conn.execute("SELECT count(*) AS n FROM flights").fetchone()["n"]
        cities = conn.execute("SELECT count(*) AS n FROM cities").fetchone()["n"]
    assert after == before
    assert cities == len(CITIES)
