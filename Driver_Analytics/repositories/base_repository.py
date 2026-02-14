"""Base repository helpers for dataframe and backend handling."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from core.database import get_sqlite_connection, get_supabase_client
from domain.validators import ensure_columns


def _to_db_record(record: dict) -> dict:
    """Normalize in-memory keys to database keys."""

    payload = dict(record)
    if "tempo trabalhado" in payload:
        payload["tempo_trabalhado"] = payload.pop("tempo trabalhado")
    if "total aportado" in payload:
        payload["total_aportado"] = payload.pop("total aportado")
    if "patrimonio total" in payload:
        payload["patrimonio_total"] = payload.pop("patrimonio total")
    return payload


def _from_db_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize database columns to UI/domain expected names."""

    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    return df.rename(
        columns={
            "tempo_trabalhado": "tempo trabalhado",
            "total_aportado": "total aportado",
            "patrimonio_total": "patrimonio total",
        }
    )


def normalize_dataframe(
    df: pd.DataFrame | None,
    columns: Iterable[str],
    numeric_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Return schema-stable dataframe with optional numeric sanitation."""

    safe_df = _from_db_dataframe(df if isinstance(df, pd.DataFrame) else pd.DataFrame())
    safe_df = ensure_columns(safe_df, columns)

    for col in numeric_columns or []:
        safe_df[col] = pd.to_numeric(safe_df[col], errors="coerce").fillna(0.0)
        if col in {"id", "tempo trabalhado"}:
            safe_df[col] = safe_df[col].astype(int)

    return safe_df


class BaseRepository:
    """Base repository shared behavior."""

    table_name: str = ""
    columns: list[str] = []
    numeric_columns: list[str] = []

    def _supabase(self):
        return get_supabase_client()

    def _sqlite(self):
        return get_sqlite_connection()

    def _normalize(self, df: pd.DataFrame | None) -> pd.DataFrame:
        return normalize_dataframe(df, self.columns, self.numeric_columns)

    def _is_remote(self) -> bool:
        return self._supabase() is not None
