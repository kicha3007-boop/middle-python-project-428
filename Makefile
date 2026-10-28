# Локальные переменные окружения (DATABASE_URL, PORT) из .env, если файл есть.
-include .env
export

FRONTEND_DIST = node_modules/@hexlet/python-flight-booking-frontend/dist
# Запуск без dev-зависимостей: --inexact не удаляет pytest и ruff, если они уже стоят,
# а в чистом окружении (контейнер проверки, образ) uv доставит только нужное приложению.
RUN = uv run --frozen --no-dev --inexact

.PHONY: install build start test lint format migrate seed contract db-up db-down

# Зависимости Python (вместе с инструментами разработки) и Node.js (фронтенд и TypeSpec).
install:
	uv sync --frozen
	npm ci

# Раскладывает собранный фронтенд в public/. К базе не обращается.
build:
	mkdir -p public
	rm -rf public/assets public/index.html
	cp -R $(FRONTEND_DIST)/. public/

# Миграции и справочные данные, затем сервер. Повторный запуск безопасен.
start:
	$(RUN) python -m app.cli prepare
	$(RUN) uvicorn --factory app.main:create_app --host 0.0.0.0 --port $${PORT:-8080}

migrate:
	$(RUN) python -m app.cli migrate

seed:
	$(RUN) python -m app.cli seed

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

# Пересборка contract/openapi.yaml из contract/main.tsp.
contract:
	npx tsp compile contract

# Локальная база в Docker (см. docker-compose.yml).
db-up:
	docker compose up -d db

db-down:
	docker compose down
