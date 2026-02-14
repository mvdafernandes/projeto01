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
        client = self._supabase()
        if client:
            data = client.table(self.table_name).select("*").execute().data
            return self._normalize(pd.DataFrame(data))

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        client = self._supabase()
        if client:
            data = client.table(self.table_name).select("*").eq("id", item_id).execute().data
            return self._normalize(pd.DataFrame(data))

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name} WHERE id = ?", conn, params=(item_id,))
        conn.close()
        return self._normalize(df)

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
        payload = _to_db_record(
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

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
            except Exception as exc:
                # Backward compatibility: only fallback for missing-column schemas.
                msg = str(exc).lower()
                missing_col_error = "column" in msg and ("does not exist" in msg or "schema cache" in msg)
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

        conn = self._sqlite()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO investimentos (
                    data, data_inicio, data_fim, tipo_movimentacao, categoria, aporte,
                    "total aportado", rendimento, "patrimonio total"
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data,
                    data_ini,
                    data_end,
                    tipo,
                    str(categoria).strip(),
                    float(aporte),
                    float(total_aportado),
                    float(rendimento),
                    float(patrimonio_total),
                ),
            )
        except Exception:
            cursor.execute(
                """
                INSERT INTO investimentos (data, categoria, aporte, "total aportado", rendimento, "patrimonio total")
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (data, str(categoria).strip(), float(aporte), float(total_aportado), float(rendimento), float(patrimonio_total)),
            )
        conn.commit()
        conn.close()

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
        payload = _to_db_record(
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

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).update(payload).eq("id", int(item_id)).execute()
            except Exception as exc:
                # Backward compatibility: only fallback for missing-column schemas.
                msg = str(exc).lower()
                missing_col_error = "column" in msg and ("does not exist" in msg or "schema cache" in msg)
                if not missing_col_error:
                    raise

                fallback_payload = dict(payload)
                for col in ["data_inicio", "data_fim", "tipo_movimentacao", "categoria"]:
                    if col in msg:
                        fallback_payload.pop(col, None)
                if fallback_payload == payload:
                    fallback_payload.pop("categoria", None)
                client.table(self.table_name).update(fallback_payload).eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE investimentos
                SET data = ?, data_inicio = ?, data_fim = ?, tipo_movimentacao = ?, categoria = ?,
                    aporte = ?, "total aportado" = ?, rendimento = ?, "patrimonio total" = ?
                WHERE id = ?
                """,
                (
                    data,
                    data_ini,
                    data_end,
                    tipo,
                    str(categoria).strip(),
                    float(aporte),
                    float(total_aportado),
                    float(rendimento),
                    float(patrimonio_total),
                    int(item_id),
                ),
            )
        except Exception:
            cursor.execute(
                """
                UPDATE investimentos
                SET data = ?, categoria = ?, aporte = ?, "total aportado" = ?, rendimento = ?, "patrimonio total" = ?
                WHERE id = ?
                """,
                (data, str(categoria).strip(), float(aporte), float(total_aportado), float(rendimento), float(patrimonio_total), int(item_id)),
            )
        conn.commit()
        conn.close()

    def deletar(self, item_id: int) -> None:
        client = self._supabase()
        if client:
            client.table(self.table_name).delete().eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM investimentos WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()

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
            for _, row in work_df.iterrows():
                client.table(self.table_name).update({"total_aportado": float(row["total aportado"])}).eq(
                    "id", int(row["id"])
                ).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        for _, row in work_df.iterrows():
            cursor.execute(
                'UPDATE investimentos SET "total aportado" = ? WHERE id = ?',
                (float(row["total aportado"]), int(row["id"])),
            )
        conn.commit()
        conn.close()

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
            for _, row in work_df.iterrows():
                client.table(self.table_name).update({"patrimonio_total": float(row["patrimonio total"])}).eq(
                    "id", int(row["id"])
                ).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        for _, row in work_df.iterrows():
            cursor.execute(
                'UPDATE investimentos SET "patrimonio total" = ? WHERE id = ?',
                (float(row["patrimonio total"]), int(row["id"])),
            )
        conn.commit()
        conn.close()
