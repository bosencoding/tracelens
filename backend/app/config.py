"""Settings for v2: SQLite file, upload dir, upload limit. No network services, no keys."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    db_path: Path = DATA / "tracelens.db"
    upload_dir: Path = DATA / "uploads"
    max_upload_mb: int = 20

    @property
    def max_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def settings() -> Settings:
    cfg = Settings()
    cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.upload_dir.mkdir(parents=True, exist_ok=True)
    return cfg
