"""Модели тел запросов.

Валидация проверяет наличие и непустоту полей, а не их формат: номер документа «1» допустим.
Исключение — дата рождения: строка, которая не разбирается как дата, отсекается здесь,
а не ошибкой базы.
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ContactIn(CamelModel):
    email: NonEmptyStr
    phone: NonEmptyStr


class PassengerIn(CamelModel):
    first_name: NonEmptyStr
    last_name: NonEmptyStr
    date_of_birth: date
    document_number: NonEmptyStr


class CreateBookingIn(CamelModel):
    flight_id: NonEmptyStr
    contact: ContactIn
    passengers: list[PassengerIn] = Field(min_length=1)


class LastNameIn(CamelModel):
    last_name: str | None = None
