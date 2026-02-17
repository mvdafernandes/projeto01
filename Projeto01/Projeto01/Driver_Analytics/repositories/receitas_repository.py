"""Repository for receitas persistence."""

from __future__ import annotations

import pandas as pd

from domain.models import Receita
from repositories.base_repository import BaseRepository, _to_db_record


class ReceitasRepository(BaseRepository):
    """Data access for receitas table."""

    table_name = "receitas"
    columns = ["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"]
    numeric_columns = ["id", "valor", "km", "km_rodado_total", "tempo trabalhado"]

    @staticmethod
    def _legacy_payload(payload: dict) -> dict:
        out = dict(payload)
        out.pop("km_rodado_total", None)
        return out

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

    def inserir(
        self,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        """Insert receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "km_rodado_total": km_rodado_total,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = _to_db_record(model.to_record())

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
            INSERT INTO receitas (data, valor, km, km_rodado_total, "tempo trabalhado", observacao)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (model.data, model.valor, model.km, float(km_rodado_total), model.tempo_trabalhado, model.observacao),
        )
        conn.commit()
        conn.close()

    def atualizar(
        self,
        item_id: int,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        observacao: str,
        km_rodado_total: float = 0.0,
    ) -> None:
        """Update receita."""

        model = Receita.from_raw(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "km_rodado_total": km_rodado_total,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        payload = _to_db_record(model.to_record())

        client = self._supabase()
        if client:
            try:
                client.table(self.table_name).update(payload).eq("id", int(item_id)).execute()
            except Exception:
                client.table(self.table_name).update(self._legacy_payload(payload)).eq("id", int(item_id)).execute()

            # Defensive verification: in some Supabase/RLS setups UPDATE can be silently ignored.
            check = client.table(self.table_name).select("*").eq("id", int(item_id)).limit(1).execute().data
            if not check:
                raise ValueError("Registro não encontrado para atualização no Supabase.")
            atual = self._normalize(pd.DataFrame(check)).iloc[0]
            has_km_total_col = "km_rodado_total" in atual.index
            ok = (
                str(atual.get("data", "")) == str(model.data)
                and abs(float(atual.get("valor", 0.0)) - float(model.valor)) < 1e-9
                and abs(float(atual.get("km", 0.0)) - float(model.km)) < 1e-9
                and (not has_km_total_col or abs(float(atual.get("km_rodado_total", 0.0)) - float(km_rodado_total)) < 1e-9)
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
            SET data = ?, valor = ?, km = ?, km_rodado_total = ?, "tempo trabalhado" = ?, observacao = ?
            WHERE id = ?
            """,
            (model.data, model.valor, model.km, float(km_rodado_total), model.tempo_trabalhado, model.observacao, int(item_id)),
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
