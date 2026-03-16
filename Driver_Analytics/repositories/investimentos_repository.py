"""Repository for investimentos persistence."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository, _to_db_record


class InvestimentosRepository(BaseRepository):
    """Data access for investimentos table."""

    table_name = "investimentos"
    columns = [
        "id",
        "data",
        "data_inicio",
        "data_fim",
        "tipo_movimentacao",
        "categoria",
        "aporte",
        "total aportado",
        "rendimento",
        "patrimonio total",
    ]
    numeric_columns = ["id", "aporte", "total aportado", "rendimento", "patrimonio total"]

    def listar(self) -> pd.DataFrame:
        data = self._list_remote_rows()
        return self._normalize(pd.DataFrame(data))

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
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
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        data_ini = str(data_inicio or data)
        data_end = str(data_fim or data)
        tipo = str(tipo_movimentacao or "").strip()
        payload = self._with_user_id(
            _to_db_record(
            {
                "data": data,
                "data_inicio": data_ini,
                "data_fim": data_end,
                "tipo_movimentacao": tipo,
                "categoria": str(categoria).strip(),
                "aporte": float(aporte),
                "total aportado": float(total_aportado),
                "rendimento": float(rendimento),
                "patrimonio total": float(patrimonio_total),
            }
            )
        )

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
            except Exception as exc:
                # Backward compatibility: only fallback for missing-column schemas.
                msg = str(exc).lower()
                missing_col_error = "column" in msg and "does not exist" in msg
                if not missing_col_error:
                    raise

                fallback_payload = dict(payload)
                for col in ["data_inicio", "data_fim", "tipo_movimentacao", "categoria"]:
                    if col in msg:
                        fallback_payload.pop(col, None)
                if fallback_payload == payload:
                        fallback_payload.pop("categoria", None)
                client.table(self.table_name).insert(fallback_payload).execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")

    def atualizar(
        self,
        item_id: int,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        data_ini = str(data_inicio or data)
        data_end = str(data_fim or data)
        tipo = str(tipo_movimentacao or "").strip()
        payload = self._with_user_id(
            _to_db_record(
            {
                "data": data,
                "data_inicio": data_ini,
                "data_fim": data_end,
                "tipo_movimentacao": tipo,
                "categoria": str(categoria).strip(),
                "aporte": float(aporte),
                "total aportado": float(total_aportado),
                "rendimento": float(rendimento),
                "patrimonio total": float(patrimonio_total),
            }
            )
        )

        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            try:
                query = client.table(self.table_name).update(payload).eq("id", int(item_id)).eq("user_id", int(user_id))
                query.execute()
            except Exception as exc:
                # Backward compatibility: only fallback for missing-column schemas.
                msg = str(exc).lower()
                missing_col_error = "column" in msg and "does not exist" in msg
                if not missing_col_error:
                    raise

                fallback_payload = dict(payload)
                for col in ["data_inicio", "data_fim", "tipo_movimentacao", "categoria"]:
                    if col in msg:
                        fallback_payload.pop(col, None)
                if fallback_payload == payload:
                    fallback_payload.pop("categoria", None)
                query = client.table(self.table_name).update(fallback_payload).eq("id", int(item_id)).eq("user_id", int(user_id))
                query.execute()
            return
        raise RuntimeError("Falha ao atualizar investimento no Supabase.")

    def deletar(self, item_id: int) -> None:
        client = self._supabase()
        user_id = self._require_user_id()
        if client:
            query = client.table(self.table_name).delete().eq("id", int(item_id)).eq("user_id", int(user_id))
            query.execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")

    def recalcular_total_aportado(self) -> None:
        df = self.listar()
        if df.empty:
            return

        work_df = df.copy()
        if "data_fim" in work_df.columns:
            work_df["data_ref"] = pd.to_datetime(work_df["data_fim"], errors="coerce")
        else:
            work_df["data_ref"] = pd.to_datetime(work_df.get("data"), errors="coerce")
        work_df = work_df.sort_values(by=["data_ref", "id"], ascending=[True, True])
        work_df["aporte"] = pd.to_numeric(work_df["aporte"], errors="coerce").fillna(0.0)
        work_df["total aportado"] = work_df["aporte"].cumsum()

        client = self._supabase()
        if client:
            user_id = self._require_user_id()
            for _, row in work_df.iterrows():
                client.table(self.table_name).update({"total_aportado": float(row["total aportado"])}).eq("id", int(row["id"])).eq(
                    "user_id", int(user_id)
                ).execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")

    def recalcular_patrimonio_total(self) -> None:
        """Rebuild patrimonio total as cumulative sum of aporte + rendimento ordered by data/id."""

        df = self.listar()
        if df.empty:
            return

        work_df = df.copy()
        if "data_fim" in work_df.columns:
            work_df["data_ref"] = pd.to_datetime(work_df["data_fim"], errors="coerce")
        else:
            work_df["data_ref"] = pd.to_datetime(work_df.get("data"), errors="coerce")
        work_df = work_df.sort_values(by=["data_ref", "id"], ascending=[True, True])
        work_df["aporte"] = pd.to_numeric(work_df["aporte"], errors="coerce").fillna(0.0)
        work_df["rendimento"] = pd.to_numeric(work_df["rendimento"], errors="coerce").fillna(0.0)

        patrimonio = 0.0
        valores = []
        for _, row in work_df.iterrows():
            patrimonio += float(row["aporte"]) + float(row["rendimento"])
            valores.append(max(0.0, patrimonio))
        work_df["patrimonio total"] = valores

        client = self._supabase()
        if client:
            user_id = self._require_user_id()
            for _, row in work_df.iterrows():
                client.table(self.table_name).update({"patrimonio_total": float(row["patrimonio total"])}).eq("id", int(row["id"])).eq(
                    "user_id", int(user_id)
                ).execute()
            return
        raise RuntimeError("Supabase remoto indisponivel.")
