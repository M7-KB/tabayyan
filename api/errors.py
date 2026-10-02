"""Fixed error responses never echo request bodies or exception details."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def response(status: int, code: str, message_en: str, message_ar: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message_ar": message_ar,
                "message_en": message_en,
            }
        },
    )


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return response(exc.status_code, code, "Request could not be completed", "تعذر إتمام الطلب")

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return response(422, "INVALID_REQUEST", "Invalid request", "الطلب غير صالح")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return response(500, "INTERNAL_ERROR", "Internal service error", "خطأ داخلي في الخدمة")
