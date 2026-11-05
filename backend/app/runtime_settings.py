"""Runtime settings stored in SQLite, editable from the UI.

The env value (MAX_UPLOAD_MB) is only the seed for a fresh database; after that the
`settings` table is the single source of truth, so a change survives a restart.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import db
from .config import settings as env_settings

MAX_UPLOAD_KEY = "max_upload_mb"
LIMITS = (1, 500)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_defaults() -> None:
    """Insert defaults once. Existing rows are never overwritten by the env value."""
    if db.row("SELECT 1 FROM settings WHERE key = ?", (MAX_UPLOAD_KEY,)) is None:
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?,?,?)",
            (MAX_UPLOAD_KEY, str(env_settings().max_upload_mb), _now()),
        )


def get_int(key: str, default: int) -> int:
    row = db.row("SELECT value FROM settings WHERE key = ?", (key,))
    if row is None:
        return default
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return default


def set_int(key: str, value: int) -> None:
    db.execute(
        """INSERT INTO settings (key, value, updated_at) VALUES (?,?,?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value,
             updated_at = excluded.updated_at""",
        (key, str(value), _now()),
    )


def max_upload_mb() -> int:
    return get_int(MAX_UPLOAD_KEY, env_settings().max_upload_mb)


def max_upload_bytes() -> int:
    return max_upload_mb() * 1024 * 1024
