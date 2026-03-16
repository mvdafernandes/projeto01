"""Repository for work_day_events persistence."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository, normalize_dataframe


class WorkDayEventsRepository(BaseRepository):
    """Data access for work_day_events table."""

    table_name = "work_day_events"
    columns = [
        "id",
        "work_day_id",
        "event_type",
        "event_timestamp",
        "km_value",
        "old_value",
        "new_value",
        "notes",
        "created_at",
    ]
    numeric_columns = ["id", "work_day_id", "km_value"]

    def _normalize(self, df: pd.DataFrame | None) -> pd.DataFrame:
        return normalize_dataframe(df, self.columns, self.numeric_columns)

    def listar_por_work_day(self, work_day_id: int) -> pd.DataFrame:
        client = self._supabase()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        data = (
            client.table(self.table_name)
            .select("*")
            .eq("work_day_id", int(work_day_id))
            .order("event_timestamp", desc=True)
            .execute()
            .data
            or []
        )
        return self._normalize(pd.DataFrame(data))

    def inserir(self, payload: dict) -> dict:
        client = self._supabase()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        data = client.table(self.table_name).insert(payload).execute().data or []
        return dict(data[0]) if data else {}
