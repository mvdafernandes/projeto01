"""Database access layer with Supabase primary and SQLite fallback."""

from __future__ import annotations

import sqlite3
from urllib.parse import urlparse

from core.config import cache_resource, get_settings


@cache_resource
def get_supabase_client():
    """Return cached Supabase client when credentials are valid."""

    settings = get_settings()
    if settings.app_db_mode == "local":
        return None
    if not settings.supabase_url or not settings.supabase_key:
        if settings.app_db_mode == "remote":
            raise RuntimeError("APP_DB_MODE=remote exige SUPABASE_URL/SUPABASE_KEY válidos.")
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
            user_id INTEGER,
            data TEXT NOT NULL,
            valor REAL NOT NULL CHECK (valor >= 0),
            km REAL NOT NULL CHECK (km >= 0),
            km_rodado_total REAL NOT NULL DEFAULT 0 CHECK (km_rodado_total >= 0),
            "tempo trabalhado" INTEGER NOT NULL,
            observacao TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias_despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nome TEXT NOT NULL UNIQUE
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS despesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL CHECK (valor >= 0),
            observacao TEXT,
            tipo_despesa TEXT NOT NULL DEFAULT 'VARIAVEL',
            subcategoria_fixa TEXT,
            esfera_despesa TEXT NOT NULL DEFAULT 'NEGOCIO',
            litros REAL NOT NULL DEFAULT 0 CHECK (litros >= 0)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS controle_km (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data_inicio TEXT NOT NULL,
            data_fim TEXT NOT NULL,
            km_total_rodado REAL NOT NULL DEFAULT 0 CHECK (km_total_rodado >= 0)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS controle_litros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            data TEXT NOT NULL,
            litros REAL NOT NULL DEFAULT 0 CHECK (litros >= 0)
        )
        """
    )
    if not _sqlite_column_exists(cursor, "controle_km", "data_inicio"):
        cursor.execute("ALTER TABLE controle_km ADD COLUMN data_inicio TEXT")
    if not _sqlite_column_exists(cursor, "controle_km", "data_fim"):
        cursor.execute("ALTER TABLE controle_km ADD COLUMN data_fim TEXT")
    if _sqlite_column_exists(cursor, "controle_km", "data"):
        cursor.execute("UPDATE controle_km SET data_inicio = COALESCE(data_inicio, data)")
        cursor.execute("UPDATE controle_km SET data_fim = COALESCE(data_fim, data)")
    cursor.execute("UPDATE controle_km SET data_inicio = COALESCE(data_inicio, date('now'))")
    cursor.execute("UPDATE controle_km SET data_fim = COALESCE(data_fim, data_inicio)")
    cursor.execute("UPDATE controle_litros SET litros = COALESCE(litros, 0)")

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
    if not _sqlite_column_exists(cursor, "despesas", "litros"):
        cursor.execute("ALTER TABLE despesas ADD COLUMN litros REAL NOT NULL DEFAULT 0")
    if not _sqlite_column_exists(cursor, "receitas", "km_rodado_total"):
        cursor.execute("ALTER TABLE receitas ADD COLUMN km_rodado_total REAL NOT NULL DEFAULT 0")
    for table in ["receitas", "despesas", "investimentos", "categorias_despesas", "controle_km", "controle_litros"]:
        if not _sqlite_column_exists(cursor, table, "user_id"):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")

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
    cursor.execute("UPDATE despesas SET litros = COALESCE(litros, 0)")
    cursor.execute("UPDATE receitas SET km_rodado_total = COALESCE(km_rodado_total, km, 0)")
    # Auth users table for local fallback mode.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            cpf TEXT UNIQUE,
            nome_completo TEXT,
            data_nascimento TEXT,
            pergunta_secreta TEXT,
            resposta_secreta_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    if not _sqlite_column_exists(cursor, "usuarios", "must_change_password"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            last_seen_at TEXT,
            user_agent TEXT
        )
        """
    )
    for table in ["receitas", "despesas", "investimentos", "categorias_despesas", "controle_km", "controle_litros"]:
        cursor.execute(
            f"""
            UPDATE {table}
            SET user_id = COALESCE(
                user_id,
                (SELECT id FROM usuarios ORDER BY id ASC LIMIT 1)
            )
            """
        )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            key TEXT NOT NULL,
            action TEXT NOT NULL,
            failures INTEGER NOT NULL DEFAULT 0,
            blocked_until TEXT,
            last_failure_at TEXT,
            PRIMARY KEY (key, action)
        )
        """
    )

    # Seed default categories only when missing.
    for nome in ["Combustível", "Alimentação", "Manutenção", "Lavagem", "Seguro", "Outros"]:
        cursor.execute("INSERT OR IGNORE INTO categorias_despesas (nome) VALUES (?)", (nome,))

    # Helpful indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receitas_data ON receitas(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_despesas_data ON despesas(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_receitas_user_id ON receitas(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_despesas_user_id ON despesas(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investimentos_user_id ON investimentos(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_categorias_user_id ON categorias_despesas(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investimentos_data ON investimentos(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_investimentos_categoria ON investimentos(categoria)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_controle_km_data_inicio ON controle_km(data_inicio)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_controle_km_data_fim ON controle_km(data_fim)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_controle_km_user_id ON controle_km(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_controle_litros_data ON controle_litros(data)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_controle_litros_user_id ON controle_litros(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions(expires_at)")

    conn.commit()
    conn.close()
