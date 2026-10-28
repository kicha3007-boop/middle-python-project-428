"""Маршруты: API под /api и раздача фронтенда с SPA-fallback.

Обработчики тонкие: разбирают запрос, зовут сценарий из app.services и отдают результат.
HEAD перечислен у GET-маршрутов явно: FastAPI сам его не добавляет.
"""

from datetime import date
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app import services
from app.db import get_connection
from app.errors import NotFoundError
from app.schemas import CreateBookingIn, LastNameIn

READ = ["GET", "HEAD"]
ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

Connection = Annotated[psycopg.Connection, Depends(get_connection)]
RequiredParam = Annotated[str, Query(min_length=1)]

api = APIRouter(prefix="/api")


@api.api_route("/health", methods=READ)
def health() -> dict:
    return {"status": "ok"}


@api.api_route("/cities", methods=READ)
def list_cities(conn: Connection) -> list[dict]:
    return services.list_cities(conn)


@api.api_route("/flights", methods=READ)
def search_flights(
    conn: Connection,
    origin: RequiredParam,
    destination: RequiredParam,
    day: Annotated[date, Query(alias="date")],
    passengers: Annotated[int, Query(ge=1)] = 1,
) -> list[dict]:
    return services.search_flights(conn, origin, destination, day, passengers)


@api.api_route("/flights/{flight_id}", methods=READ)
def get_flight(conn: Connection, flight_id: str) -> dict:
    return services.get_flight(conn, flight_id)


@api.post("/bookings", status_code=201)
def create_booking(conn: Connection, payload: CreateBookingIn) -> dict:
    return services.create_booking(conn, payload)


@api.api_route("/bookings/{code}", methods=READ)
def get_booking(
    conn: Connection, code: str, last_name: Annotated[str | None, Query(alias="lastName")] = None
) -> dict:
    return services.get_booking(conn, code, last_name)


@api.post("/bookings/{code}/cancel")
def cancel_booking(conn: Connection, code: str, body: LastNameIn | None = None) -> dict:
    return services.cancel_booking(conn, code, body.last_name if body else None)


@api.api_route("/{path:path}", methods=ALL_METHODS, include_in_schema=False)
def api_not_found(path: str) -> None:
    raise NotFoundError(f"Неизвестный адрес API: /api/{path}")


def create_static_router(public_dir: Path) -> APIRouter:
    """SPA-fallback: существующий файл из public отдаётся как есть, иначе — index.html."""
    router = APIRouter()
    root = public_dir.resolve()

    @router.api_route("/{path:path}", methods=READ, include_in_schema=False)
    def spa(path: str) -> FileResponse:
        file = (root / path).resolve()
        # Путь пришёл из запроса: «..» не должен выводить за пределы каталога со статикой.
        if path and file.is_relative_to(root) and file.is_file():
            return FileResponse(file)
        index = root / "index.html"
        if not index.is_file():
            raise NotFoundError("Фронтенд не собран: выполните make build")
        return FileResponse(index)

    return router
