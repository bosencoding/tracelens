"""Settings endpoints. GET is open, PATCH is loopback/CORS-origin only (no auth in this app)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from . import db, runtime_settings
from .config import settings
from .errors import ApiError
from .models import AppSettings, SettingsPatch

router = APIRouter(prefix="/api/settings", tags=["settings"])

APP_VERSION = "2.1.0"
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _payload() -> AppSettings:
    return AppSettings(
        max_upload_mb=runtime_settings.max_upload_mb(),
        db_path=str(settings().db_path),
        evidence_count=db.row("SELECT COUNT(*) AS n FROM evidence")["n"],
        app_version=APP_VERSION,
    )


def _require_local(request: Request) -> None:
    """No auth here: refuse writes unless the caller is on this machine or an allowed origin."""
    client = request.client.host if request.client else ""
    origin = request.headers.get("origin")
    if client in LOOPBACK or (origin and origin in settings().origin_list):
        return
    raise ApiError(
        "pengaturan hanya bisa diubah dari mesin ini (loopback) atau origin yang diizinkan",
        "forbidden",
        403,
    )


@router.get("", response_model=AppSettings)
def read_settings() -> AppSettings:
    return _payload()


@router.patch("", response_model=AppSettings)
def update_settings(body: SettingsPatch, request: Request) -> AppSettings:
    _require_local(request)
    runtime_settings.set_int(runtime_settings.MAX_UPLOAD_KEY, body.max_upload_mb)
    return _payload()
