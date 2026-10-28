"""Применение SQL-миграций из db/migrations.

Порядок задаётся числовым префиксом имени файла (0001_..., 0002_...), а не порядком файлов
в каталоге. Применённые миграции учитываются в таблице schema_migrations, поэтому повторный
запуск ничего не делает.
"""

import re
from pathlib import Path

import psycopg

from app.config import MIGRATIONS_DIR

MIGRATION_NAME = re.compile(r"^(\d+)_[a-z0-9_]+\.sql$")
# Произвольный ключ advisory-блокировки: два одновременных запуска не применят миграцию дважды.
LOCK_KEY = 428_001


def discover(directory: Path = MIGRATIONS_DIR) -> list[tuple[int, Path]]:
    found = []
    for path in directory.glob("*.sql"):
        match = MIGRATION_NAME.match(path.name)
        if not match:
            raise ValueError(f"Имя миграции не по шаблону NNNN_name.sql: {path.name}")
        found.append((int(match.group(1)), path))
    found.sort(key=lambda item: item[0])
    versions = [version for version, _ in found]
    if len(versions) != len(set(versions)):
        raise ValueError("Номера миграций повторяются")
    return found


def migrate(conn: psycopg.Connection) -> list[str]:
    applied_now = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version integer PRIMARY KEY,
                name text NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        applied = {row["version"] for row in rows}
        for version, path in discover():
            if version in applied:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                (version, path.name),
            )
            applied_now.append(path.name)
    return applied_now
