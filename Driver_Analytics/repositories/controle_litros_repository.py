"""Repository for controle_litros persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import ControleLitros
from repositories.base_repository import BaseRepository


class ControleLitrosRepository(BaseRepository):
    """Data access for controle_litros table."""

    table_name = "controle_litros"
    columns = ["id", "data", "litros"]
    numeric_columns = ["id", "litros"]

    def listar(self) -> pd.DataFrame:
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
                pass

        conn = self._sqlite()
        if user_id is not None:
            df = pd.read_sql(f"SELECT * FROM {self.table_name} WHERE user_id = ?", conn, params=(int(user_id),))
        else:
            df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
        conn.close()
        return self._normalize(df)

    def inserir(self, data: str, litros: float) -> None:
        model = ControleLitros.from_raw({"data": data, "litros": litros})
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).insert(payload).execute()
                return
            except Exception:
                pass

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO controle_litros (user_id, data, litros)
            VALUES (?, ?, ?)
            """,
            (self._current_user_id(), model.data, model.litros),
        )
        conn.commit()
        conn.close()

    def atualizar(self, item_id: int, data: str, litros: float) -> None:
        model = ControleLitros.from_raw({"data": data, "litros": litros})
        payload = self._with_user_id(model.to_record())

        client = self._supabase()
        user_id = self._current_user_id()
        if client:
            try:
                query = client.table(self.table_name).update(payload).eq("id", int(item_id))
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
                UPDATE controle_litros
                SET data = ?, litros = ?
                WHERE id = ? AND user_id = ?
                """,
                (model.data, model.litros, int(item_id), int(user_id)),
            )
        else:
            cursor.execute(
                """
                UPDATE controle_litros
                SET data = ?, litros = ?
                WHERE id = ?
                """,
                (model.data, model.litros, int(item_id)),
            )
        conn.commit()
        conn.close()

    def deletar(self, item_id: int) -> None:
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
            cursor.execute("DELETE FROM controle_litros WHERE id = ? AND user_id = ?", (int(item_id), int(user_id)))
        else:
            cursor.execute("DELETE FROM controle_litros WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
