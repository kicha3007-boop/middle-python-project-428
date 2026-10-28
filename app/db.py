"""Подключение к PostgreSQL: пул для приложения и одиночное соединение для консольных команд."""

from collections.abc import Iterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# Пояс сессии выставляется явно: по умолчанию он берётся с сервера базы
# и отличается от машины к машине.
CONNECTION_OPTIONS = {"options": "-c TimeZone=UTC", "row_factory": dict_row}


def create_pool(url: str) -> ConnectionPool:
    return ConnectionPool(url, kwargs=CONNECTION_OPTIONS, min_size=1, max_size=10, open=True)


def connect(url: str) -> psycopg.Connection:
    return psycopg.connect(url, **CONNECTION_OPTIONS)


def get_connection(request: Request) -> Iterator[psycopg.Connection]:
    """Зависимость FastAPI: соединение на время запроса.

    Контекст пула фиксирует транзакцию при успехе, откатывает при исключении
    и в любом случае возвращает соединение в пул.
    """
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        yield conn
