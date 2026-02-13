"""Legacy compatibility wrapper for database initialization."""

from core.database import init_sqlite_schema


def criar_banco() -> None:
    """Backward compatible alias."""

    init_sqlite_schema()
