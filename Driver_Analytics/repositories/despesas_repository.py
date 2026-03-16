"""Repository for despesas persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import Despesa
from repositories.base_repository import BaseRepository


class DespesasRepository(BaseRepository):
    """Data access for despesas table."""

    table_name = "despesas"
    columns = [
        "id",
        "data",
        "categoria",
        "valor",
        "observacao",
        "tipo_despesa",
        "subcategoria_fixa",
        "esfera_despesa",
        "litros",
        "recorrencia_tipo",
        "recorrencia_meses",
        "recorrencia_serie_id",
    ]
    numeric_columns = ["id", "valor", "litros", "recorrencia_meses"]

    @staticmethod
    def _legacy_payload(payload: dict) -> dict:
        out = dict(payload)
        out.pop("tipo_despesa", None)
        out.pop("subcategoria_fixa", None)
        out.pop("esfera_despesa", None)
        out.pop("litros", None)
        out.pop("recorrencia_tipo", None)
        out.pop("recorrencia_meses", None)
        out.pop("recorrencia_serie_id", None)
        return out

    def listar(self) -> pd.DataFrame:
        """List despesas as standardized dataframe."""
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        """Get despesa by id as standardized dataframe."""

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
        categoria: str,
        valor: float,
        observacao: str = "",
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
        recorrencia_tipo: str = "",
        recorrencia_meses: int = 0,
        recorrencia_serie_id: str = "",
    ) -> None:
        """Insert despesa."""

        model = Despesa.from_raw(
            {
                "data": data,
                "categoria": categoria,
                "valor": valor,
                "observacao": observacao,
                "tipo_despesa": tipo_despesa,
                "subcategoria_fixa": subcategoria_fixa,
                "esfera_despesa": esfera_despesa,
                "litros": litros,
                "recorrencia_tipo": recorrencia_tipo,
                "recorrencia_meses": recorrencia_meses,
                "recorrencia_serie_id": recorrencia_serie_id,
            }
        )
        payload = self._with_user_id(model.to_record())

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
        categoria: str,
        valor: float,
        observacao: str,
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
        recorrencia_tipo: str = "",
        recorrencia_meses: int = 0,
        recorrencia_serie_id: str = "",
    ) -> None:
        """Update despesa."""

        model = Despesa.from_raw(
            {
                "data": data,
                "categoria": categoria,
                "valor": valor,
                "observacao": observacao,
                "tipo_despesa": tipo_despesa,
                "subcategoria_fixa": subcategoria_fixa,
                "esfera_despesa": esfera_despesa,
                "litros": litros,
                "recorrencia_tipo": recorrencia_tipo,
                "recorrencia_meses": recorrencia_meses,
                "recorrencia_serie_id": recorrencia_serie_id,
            }
        )
        payload = self._with_user_id(model.to_record())

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
                    return
                except Exception:
                    pass
        raise RuntimeError("Falha ao atualizar despesa no Supabase.")

    def deletar(self, item_id: int) -> None:
        """Delete despesa by id."""

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            query = client.table(self.table_name).delete().eq("id", int(item_id)).eq("user_id", int(user_id))
            query.execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")
