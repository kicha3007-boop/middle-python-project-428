"""Точка входа: uvicorn --factory app.main:create_app.

Фабрика, а не модульный объект app: пул соединений открывается при старте приложения,
и простой импорт модуля (например, тестами) к базе не подключается.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.config import PUBLIC_DIR, database_url
from app.db import create_pool
from app.errors import register_error_handlers
from app.routes import api, create_static_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = create_pool(database_url())
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()


def create_app(public_dir: Path = PUBLIC_DIR) -> FastAPI:
    app = FastAPI(
        title="Flight Booking API",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    register_error_handlers(app)
    # Порядок важен: сначала API (с JSON-404 на неизвестный путь под /api), SPA-fallback последним.
    app.include_router(api)
    app.include_router(create_static_router(public_dir))
    return app
