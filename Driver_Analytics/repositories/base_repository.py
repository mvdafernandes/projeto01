"""Base repository helpers for dataframe and backend handling."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

from core.database import get_supabase_client
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
        if col in {"id", "tempo trabalhado", "recorrencia_meses"}:
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
        raise RuntimeError("Persistencia local desabilitada. Configure e use apenas Supabase remoto.")

    def _normalize(self, df: pd.DataFrame | None) -> pd.DataFrame:
        return normalize_dataframe(df, self.columns, self.numeric_columns)

    def _is_remote(self) -> bool:
        return self._supabase() is not None

    def _list_remote_rows(self, order_by: str | None = None) -> list[dict]:
        """Read rows from Supabase with safe user_id reconciliation for legacy data."""

        client = self._supabase()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")

        user_id = self._current_user_id()
        base_query = client.table(self.table_name).select("*")
        if order_by:
            base_query = base_query.order(order_by)
        if user_id is not None:
            user_query = client.table(self.table_name).select("*").eq("user_id", int(user_id))
            if order_by:
                user_query = user_query.order(order_by)
            try:
                data = user_query.execute().data or []
            except Exception as exc:
                raise RuntimeError(f"Falha ao consultar {self.table_name} no Supabase: {exc}") from exc
            if data:
                return [dict(row) for row in data]
        else:
            try:
                data = base_query.execute().data or []
                return [dict(row) for row in data]
            except Exception as exc:
                raise RuntimeError(f"Falha ao consultar {self.table_name} no Supabase: {exc}") from exc

        # No rows found for current user: try a legacy ownership reconciliation.
        try:
            all_data = base_query.execute().data or []
        except Exception as exc:
            raise RuntimeError(f"Falha ao consultar {self.table_name} no Supabase: {exc}") from exc
        if not all_data:
            return []

        if user_id is None:
            return [dict(row) for row in all_data]

        distinct_non_null_ids: set[int] = set()
        has_null_owner = False
        for row in all_data:
            value = dict(row).get("user_id")
            if value is None:
                has_null_owner = True
                continue
            try:
                distinct_non_null_ids.add(int(value))
            except Exception:
                pass

        # Safe only for single-tenant legacy data.
        if len(distinct_non_null_ids) <= 1:
            old_user_id = next(iter(distinct_non_null_ids), None)
            try:
                if old_user_id is not None and int(old_user_id) != int(user_id):
                    client.table(self.table_name).update({"user_id": int(user_id)}).eq("user_id", int(old_user_id)).execute()
                if has_null_owner:
                    client.table(self.table_name).update({"user_id": int(user_id)}).is_("user_id", "null").execute()
                repaired_query = client.table(self.table_name).select("*").eq("user_id", int(user_id))
                if order_by:
                    repaired_query = repaired_query.order(order_by)
                repaired = repaired_query.execute().data or []
                if repaired:
                    return [dict(row) for row in repaired]
            except Exception:
                pass

        # Compatibility fallback: never hide existing remote data in legacy ownership scenarios.
        # This avoids "all zero" dashboards when user_id history is inconsistent.
        return [dict(row) for row in all_data]

    def _current_user_id(self) -> int | None:
        # Lazy import avoids hard import coupling during app bootstrap/deploy.
        try:
            from core.auth import get_logged_user_id  # local import on purpose

            user_id = get_logged_user_id()
            return int(user_id) if user_id is not None else None
        except Exception:
            try:
                if st is None:
                    return None
                raw = st.session_state.get("current_user_id")
                return int(raw) if raw is not None else None
            except Exception:
                return None

    def _with_user_id(self, payload: dict) -> dict:
        out = dict(payload)
        user_id = self._current_user_id()
        if user_id is not None:
            out["user_id"] = int(user_id)
        return out
