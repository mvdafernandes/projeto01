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
        if client:
            try:
                data = client.table(self.table_name).select("*").order("nome").execute().data
                return self._normalize(pd.DataFrame(data))
            except Exception:
                return self._normalize(pd.DataFrame())

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name} ORDER BY nome", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_nome(self, nome: str) -> pd.DataFrame:
        normalized = str(nome).strip()
        if not normalized:
            return pd.DataFrame(columns=self.columns)

        client = self._supabase()
        if client:
            try:
                data = client.table(self.table_name).select("*").ilike("nome", normalized).execute().data
                df = self._normalize(pd.DataFrame(data))
                if df.empty:
                    return df
                return df[df["nome"].astype(str).str.casefold() == normalized.casefold()]
            except Exception:
                return self._normalize(pd.DataFrame())

        conn = self._sqlite()
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
        if client:
            try:
                client.table(self.table_name).insert({"nome": normalized}).execute()
            except Exception:
                # If migration was not executed yet, keep app running and allow free-text fallback.
                return
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT OR IGNORE INTO {self.table_name} (nome) VALUES (?)",
            (normalized,),
        )
        conn.commit()
        conn.close()
