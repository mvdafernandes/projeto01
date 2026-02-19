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
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).select("*")
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                data = query.execute().data
                return self._normalize(pd.DataFrame(data))
            except Exception:
                # Fallback for legacy schemas/RLS setups without user_id support.
                try:
                    data = client.table(self.table_name).select("*").execute().data
                    return self._normalize(pd.DataFrame(data))
                except Exception:
                    pass

        conn = self._sqlite()
        if user_id is not None:
            df = pd.read_sql(f"SELECT * FROM {self.table_name} WHERE user_id = ?", conn, params=(int(user_id),))
        else:
            df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        """Get despesa by id as standardized dataframe."""

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).select("*").eq("id", item_id)
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                data = query.execute().data
                return self._normalize(pd.DataFrame(data))
            except Exception:
                try:
                    data = client.table(self.table_name).select("*").eq("id", item_id).execute().data
                    return self._normalize(pd.DataFrame(data))
                except Exception:
                    pass

        conn = self._sqlite()
        if user_id is not None:
            df = pd.read_sql(
                f"SELECT * FROM {self.table_name} WHERE id = ? AND user_id = ?",
                conn,
                params=(item_id, int(user_id)),
            )
        else:
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

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO despesas (user_id, data, categoria, valor, observacao, tipo_despesa, subcategoria_fixa, esfera_despesa, litros)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._current_user_id(),
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
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).update(payload).eq("id", int(item_id))
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                query.execute()
            except Exception:
                try:
                    query = client.table(self.table_name).update(self._legacy_payload(payload)).eq("id", int(item_id))
                    if user_id is not None:
                        query = query.eq("user_id", int(user_id))
                    query.execute()
                    return
                except Exception:
                    pass

        conn = self._sqlite()
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute(
                """
                UPDATE despesas
                SET data = ?, categoria = ?, valor = ?, observacao = ?, tipo_despesa = ?, subcategoria_fixa = ?, esfera_despesa = ?, litros = ?
                WHERE id = ? AND user_id = ?
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
                    int(user_id),
                ),
            )
        else:
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
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).delete().eq("id", int(item_id))
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                query.execute()
                return
            except Exception:
                pass

        conn = self._sqlite()
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("DELETE FROM despesas WHERE id = ? AND user_id = ?", (int(item_id), int(user_id)))
        else:
            cursor.execute("DELETE FROM despesas WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
