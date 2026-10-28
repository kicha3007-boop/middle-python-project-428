"""Генерация кода брони: ровно 6 символов из A-Z и 0-9.

Из алфавита убраны 0, O, 1 и I — их легко перепутать, когда код диктуют вслух.
Уникальность гарантирует ограничение UNIQUE в базе, здесь только случайная строка.
"""

import secrets
import string

ALPHABET = "".join(ch for ch in string.ascii_uppercase + string.digits if ch not in "0O1I")
CODE_LENGTH = 6


def generate_booking_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_booking_code(code: str) -> str:
    """Код из адреса приводится к виду, в котором хранится: ab12cd находит бронь AB12CD."""
    return code.strip().upper()
