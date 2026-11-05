"""SQLite access: one connection per call, dict rows, schema applied on first use."""

from __future__ import annotations

import json
import sqlite3
import sys
from contextlib import contextmanager
from typing import Any, Iterator

from .config import settings

SCHEMA = __import__("pathlib").Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings().db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA.read_text())


def rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    found = rows(sql, params)
    return found[0] if found else None


def execute(sql: str, params: tuple = ()) -> int:
    with connect() as conn:
        return conn.execute(sql, params).rowcount


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback


def list_reference_cameras() -> list[dict[str, Any]]:
    """List all reference cameras with parsed quantization tables."""
    sql = """
        SELECT 
            id, label, make, model, 
            qtable_luma, qtable_chroma,
            subsampling, note
        FROM reference_cameras
        ORDER BY make, model
    """
    results = []
    for r in rows(sql):
        results.append({
            "id": r["id"],
            "label": r["label"],
            "make": r["make"],
            "model": r["model"],
            "luma_table": loads(r.get("qtable_luma"), []),
            "chroma_table": loads(r.get("qtable_chroma"), []),
            "subsampling": r.get("subsampling", "4:2:0"),
            "note": r.get("note", ""),
        })
    return results
