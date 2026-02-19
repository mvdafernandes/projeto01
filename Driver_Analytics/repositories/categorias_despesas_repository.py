"""Repository for expense categories."""

from __future__ import annotations

import pandas as pd

from repositories.base_repository import BaseRepository


class CategoriasDespesasRepository(BaseRepository):
    """Data access for categorias_despesas table."""

    table_name = "categorias_despesas"
    columns = ["id", "nome"]
    numeric_columns = ["id"]

    def listar(self) -> pd.DataFrame:
        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).select("*")
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                data = query.order("nome").execute().data
                return self._normalize(pd.DataFrame(data))
            except Exception:
                return self._normalize(pd.DataFrame())

        conn = self._sqlite()
        if user_id is not None:
            df = pd.read_sql(f"SELECT * FROM {self.table_name} WHERE user_id = ? ORDER BY nome", conn, params=(int(user_id),))
        else:
            df = pd.read_sql(f"SELECT * FROM {self.table_name} ORDER BY nome", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_nome(self, nome: str) -> pd.DataFrame:
        normalized = str(nome).strip()
        if not normalized:
            return pd.DataFrame(columns=self.columns)

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).select("*").ilike("nome", normalized)
                if user_id is not None:
                    query = query.eq("user_id", int(user_id))
                data = query.execute().data
                df = self._normalize(pd.DataFrame(data))
                if df.empty:
                    return df
                return df[df["nome"].astype(str).str.casefold() == normalized.casefold()]
            except Exception:
                return self._normalize(pd.DataFrame())

        conn = self._sqlite()
        if user_id is not None:
            df = pd.read_sql(
                f"SELECT * FROM {self.table_name} WHERE lower(nome) = lower(?) AND user_id = ?",
                conn,
                params=(normalized, int(user_id)),
            )
        else:
            df = pd.read_sql(
                f"SELECT * FROM {self.table_name} WHERE lower(nome) = lower(?)",
                conn,
                params=(normalized,),
            )
        conn.close()
        return self._normalize(df)

    def inserir(self, nome: str) -> None:
        normalized = str(nome).strip()
        if not normalized:
            return

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                payload = {"nome": normalized}
                if user_id is not None:
                    payload["user_id"] = int(user_id)
                client.table(self.table_name).insert(payload).execute()
            except Exception:
                # If migration was not executed yet, keep app running and allow free-text fallback.
                return
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute(
                f"INSERT OR IGNORE INTO {self.table_name} (user_id, nome) VALUES (?, ?)",
                (int(user_id), normalized),
            )
        else:
            cursor.execute(
                f"INSERT OR IGNORE INTO {self.table_name} (nome) VALUES (?)",
                (normalized,),
            )
        conn.commit()
        conn.close()
