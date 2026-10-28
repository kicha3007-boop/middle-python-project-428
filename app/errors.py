"""Единый формат ошибок API: {"code": "...", "message": "..."}.

Обработчики регистрируются один раз на всё приложение и переводят в этот формат
и собственные ошибки, и ошибки фреймворка (422 валидации, 404/405 маршрутизации).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

HTTP_ERROR_CODES = {
    400: "validation_error",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(ApiError):
    status_code = 400
    code = "validation_error"


class NotFoundError(ApiError):
    status_code = 404
    code = "not_found"


def error_response(status_code: int, code: str, message: str, headers=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message},
        headers=headers,
    )


def describe_validation_error(error: dict) -> str:
    location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")]
    field = ".".join(location)
    if error.get("type") == "json_invalid":
        return "Тело запроса — не корректный JSON"
    if not field:
        return "Некорректное тело запроса"
    if error.get("type") == "missing":
        return f"Не заполнено обязательное поле {field}"
    return f"Некорректное значение поля {field}"


async def handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = describe_validation_error(errors[0]) if errors else "Некорректный запрос"
    return error_response(400, "validation_error", message)


async def handle_http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = HTTP_ERROR_CODES.get(exc.status_code, "http_error")
    return error_response(exc.status_code, code, str(exc.detail), headers=exc.headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
