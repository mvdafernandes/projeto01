"""Repository for expense categories."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository


class CategoriasDespesasRepository(BaseRepository):
    """Data access for categorias_despesas table."""

    table_name = "categorias_despesas"
    columns = ["id", "nome"]
    numeric_columns = ["id"]

    @staticmethod
    def _dedupe_rows(rows: list[dict]) -> list[dict]:
        by_name: dict[str, dict] = {}
        for row in rows:
            nome = str(row.get("nome", "")).strip()
            if not nome:
                continue
            key = nome.casefold()
            existing = by_name.get(key)
            # User-specific rows win over global rows with the same display name.
            if existing is None or existing.get("user_id") is None:
                by_name[key] = dict(row)
        return sorted(by_name.values(), key=lambda item: str(item.get("nome", "")).casefold())

    def listar(self) -> pd.DataFrame:
        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            rows: list[dict] = []
            try:
                global_rows = client.table(self.table_name).select("*").is_("user_id", "null").order("nome").execute().data or []
                rows.extend(dict(row) for row in global_rows)
                if user_id is not None:
                    user_rows = client.table(self.table_name).select("*").eq("user_id", int(user_id)).order("nome").execute().data or []
                    rows.extend(dict(row) for row in user_rows)
                return self._normalize(pd.DataFrame(self._dedupe_rows(rows)))
            except Exception:
                return self._normalize(pd.DataFrame())

        return self._normalize(pd.DataFrame())

    def buscar_por_nome(self, nome: str) -> pd.DataFrame:
        normalized = str(nome).strip()
        if not normalized:
            return pd.DataFrame(columns=self.columns)

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                rows: list[dict] = []
                if user_id is not None:
                    user_rows = client.table(self.table_name).select("*").ilike("nome", normalized).eq("user_id", int(user_id)).execute().data or []
                    rows.extend(dict(row) for row in user_rows)
                global_rows = client.table(self.table_name).select("*").ilike("nome", normalized).is_("user_id", "null").execute().data or []
                rows.extend(dict(row) for row in global_rows)
                rows = [row for row in self._dedupe_rows(rows) if str(row.get("nome", "")).strip().casefold() == normalized.casefold()]
                return self._normalize(pd.DataFrame(rows))
            except Exception:
                return self._normalize(pd.DataFrame())

        return self._normalize(pd.DataFrame())

    def inserir(self, nome: str) -> None:
        normalized = str(nome).strip()
        if not normalized:
            return

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            try:
                payload = {"nome": normalized, "user_id": int(user_id)}
                client.table(self.table_name).insert(payload).execute()
            except Exception:
                # If migration was not executed yet, keep app running and allow free-text fallback.
                return
            return
        raise RuntimeError("Supabase remoto indisponivel.")
