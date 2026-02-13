"""Application service orchestrating repositories and metrics."""

from __future__ import annotations

import pandas as pd

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
        self.metrics = MetricsService()

    def listar_receitas(self) -> pd.DataFrame:
        """Return receitas dataframe."""

        return self.receitas_repo.listar()

    def listar_despesas(self) -> pd.DataFrame:
        """Return despesas dataframe."""

        return self.despesas_repo.listar()

    def listar_investimentos(self) -> pd.DataFrame:
        """Return investimentos dataframe."""

        return self.investimentos_repo.listar()

    def criar_receita(self, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str = "") -> None:
        """Create receita record."""

        self.receitas_repo.inserir(data, valor, km, tempo_trabalhado, observacao)

    def atualizar_receita(self, item_id: int, data: str, valor: float, km: float, tempo_trabalhado: int, observacao: str) -> None:
        """Update receita record."""

        self.receitas_repo.atualizar(item_id, data, valor, km, tempo_trabalhado, observacao)

    def deletar_receita(self, item_id: int) -> None:
        """Delete receita record."""

        self.receitas_repo.deletar(item_id)

    def criar_despesa(self, data: str, categoria: str, valor: float, observacao: str = "") -> None:
        """Create despesa record."""

        self.despesas_repo.inserir(data, categoria, valor, observacao)

    def atualizar_despesa(self, item_id: int, data: str, categoria: str, valor: float, observacao: str) -> None:
        """Update despesa record."""

        self.despesas_repo.atualizar(item_id, data, categoria, valor, observacao)

    def deletar_despesa(self, item_id: int) -> None:
        """Delete despesa record."""

        self.despesas_repo.deletar(item_id)

    def criar_investimento(self, data: str, aporte: float, total_aportado: float, rendimento: float, patrimonio_total: float) -> None:
        """Create investimento record."""

        self.investimentos_repo.inserir(data, aporte, total_aportado, rendimento, patrimonio_total)

    def atualizar_investimento(self, item_id: int, data: str, aporte: float, total_aportado: float, rendimento: float, patrimonio_total: float) -> None:
        """Update investimento record."""

        self.investimentos_repo.atualizar(item_id, data, aporte, total_aportado, rendimento, patrimonio_total)

    def deletar_investimento(self, item_id: int) -> None:
        """Delete investimento record."""

        self.investimentos_repo.deletar(item_id)

    def recalcular_total_aportado(self) -> None:
        """Recalculate investment cumulative contributions."""

        self.investimentos_repo.recalcular_total_aportado()

    def resumo_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> dict:
        """Build dashboard monthly summary."""

        return self.metrics.resumo_mensal(df_receitas, df_despesas)

    def score_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> int:
        """Calculate dashboard monthly score."""

        return self.metrics.score_mensal(df_receitas, df_despesas)
