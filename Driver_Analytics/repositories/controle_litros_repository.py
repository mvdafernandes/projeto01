"""Repository for controle_litros persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import ControleLitros
from repositories.base_repository import BaseRepository


class ControleLitrosRepository(BaseRepository):
    """Data access for controle_litros table."""

    table_name = "controle_litros"
    columns = ["id", "data", "litros", "odometro", "valor_total", "tanque_cheio", "tipo_combustivel", "observacao"]
    numeric_columns = ["id", "litros", "odometro", "valor_total"]

    def listar(self) -> pd.DataFrame:
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def inserir(
        self,
        data: str,
        litros: float,
        odometro: float | None = None,
        valor_total: float = 0.0,
        tanque_cheio: bool = False,
        tipo_combustivel: str = "",
        observacao: str = "",
    ) -> None:
        model = ControleLitros.from_raw(
            {
                "data": data,
                "litros": litros,
                "odometro": odometro,
                "valor_total": valor_total,
                "tanque_cheio": tanque_cheio,
                "tipo_combustivel": tipo_combustivel,
                "observacao": observacao,
            }
        )
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
                return
            except Exception:
                pass
        raise RuntimeError("Supabase remoto indisponivel.")

    def atualizar(
        self,
        item_id: int,
        data: str,
        litros: float,
        odometro: float | None = None,
        valor_total: float = 0.0,
        tanque_cheio: bool = False,
        tipo_combustivel: str = "",
        observacao: str = "",
    ) -> None:
        model = ControleLitros.from_raw(
            {
                "data": data,
                "litros": litros,
                "odometro": odometro,
                "valor_total": valor_total,
                "tanque_cheio": tanque_cheio,
                "tipo_combustivel": tipo_combustivel,
                "observacao": observacao,
            }
        )
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
        raise RuntimeError("Falha ao atualizar controle_litros no Supabase.")

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
