"""TraceLens v2 API. Run: uv run uvicorn app.main:app --port 8001"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db, errors, routes_evidence, routes_reference, routes_settings, runtime_settings
from .config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    runtime_settings.seed_defaults()
    yield


app = FastAPI(
    title="TraceLens API",
    version="2.0.0",
    description=(
        "Identifikasi signature JPEG: EXIF, tabel kuantisasi, fingerprint encoder, dan jejak edit. "
        "Seluruh data contoh bersifat sintetis."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

errors.install(app)
app.include_router(routes_evidence.router)
app.include_router(routes_reference.router)
app.include_router(routes_settings.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "jpeg-signature-v2", "data": "synthetic", "db": "sqlite"}
