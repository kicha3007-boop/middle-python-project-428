"""Настройки приложения из переменных окружения."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public"
MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Не задана переменная окружения DATABASE_URL")
    return url
