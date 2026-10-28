"""Загрузка справочных данных: города, авиакомпании и рейсы на 30 дней от текущей даты.

Загрузка повторяемая: справочники обновляются по ключу, а у рейса детерминированный id
(пара городов, дата, порядковый номер), поэтому повторный запуск не создаёт дублей и только
дозаполняет окно, если наступил новый день.
"""

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import psycopg

CITIES = [
    ("MOW", "Москва", "Россия"),
    ("LED", "Санкт-Петербург", "Россия"),
    ("AER", "Сочи", "Россия"),
    ("KZN", "Казань", "Россия"),
    ("SVX", "Екатеринбург", "Россия"),
    ("OVB", "Новосибирск", "Россия"),
    ("KGD", "Калининград", "Россия"),
]

AIRLINES = [
    ("SU", "Аэрофлот"),
    ("DP", "Победа"),
    ("S7", "S7 Airlines"),
    ("U6", "Уральские авиалинии"),
]

DAYS_AHEAD = 30
# Первый вылет дня — не раньше 05:00 UTC, последний — не позже 20:00 UTC.
FIRST_DEPARTURE_MINUTE = 5 * 60
LAST_DEPARTURE_MINUTE = 20 * 60


@dataclass(frozen=True)
class FlightSeed:
    id: str
    flight_number: str
    airline_code: str
    origin_code: str
    destination_code: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    price_amount: int
    seats_available: int


def flights_for_day(origin: str, destination: str, day: date) -> list[FlightSeed]:
    """Рейсы одного направления на один день.

    Генератор случайных чисел инициализируется направлением и датой: одинаковые входные
    данные всегда дают одинаковые рейсы.
    """
    rng = random.Random(f"{origin}-{destination}-{day.isoformat()}")
    count = rng.randint(2, 3)
    window = (LAST_DEPARTURE_MINUTE - FIRST_DEPARTURE_MINUTE) // count
    # Длительность зависит только от направления: в течение дня у маршрута она одна.
    route_rng = random.Random(f"{origin}-{destination}")
    base_duration = route_rng.randint(80, 260)
    flights = []
    for index in range(count):
        start = FIRST_DEPARTURE_MINUTE + index * window
        minute = start + rng.randrange(0, window - 30, 5)
        departure_at = datetime.combine(day, time(), tzinfo=UTC) + timedelta(minutes=minute)
        duration = base_duration + rng.randrange(0, 21, 5)
        airline_code, _ = rng.choice(AIRLINES)
        flights.append(
            FlightSeed(
                id=f"{origin}{destination}-{day:%Y%m%d}-{index + 1}",
                flight_number=f"{airline_code}{rng.randint(100, 9999)}",
                airline_code=airline_code,
                origin_code=origin,
                destination_code=destination,
                departure_at=departure_at,
                arrival_at=departure_at + timedelta(minutes=duration),
                duration_minutes=duration,
                price_amount=rng.randrange(3000, 8501, 100),
                seats_available=rng.randint(10, 90),
            )
        )
    return flights


def generate_flights(start: date, days: int = DAYS_AHEAD) -> list[FlightSeed]:
    codes = [code for code, _, _ in CITIES]
    flights = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for origin in codes:
            for destination in codes:
                if origin != destination:
                    flights.extend(flights_for_day(origin, destination, day))
    return flights


def seed(conn: psycopg.Connection, today: date | None = None) -> int:
    """Заливает справочники и рейсы; возвращает число рейсов в окне."""
    start = today or datetime.now(UTC).date()
    flights = generate_flights(start)
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO cities (code, name, country, position) VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name, country = EXCLUDED.country, position = EXCLUDED.position
            """,
            [(code, name, country, pos) for pos, (code, name, country) in enumerate(CITIES)],
        )
        cur.executemany(
            """
            INSERT INTO airlines (code, name) VALUES (%s, %s)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            """,
            AIRLINES,
        )
        cur.executemany(
            """
            INSERT INTO flights (
                id, flight_number, airline_code, origin_code, destination_code,
                departure_at, arrival_at, duration_minutes, price_amount, currency, seats_available
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'RUB', %s)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                (
                    f.id,
                    f.flight_number,
                    f.airline_code,
                    f.origin_code,
                    f.destination_code,
                    f.departure_at,
                    f.arrival_at,
                    f.duration_minutes,
                    f.price_amount,
                    f.seats_available,
                )
                for f in flights
            ],
        )
    return len(flights)
