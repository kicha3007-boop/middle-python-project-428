"""Консольные команды: python -m app.cli migrate | seed | prepare."""

import sys

from app.config import database_url
from app.db import connect
from app.migrations import migrate
from app.seed import seed

USAGE = "Использование: python -m app.cli migrate|seed|prepare"


def run_migrate() -> None:
    with connect(database_url()) as conn:
        applied = migrate(conn)
    print(f"Миграции применены: {', '.join(applied) if applied else 'новых нет'}")


def run_seed() -> None:
    with connect(database_url()) as conn:
        count = seed(conn)
    print(f"Справочные данные загружены, рейсов в окне: {count}")


COMMANDS = {
    "migrate": [run_migrate],
    "seed": [run_seed],
    "prepare": [run_migrate, run_seed],
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print(USAGE, file=sys.stderr)
        return 2
    for command in COMMANDS[argv[0]]:
        command()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
