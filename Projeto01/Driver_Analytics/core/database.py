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


def _sqlite_column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def init_sqlite_schema() -> None:
    """Create local fallback schema if it does not exist."""

    conn = get_sqlite_connection()
    cursor = conn.cursor()

    # Core business tables
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
        CREATE TABLE IF NOT EXISTS categorias_despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
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
            observacao TEXT,
            tipo_despesa TEXT NOT NULL DEFAULT 'VARIAVEL',
            subcategoria_fixa TEXT,
            esfera_despesa TEXT NOT NULL DEFAULT 'NEGOCIO'
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            data_inicio TEXT,
            data_fim TEXT,
            tipo_movimentacao TEXT,
            categoria TEXT NOT NULL DEFAULT 'Renda Fixa',
            aporte REAL NOT NULL,
            "total aportado" REAL NOT NULL,
            rendimento REAL NOT NULL,
            "patrimonio total" REAL NOT NULL
        )
        """
    )

    # Backward-compatible migration for existing local DBs.
    if not _sqlite_column_exists(cursor, "investimentos", "categoria"):
        cursor.execute("ALTER TABLE investimentos ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Renda Fixa'")
    if not _sqlite_column_exists(cursor, "investimentos", "data_inicio"):
        cursor.execute("ALTER TABLE investimentos ADD COLUMN data_inicio TEXT")
    if not _sqlite_column_exists(cursor, "investimentos", "data_fim"):
        cursor.execute("ALTER TABLE investimentos ADD COLUMN data_fim TEXT")
    if not _sqlite_column_exists(cursor, "investimentos", "tipo_movimentacao"):
        cursor.execute("ALTER TABLE investimentos ADD COLUMN tipo_movimentacao TEXT")
    if not _sqlite_column_exists(cursor, "despesas", "tipo_despesa"):
        cursor.execute("ALTER TABLE despesas ADD COLUMN tipo_despesa TEXT NOT NULL DEFAULT 'VARIAVEL'")
    if not _sqlite_column_exists(cursor, "despesas", "subcategoria_fixa"):
        cursor.execute("ALTER TABLE despesas ADD COLUMN subcategoria_fixa TEXT")
    if not _sqlite_column_exists(cursor, "despesas", "esfera_despesa"):
        cursor.execute("ALTER TABLE despesas ADD COLUMN esfera_despesa TEXT NOT NULL DEFAULT 'NEGOCIO'")

    cursor.execute("UPDATE investimentos SET data_inicio = COALESCE(data_inicio, data)")
    cursor.execute("UPDATE investimentos SET data_fim = COALESCE(data_fim, data)")
    cursor.execute(
        """
        UPDATE investimentos
        SET tipo_movimentacao = COALESCE(
            tipo_movimentacao,
            CASE
                WHEN COALESCE(aporte, 0) > 0 THEN 'APORTE'
                WHEN COALESCE(aporte, 0) < 0 THEN 'RETIRADA'
                ELSE 'RENDIMENTO'
            END
        )
        """
    )
    cursor.execute("UPDATE despesas SET tipo_despesa = COALESCE(tipo_despesa, 'VARIAVEL')")
    cursor.execute("UPDATE despesas SET esfera_despesa = COALESCE(esfera_despesa, 'NEGOCIO')")

    # Auth users table for local fallback mode.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            cpf TEXT UNIQUE,
            nome_completo TEXT,
            data_nascimento TEXT,
            pergunta_secreta TEXT,
            resposta_secreta_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Seed default categories only when missing.
    for nome in ["Combustível", "Alimentação", "Manutenção", "Lavagem", "Seguro", "Outros"]:
        cursor.execute("INSERT OR IGNORE INTO categorias_despesas (nome) VALUES (?)", (nome,))

    # Helpful indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receitas_data ON receitas(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_despesas_data ON despesas(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investimentos_data ON investimentos(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investimentos_categoria ON investimentos(categoria)")

    conn.commit()
    conn.close()
