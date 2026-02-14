"""Repository for investimentos persistence."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository, _to_db_record


class InvestimentosRepository(BaseRepository):
    """Data access for investimentos table."""

    table_name = "investimentos"
    columns = ["id", "data", "categoria", "aporte", "total aportado", "rendimento", "patrimonio total"]
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
    ) -> None:
        payload = _to_db_record(
            {
                "data": data,
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
            except Exception:
                # Backward compatibility for schemas without coluna categoria.
                fallback_payload = dict(payload)
                fallback_payload.pop("categoria", None)
                client.table(self.table_name).insert(fallback_payload).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
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
    ) -> None:
        payload = _to_db_record(
            {
                "data": data,
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
            except Exception:
                # Backward compatibility for schemas without coluna categoria.
                fallback_payload = dict(payload)
                fallback_payload.pop("categoria", None)
                client.table(self.table_name).update(fallback_payload).eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
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
        if "data" in work_df.columns:
            work_df["data"] = pd.to_datetime(work_df["data"], errors="coerce")
            work_df = work_df.sort_values(by=["data", "id"], ascending=[True, True])
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
