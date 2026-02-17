"""Repository for despesas persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import Despesa
from repositories.base_repository import BaseRepository


class DespesasRepository(BaseRepository):
    """Data access for despesas table."""

    table_name = "despesas"
    columns = ["id", "data", "categoria", "valor", "observacao", "tipo_despesa", "subcategoria_fixa", "esfera_despesa", "litros"]
    numeric_columns = ["id", "valor", "litros"]

    @staticmethod
    def _legacy_payload(payload: dict) -> dict:
        out = dict(payload)
        out.pop("tipo_despesa", None)
        out.pop("subcategoria_fixa", None)
        out.pop("esfera_despesa", None)
        out.pop("litros", None)
        return out

    def listar(self) -> pd.DataFrame:
        """List despesas as standardized dataframe."""

        client = self._supabase()
        if client:
            data = client.table(self.table_name).select("*").execute().data
            return self._normalize(pd.DataFrame(data))

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        """Get despesa by id as standardized dataframe."""

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
        valor: float,
        observacao: str = "",
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
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
            }
        )
        payload = model.to_record()

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
            except Exception:
                client.table(self.table_name).insert(self._legacy_payload(payload)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO despesas (data, categoria, valor, observacao, tipo_despesa, subcategoria_fixa, esfera_despesa, litros)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model.data,
                model.categoria,
                model.valor,
                model.observacao,
                model.tipo_despesa,
                model.subcategoria_fixa,
                model.esfera_despesa,
                model.litros,
            ),
        )
        conn.commit()
        conn.close()

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
            }
        )
        payload = model.to_record()

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).update(payload).eq("id", int(item_id)).execute()
            except Exception:
                client.table(self.table_name).update(self._legacy_payload(payload)).eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE despesas
            SET data = ?, categoria = ?, valor = ?, observacao = ?, tipo_despesa = ?, subcategoria_fixa = ?, esfera_despesa = ?, litros = ?
            WHERE id = ?
            """,
            (
                model.data,
                model.categoria,
                model.valor,
                model.observacao,
                model.tipo_despesa,
                model.subcategoria_fixa,
                model.esfera_despesa,
                model.litros,
                int(item_id),
            ),
        )
        conn.commit()
        conn.close()

    def deletar(self, item_id: int) -> None:
        """Delete despesa by id."""

        client = self._supabase()
        if client:
            client.table(self.table_name).delete().eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM despesas WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
