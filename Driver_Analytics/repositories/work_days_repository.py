"""Repository for work_days persistence."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository


class WorkDaysRepository(BaseRepository):
    """Data access for work_days table."""

    table_name = "work_days"
    columns = [
        "id",
        "work_date",
        "start_time",
        "end_time",
        "start_time_source",
        "end_time_source",
        "start_km",
        "end_km",
        "km_remunerado",
        "km_nao_remunerado_antes",
        "worked_minutes_calculated",
        "worked_minutes_manual",
        "worked_minutes_final",
        "status",
        "is_manually_adjusted",
        "notes",
        "created_at",
        "updated_at",
    ]
    numeric_columns = [
        "id",
        "start_km",
        "end_km",
        "km_remunerado",
        "km_nao_remunerado_antes",
        "worked_minutes_calculated",
        "worked_minutes_manual",
        "worked_minutes_final",
    ]

    def listar(self) -> pd.DataFrame:
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def listar_raw(self) -> list[dict]:
        return self._list_remote_rows()

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

    def buscar_aberta(self) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        rows = (
            client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .eq("status", "open")
            .order("start_time", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return dict(rows[0]) if rows else None

    def buscar_incompleta_por_data(self, work_date: str) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        rows = (
            client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .eq("work_date", str(work_date))
            .execute()
            .data
        )
        filtered = [dict(row) for row in (rows or []) if str(row.get("status", "")).lower() in {"partial", "open"}]
        filtered.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)
        return filtered[0] if filtered else None

    def buscar_ultima_fechada_antes(self, work_date: str, current_id: int | None = None) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        rows = (
            client.table(self.table_name)
            .select("*")
            .eq("user_id", int(user_id))
            .lt("work_date", str(work_date))
            .execute()
        )
        filtered = []
        for row in rows.data or []:
            status = str(row.get("status", "")).lower()
            if status not in {"closed", "adjusted", "manual"}:
                continue
            if current_id is not None and int(row.get("id", 0)) == int(current_id):
                continue
            filtered.append(dict(row))
        filtered.sort(key=lambda row: (str(row.get("work_date", "")), int(row.get("id", 0))), reverse=True)
        return filtered[0] if filtered else None

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
