"""Application service orchestrating repositories and metrics."""

from __future__ import annotations

import pandas as pd

from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.despesas_repository import DespesasRepository
from repositories.investimentos_repository import InvestimentosRepository
from repositories.receitas_repository import ReceitasRepository
from services.metrics_service import MetricsService


class DashboardService:
    """Facade service consumed by Streamlit UI pages."""

    def __init__(self) -> None:
        self.receitas_repo = ReceitasRepository()
        self.despesas_repo = DespesasRepository()
        self.investimentos_repo = InvestimentosRepository()
        self.categorias_repo = CategoriasDespesasRepository()
        self.metrics = MetricsService()

    @staticmethod
    def _to_date_str(value) -> str:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return ""
        return parsed.date().isoformat()

    @staticmethod
    def _to_float(value) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _normalize_title(value: str) -> str:
        return " ".join(str(value).strip().split()).title()

    def listar_categorias_despesas(self) -> list[str]:
        """Return normalized list of expense categories."""

        df = self.categorias_repo.listar()
        if df.empty or "nome" not in df.columns:
            return []
        values = [self._normalize_title(v) for v in df["nome"].dropna().astype(str).tolist() if str(v).strip()]
        return sorted(set(values))

    def garantir_categoria_despesa(self, nome: str) -> str:
        """Ensure category exists and return normalized display value."""

        normalized = self._normalize_title(nome)
        if not normalized:
            raise ValueError("Informe uma categoria válida.")

        existentes = {v.casefold(): v for v in self.listar_categorias_despesas()}
        if normalized.casefold() not in existentes:
            self.categorias_repo.inserir(normalized)
        return normalized

    def _receita_duplicada(
        self,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_receitas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        df_cmp["km_cmp"] = pd.to_numeric(df_cmp["km"], errors="coerce").fillna(0.0)
        df_cmp["tempo_cmp"] = pd.to_numeric(df_cmp["tempo trabalhado"], errors="coerce").fillna(0).astype(int)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["valor_cmp"] == self._to_float(valor))
            & (df_cmp["km_cmp"] == self._to_float(km))
            & (df_cmp["tempo_cmp"] == self._to_int(tempo_trabalhado))
        ).any()

    def _despesa_duplicada(self, data: str, categoria: str, valor: float, ignore_id: int | None = None) -> bool:
        df = self.listar_despesas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["valor_cmp"] == self._to_float(valor))
        ).any()

    def _investimento_duplicado(
        self,
        data: str,
        categoria: str,
        aporte: float,
        rendimento: float,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_investimentos()
        if df.empty:
            return False
        df_cmp = df.copy()
        if "categoria" not in df_cmp.columns:
            df_cmp["categoria"] = "Renda Fixa"
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["aporte_cmp"] = pd.to_numeric(df_cmp["aporte"], errors="coerce").fillna(0.0)
        df_cmp["rendimento_cmp"] = pd.to_numeric(df_cmp["rendimento"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["aporte_cmp"] == self._to_float(aporte))
            & (df_cmp["rendimento_cmp"] == self._to_float(rendimento))
        ).any()

    def listar_receitas(self) -> pd.DataFrame:
        return self.receitas_repo.listar()

    def listar_despesas(self) -> pd.DataFrame:
        return self.despesas_repo.listar()

    def listar_investimentos(self) -> pd.DataFrame:
        return self.investimentos_repo.listar()

    def criar_receita(self, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str = "") -> None:
        if self._receita_duplicada(data, valor, km, tempo_trabalhado):
            raise ValueError("Registro já existente.")
        self.receitas_repo.inserir(data, valor, km, tempo_trabalhado, observacao)

    def atualizar_receita(self, item_id: int, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str) -> None:
        if self._receita_duplicada(data, valor, km, tempo_trabalhado, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.receitas_repo.atualizar(item_id, data, valor, km, tempo_trabalhado, observacao)

    def deletar_receita(self, item_id: int) -> None:
        self.receitas_repo.deletar(item_id)

    def criar_despesa(self, data: str, categoria: str, valor: float, observacao: str = "") -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        if self._despesa_duplicada(data, categoria_ok, valor):
            raise ValueError("Registro já existente.")
        self.despesas_repo.inserir(data, categoria_ok, valor, observacao)

    def atualizar_despesa(self, item_id: int, data: str, categoria: str, valor: float, observacao: str) -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        if self._despesa_duplicada(data, categoria_ok, valor, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.despesas_repo.atualizar(item_id, data, categoria_ok, valor, observacao)

    def deletar_despesa(self, item_id: int) -> None:
        self.despesas_repo.deletar(item_id)

    def criar_investimento(
        self,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.inserir(data, categoria_ok, aporte, total_aportado, rendimento, patrimonio_total)
        self.investimentos_repo.recalcular_total_aportado()

    def atualizar_investimento(
        self,
        item_id: int,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.atualizar(item_id, data, categoria_ok, aporte, total_aportado, rendimento, patrimonio_total)
        self.investimentos_repo.recalcular_total_aportado()

    def deletar_investimento(self, item_id: int) -> None:
        self.investimentos_repo.deletar(item_id)
        self.investimentos_repo.recalcular_total_aportado()

    def recalcular_total_aportado(self) -> None:
        self.investimentos_repo.recalcular_total_aportado()

    def resumo_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> dict:
        return self.metrics.resumo_mensal(df_receitas, df_despesas)

    def score_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> int:
        return self.metrics.score_mensal(df_receitas, df_despesas)
