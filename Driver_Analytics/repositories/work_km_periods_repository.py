"""Repository for historical total-km periods."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository


class WorkKmPeriodsRepository(BaseRepository):
    """Data access for work_km_periods table."""

    table_name = "work_km_periods"
    columns = [
        "id",
        "start_date",
        "end_date",
        "km_total_periodo",
        "notes",
        "created_at",
        "updated_at",
    ]
    numeric_columns = ["id", "km_total_periodo"]

    def listar(self) -> pd.DataFrame:
        data = self._list_remote_rows(order_by="start_date")
        return self._normalize(pd.DataFrame(data))

    def listar_raw(self) -> list[dict]:
        return self._list_remote_rows(order_by="start_date")

    def buscar_por_id(self, item_id: int) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        rows = (
            client.table(self.table_name)
            .select("*")
            .eq("id", int(item_id))
            .eq("user_id", int(user_id))
            .limit(1)
            .execute()
            .data
        )
        return dict(rows[0]) if rows else None

    def inserir(self, payload: dict) -> dict:
        client = self._supabase()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        data = client.table(self.table_name).insert(self._with_user_id(payload)).execute().data or []
        return dict(data[0]) if data else {}

    def atualizar(self, item_id: int, payload: dict) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        data = (
            client.table(self.table_name)
            .update(payload)
            .eq("id", int(item_id))
            .eq("user_id", int(user_id))
            .execute()
            .data
            or []
        )
        return dict(data[0]) if data else self.buscar_por_id(int(item_id))

    def deletar(self, item_id: int) -> None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        client.table(self.table_name).delete().eq("id", int(item_id)).eq("user_id", int(user_id)).execute()
