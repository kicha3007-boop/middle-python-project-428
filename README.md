# Бекенд для бронирования авиабилетов (Python)

[![hexlet-check](https://github.com/kicha3007-boop/middle-python-project-428/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/kicha3007-boop/middle-python-project-428/actions)
[![CI](https://github.com/kicha3007-boop/middle-python-project-428/actions/workflows/ci.yml/badge.svg)](https://github.com/kicha3007-boop/middle-python-project-428/actions/workflows/ci.yml)

HTTP API сервиса бронирования авиабилетов: справочник городов, поиск рейсов, оформление, просмотр
и отмена брони. Данные хранятся в PostgreSQL. Фронтенд — готовое приложение Хекслета
(npm-пакет `@hexlet/python-flight-booking-frontend`), сервер раздаёт его на том же порту, что и API.

Учебный проект Хекслета: https://ru.hexlet.io/programs/middle-python
Как это должно работать: https://files.hexlet.app/a/76p1kx

## Стек

- Python 3.13, FastAPI, Uvicorn
- PostgreSQL, psycopg 3 и psycopg_pool, миграции на голом SQL
- uv (зависимости, `uv.lock`), ruff (линтер), pytest
- TypeSpec → OpenAPI (`contract/`)

## Требования

- Python 3.13 и [uv](https://docs.astral.sh/uv/)
- Node.js 22 или новее (ставит пакет с фронтендом и TypeSpec)
- PostgreSQL — свой или в Docker (`docker compose up -d db`)
- GNU Make

## Быстрый старт

```bash
git clone https://github.com/kicha3007-boop/middle-python-project-428.git
cd middle-python-project-428

cp .env.example .env     # DATABASE_URL и PORT; Makefile читает .env сам
make db-up               # PostgreSQL в Docker на localhost:5432 (или своя база)
make install             # uv sync + npm ci
make build               # раскладывает фронтенд в public/, к базе не обращается
make start               # миграции + справочные данные + сервер на 0.0.0.0:$PORT
```

Откройте http://localhost:8080 — главная сразу покажет рейсы Москва → Санкт-Петербург на сегодня.

Всё в контейнерах одной командой (база + приложение из `Dockerfile`):

```bash
docker compose up --build
```

## Переменные окружения

| Переменная | Назначение | По умолчанию |
| --- | --- | --- |
| `DATABASE_URL` | строка подключения к PostgreSQL, например `postgresql://postgres:postgres@localhost:5432/flight_booking` | обязательна |
| `PORT` | порт HTTP-сервера | `8080` |

Шаблон — `.env.example`. Сам `.env` в репозиторий не попадает.

## Команды

| Команда | Что делает |
| --- | --- |
| `make install` | ставит зависимости Python (вместе с dev) и Node.js |
| `make build` | копирует собранный фронтенд из `node_modules` в `public/` |
| `make start` | применяет миграции, загружает справочник и рейсы, запускает Uvicorn |
| `make migrate` / `make seed` | только миграции / только загрузка данных |
| `make test` | тесты на API (pytest), нужна база по `DATABASE_URL` |
| `make lint` | ruff: проверка и формат |
| `make format` | автоисправление стиля |
| `make contract` | пересборка `contract/openapi.yaml` из `contract/main.tsp` |
| `make db-up` / `make db-down` | локальная PostgreSQL в Docker |

`make start` можно запускать повторно: применённые миграции учитываются в `schema_migrations`,
справочники обновляются по ключу, у рейсов детерминированные id, поэтому дублей нет.

## Тесты и линтер

```bash
make db-up
make test   # pytest бьёт по приложению целиком через TestClient
make lint
```

Тесты сами применяют миграции и загружают данные в базу из `DATABASE_URL`. Каждый тест готовит свои
данные: дату поиска считает от сегодняшнего дня, бронь создаёт свою.

В GitHub Actions (`.github/workflows/ci.yml`) на каждый пуш: установка зависимостей, сборка,
линтер и тесты с PostgreSQL в сервис-контейнере.

## API

Полный контракт — `contract/openapi.yaml` (исходник — `contract/main.tsp`).

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | `/api/health` | хелсчек `{"status": "ok"}` |
| GET | `/api/cities` | справочник городов (Москва и Санкт-Петербург первыми) |
| GET | `/api/flights?origin=&destination=&date=&passengers=` | поиск рейсов |
| GET | `/api/flights/{id}` | рейс по идентификатору |
| POST | `/api/bookings` | создать бронь (201) |
| GET | `/api/bookings/{code}?lastName=` | просмотр брони по коду и фамилии |
| POST | `/api/bookings/{code}/cancel` | отмена брони, фамилия в теле `{"lastName": "..."}` |

Ошибки — `{"code": "validation_error" | "not_found", "message": "..."}` с кодами 400 и 404.
Всё, что не начинается с `/api/` и не является файлом статики, отдаёт `index.html` (SPA-fallback).

```bash
curl http://localhost:8080/api/cities
curl "http://localhost:8080/api/flights?origin=MOW&destination=LED&date=$(date -u +%F)"
```

## Устройство

```text
app/main.py          create_app(): пул соединений, обработчики ошибок, роутеры
app/routes.py        тонкие обработчики API и раздача статики с SPA-fallback
app/services.py      сценарии: поиск, оформление, просмотр и отмена брони
app/repository.py    все SQL-запросы (параметризованные)
app/presenter.py     строки базы → JSON по контракту (camelCase, время UTC с Z)
app/schemas.py       pydantic-модели тел запросов
app/errors.py        формат ошибок {code, message}, 422 → 400
app/booking_code.py  генерация кода брони
app/migrations.py    применение db/migrations/NNNN_*.sql по номеру
app/seed.py          города, авиакомпании, рейсы на 30 дней от текущей даты
app/cli.py           python -m app.cli migrate | seed | prepare
```

## Docker

`Dockerfile` в корне собирает образ приложения: забирает фронтенд из npm-пакета, ставит зависимости
по `uv.lock` без dev и запускает `make start`. Проверить локально:

```bash
docker build -t flight-booking .
docker run --rm -e PORT=8080 -e DATABASE_URL=<строка подключения> -p 8080:8080 flight-booking
```

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
