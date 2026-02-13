"""Database access layer with Supabase primary and SQLite fallback."""

from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

from core.config import cache_resource, get_settings


@cache_resource
def get_supabase_client():
    """Return cached Supabase client when credentials are valid."""

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        return None

    parsed = urlparse(settings.supabase_url)
    if not parsed.scheme or not parsed.netloc or parsed.netloc.startswith("."):
        return None

    try:
        from supabase import create_client
    except Exception:
        return None

    try:
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception:
        return None


def get_sqlite_connection() -> sqlite3.Connection:
    """Return SQLite connection for local fallback mode."""

    settings = get_settings()
    return sqlite3.connect(settings.db_name)


def init_sqlite_schema() -> None:
    """Create local fallback schema if it does not exist."""

    conn = get_sqlite_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS receitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            km REAL NOT NULL,
            "tempo trabalhado" INTEGER NOT NULL,
            observacao TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            observacao TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            aporte REAL NOT NULL,
            "total aportado" REAL NOT NULL,
            rendimento REAL NOT NULL,
            "patrimonio total" REAL NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()
