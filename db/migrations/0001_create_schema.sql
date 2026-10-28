-- Справочники: города и авиакомпании.
-- position задаёт порядок городов в /api/cities: Москва и Санкт-Петербург должны идти первыми.
CREATE TABLE cities (
    code text PRIMARY KEY CHECK (code ~ '^[A-Z]{3}$'),
    name text NOT NULL,
    country text NOT NULL,
    position integer NOT NULL UNIQUE
);

CREATE TABLE airlines (
    code text PRIMARY KEY,
    name text NOT NULL
);

-- Рейсы. Цена — целые рубли (integer), чтобы в JSON она уходила числом, а не Decimal.
CREATE TABLE flights (
    id text PRIMARY KEY CHECK (id ~ '^[A-Za-z0-9_-]+$'),
    flight_number text NOT NULL,
    airline_code text NOT NULL REFERENCES airlines (code),
    origin_code text NOT NULL REFERENCES cities (code),
    destination_code text NOT NULL REFERENCES cities (code),
    departure_at timestamptz NOT NULL,
    arrival_at timestamptz NOT NULL,
    duration_minutes integer NOT NULL CHECK (duration_minutes > 0),
    price_amount integer NOT NULL CHECK (price_amount >= 0),
    currency text NOT NULL DEFAULT 'RUB',
    seats_available integer NOT NULL CHECK (seats_available >= 0),
    CHECK (origin_code <> destination_code),
    CHECK (arrival_at > departure_at)
);

-- Поиск идёт по паре городов и интервалу времени вылета.
CREATE INDEX flights_search_idx ON flights (origin_code, destination_code, departure_at);

-- Брони. Уникальность кода держит ограничение базы, а не проверка перед вставкой.
CREATE TABLE bookings (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE CHECK (code ~ '^[A-Z0-9]{6}$'),
    status text NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
    flight_id text NOT NULL REFERENCES flights (id),
    contact_email text NOT NULL,
    contact_phone text NOT NULL,
    total_amount integer NOT NULL CHECK (total_amount >= 0),
    currency text NOT NULL DEFAULT 'RUB',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Пассажиры существуют только внутри брони.
-- last_name_key — фамилия, приведённая к единому виду (без внешних пробелов, в нижнем регистре):
-- по ней сравнивается второй фактор доступа к брони, независимо от локали сервера базы.
CREATE TABLE booking_passengers (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    booking_id bigint NOT NULL REFERENCES bookings (id) ON DELETE CASCADE,
    position integer NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    last_name_key text NOT NULL,
    date_of_birth date NOT NULL,
    document_number text NOT NULL,
    UNIQUE (booking_id, position)
);

CREATE INDEX booking_passengers_last_name_idx ON booking_passengers (booking_id, last_name_key);
