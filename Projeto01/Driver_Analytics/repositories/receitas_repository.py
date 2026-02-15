"""Repository for receitas persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import Receita
from repositories.base_repository import BaseRepository, _to_db_record


class ReceitasRepository(BaseRepository):
    """Data access for receitas table."""

    table_name = "receitas"
    columns = ["id", "data", "valor", "km", "tempo trabalhado", "observacao"]
    numeric_columns = ["id", "valor", "km", "tempo trabalhado"]

    def listar(self) -> pd.DataFrame:
        """List receitas as standardized dataframe."""

        client = self._supabase()
        if client:
            data = client.table(self.table_name).select("*").execute().data
            return self._normalize(pd.DataFrame(data))

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name}", conn)
        conn.close()
        return self._normalize(df)

    def buscar_por_id(self, item_id: int) -> pd.DataFrame:
        """Get receita by id as standardized dataframe."""

        client = self._supabase()
        if client:
            data = client.table(self.table_name).select("*").eq("id", item_id).execute().data
            return self._normalize(pd.DataFrame(data))

        conn = self._sqlite()
        df = pd.read_sql(f"SELECT * FROM {self.table_name} WHERE id = ?", conn, params=(item_id,))
        conn.close()
        return self._normalize(df)

    def inserir(self, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str = "") -> None:
        """Insert receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = _to_db_record(model.to_record())

        client = self._supabase()
        if client:
            client.table(self.table_name).insert(payload).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO receitas (data, valor, km, "tempo trabalhado", observacao)
            VALUES (?, ?, ?, ?, ?)
            """,
            (model.data, model.valor, model.km, model.tempo_trabalhado, model.observacao),
        )
        conn.commit()
        conn.close()

    def atualizar(self, item_id: int, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str) -> None:
        """Update receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = _to_db_record(model.to_record())

        client = self._supabase()
        if client:
            client.table(self.table_name).update(payload).eq("id", int(item_id)).execute()

            # Defensive verification: in some Supabase/RLS setups UPDATE can be silently ignored.
            check = client.table(self.table_name).select("*").eq("id", int(item_id)).limit(1).execute().data
            if not check:
                raise ValueError("Registro não encontrado para atualização no Supabase.")
            atual = self._normalize(pd.DataFrame(check)).iloc[0]
            ok = (
                str(atual.get("data", "")) == str(model.data)
                and abs(float(atual.get("valor", 0.0)) - float(model.valor)) < 1e-9
                and abs(float(atual.get("km", 0.0)) - float(model.km)) < 1e-9
                and int(atual.get("tempo trabalhado", 0)) == int(model.tempo_trabalhado)
                and str(atual.get("observacao", "")) == str(model.observacao)
            )
            if not ok:
                raise ValueError(
                    "Atualização não aplicada no Supabase. Verifique permissões de UPDATE (RLS/policies)."
                )
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE receitas
            SET data = ?, valor = ?, km = ?, "tempo trabalhado" = ?, observacao = ?
            WHERE id = ?
            """,
            (model.data, model.valor, model.km, model.tempo_trabalhado, model.observacao, int(item_id)),
        )
        conn.commit()
        conn.close()

    def deletar(self, item_id: int) -> None:
        """Delete receita by id."""

        client = self._supabase()
        if client:
            client.table(self.table_name).delete().eq("id", int(item_id)).execute()
            return

        conn = self._sqlite()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM receitas WHERE id = ?", (int(item_id),))
        conn.commit()
        conn.close()
