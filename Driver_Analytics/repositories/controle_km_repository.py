"""Repository for controle_km persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import ControleKM
from repositories.base_repository import BaseRepository


class ControleKMRepository(BaseRepository):
    """Data access for controle_km table."""

    table_name = "controle_km"
    columns = ["id", "data_inicio", "data_fim", "km_total_rodado"]
    numeric_columns = ["id", "km_total_rodado"]

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

    def inserir(self, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        model = ControleKM.from_raw({"data_inicio": data_inicio, "data_fim": data_fim, "km_total_rodado": km_total_rodado})
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
            INSERT INTO controle_km (user_id, data_inicio, data_fim, km_total_rodado)
            VALUES (?, ?, ?, ?)
            """,
            (self._current_user_id(), model.data_inicio, model.data_fim, model.km_total_rodado),
        )
        conn.commit()
        conn.close()

    def atualizar(self, item_id: int, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        model = ControleKM.from_raw({"data_inicio": data_inicio, "data_fim": data_fim, "km_total_rodado": km_total_rodado})
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
                UPDATE controle_km
                SET data_inicio = ?, data_fim = ?, km_total_rodado = ?
                WHERE id = ? AND user_id = ?
                """,
                (model.data_inicio, model.data_fim, model.km_total_rodado, int(item_id), int(user_id)),
            )
        else:
            cursor.execute(
                """
                UPDATE controle_km
                SET data_inicio = ?, data_fim = ?, km_total_rodado = ?
                WHERE id = ?
                """,
                (model.data_inicio, model.data_fim, model.km_total_rodado, int(item_id)),
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
            cursor.execute("DELETE FROM controle_km WHERE id = ? AND user_id = ?", (int(item_id), int(user_id)))
        else:
            cursor.execute("DELETE FROM controle_km WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
