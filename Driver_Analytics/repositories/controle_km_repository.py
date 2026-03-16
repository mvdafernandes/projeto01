"""Repository for controle_km persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import ControleKM
from repositories.base_repository import BaseRepository


class ControleKMRepository(BaseRepository):
    """Data access for controle_km table."""

    table_name = "controle_km"
    columns = ["id", "data_inicio", "data_fim", "km_total_rodado"]
    numeric_columns = ["id", "km_total_rodado"]

    def listar(self) -> pd.DataFrame:
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def inserir(self, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        model = ControleKM.from_raw({"data_inicio": data_inicio, "data_fim": data_fim, "km_total_rodado": km_total_rodado})
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
                return
            except Exception:
                pass
        raise RuntimeError("Supabase remoto indisponivel.")

    def atualizar(self, item_id: int, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        model = ControleKM.from_raw({"data_inicio": data_inicio, "data_fim": data_fim, "km_total_rodado": km_total_rodado})
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            try:
                query = client.table(self.table_name).update(payload).eq("id", int(item_id)).eq("user_id", int(user_id))
                query.execute()
                return
            except Exception:
                pass
        raise RuntimeError("Falha ao atualizar controle_km no Supabase.")

    def deletar(self, item_id: int) -> None:
        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            try:
                query = client.table(self.table_name).delete().eq("id", int(item_id)).eq("user_id", int(user_id))
                query.execute()
                return
            except Exception:
                pass
        raise RuntimeError("Supabase remoto indisponivel.")
