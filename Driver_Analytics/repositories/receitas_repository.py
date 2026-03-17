"""Repository for receitas persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import Receita
from repositories.base_repository import BaseRepository, _to_db_record


class ReceitasRepository(BaseRepository):
    """Data access for receitas table."""

    table_name = "receitas"
    columns = ["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"]
    numeric_columns = ["id", "valor", "km", "km_rodado_total", "tempo trabalhado"]

    @staticmethod
    def _legacy_payload(payload: dict) -> dict:
        out = dict(payload)
        out.pop("km_rodado_total", None)
        return out

    def listar(self) -> pd.DataFrame:
        """List receitas as standardized dataframe."""
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        """Get receita by id as standardized dataframe."""

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            query = client.table(self.table_name).select("*").eq("id", item_id).eq("user_id", int(user_id))
            data = query.execute().data
            return self._normalize(pd.DataFrame(data))
        raise RuntimeError("Supabase remoto indisponivel.")

    def inserir(
        self,
        data: str,
        valor: float,
        km: float = 0.0,
        tempo_trabalhado: int = 0,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        """Insert receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "km_rodado_total": km_rodado_total,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = self._with_user_id(_to_db_record(model.to_record()))

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
            except Exception:
                try:
                    client.table(self.table_name).insert(self._legacy_payload(payload)).execute()
                    return
                except Exception:
                    pass
            else:
                return
        raise RuntimeError("Supabase remoto indisponivel.")

    def atualizar(
        self,
        item_id: int,
        data: str,
        valor: float,
        km: float = 0.0,
        tempo_trabalhado: int = 0,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        """Update receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "km_rodado_total": km_rodado_total,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = self._with_user_id(_to_db_record(model.to_record()))

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            try:
                query = client.table(self.table_name).update(payload).eq("id", int(item_id)).eq("user_id", int(user_id))
                query.execute()
            except Exception:
                try:
                    query = client.table(self.table_name).update(self._legacy_payload(payload)).eq("id", int(item_id)).eq(
                        "user_id", int(user_id)
                    )
                    query.execute()
                except Exception:
                    pass

            # Defensive verification: in some Supabase/RLS setups UPDATE can be silently ignored.
            try:
                check_query = client.table(self.table_name).select("*").eq("id", int(item_id)).eq("user_id", int(user_id)).limit(1)
                check = check_query.execute().data
                if check:
                    atual = self._normalize(pd.DataFrame(check)).iloc[0]
                    has_km_total_col = "km_rodado_total" in atual.index
                    ok = (
                        str(atual.get("data", "")) == str(model.data)
                        and abs(float(atual.get("valor", 0.0)) - float(model.valor)) < 1e-9
                        and abs(float(atual.get("km", 0.0)) - float(model.km)) < 1e-9
                        and (
                            not has_km_total_col
                            or abs(float(atual.get("km_rodado_total", 0.0)) - float(km_rodado_total)) < 1e-9
                        )
                        and int(atual.get("tempo trabalhado", 0)) == int(model.tempo_trabalhado)
                        and str(atual.get("observacao", "")) == str(model.observacao)
                    )
                    if ok:
                        return
            except Exception:
                pass
        raise RuntimeError("Falha ao atualizar receita no Supabase.")

    def deletar(self, item_id: int) -> None:
        """Delete receita by id."""

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            query = client.table(self.table_name).delete().eq("id", int(item_id)).eq("user_id", int(user_id))
            query.execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")
