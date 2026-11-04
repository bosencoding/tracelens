"""One error shape: {detail, code} (+ fields when a body field is at fault)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, detail: str, code: str, status: int = 400) -> None:
        self.detail = detail
        self.code = code
        self.status = status


class NotFound(ApiError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "not_found", 404)


class UnsupportedMedia(ApiError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "unsupported_media_type", 415)


class TooLarge(ApiError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "file_too_large", 413)


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail, "code": exc.code}, status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "not_found", 405: "method_not_allowed", 415: "unsupported_media_type"}
        return JSONResponse(
            {"detail": str(exc.detail), "code": codes.get(exc.status_code, "http_error")},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query"))
        return JSONResponse(
            {
                "detail": f"validasi gagal pada field '{field}': {first.get('msg', 'tidak valid')}",
                "code": "validation_error",
                "fields": [field] if field else [],
            },
            status_code=422,
        )
