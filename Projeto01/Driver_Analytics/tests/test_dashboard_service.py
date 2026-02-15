"""Tests for dashboard service business rules."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

import pandas as pd

from services.dashboard_service import DashboardService


class DashboardServiceRulesTests(unittest.TestCase):
    def setUp(self):
        self.service = DashboardService()
        self.service.receitas_repo = MagicMock()
        self.service.despesas_repo = MagicMock()
        self.service.investimentos_repo = MagicMock()
        self.service.categorias_repo = MagicMock()
        self.service.categorias_repo.listar.return_value = pd.DataFrame(columns=["id", "nome"])

    def test_criar_receita_bloqueia_duplicada(self):
        self.service.receitas_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 1,
                    "data": "2026-02-01",
                    "valor": 200.0,
                    "km": 70.0,
                    "tempo trabalhado": 3600,
                    "observacao": "",
                }
            ]
        )

        with self.assertRaises(ValueError):
            self.service.criar_receita("2026-02-01", 200.0, 70.0, 3600, "")

        self.service.receitas_repo.inserir.assert_not_called()

    def test_atualizar_receita_ignora_mesmo_id_no_duplicado(self):
        self.service.receitas_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 10,
                    "data": "2026-02-01",
                    "valor": 300.0,
                    "km": 100.0,
                    "tempo trabalhado": 4200,
                    "observacao": "ok",
                }
            ]
        )

        self.service.atualizar_receita(10, "2026-02-01", 300.0, 100.0, 4200, "ok")

        self.service.receitas_repo.atualizar.assert_called_once_with(10, "2026-02-01", 300.0, 100.0, 4200, "ok")

    def test_criar_despesa_bloqueia_duplicada(self):
        self.service.despesas_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 1,
                    "data": "2026-02-05",
                    "categoria": "Combustivel",
                    "valor": 80.0,
                    "observacao": "",
                }
            ]
        )

        with self.assertRaises(ValueError):
            self.service.criar_despesa("2026-02-05", "combustivel", 80.0, "")

        self.service.despesas_repo.inserir.assert_not_called()

    def test_criar_investimento_recalcula_total_aportado(self):
        self.service.investimentos_repo.listar.return_value = pd.DataFrame(
            columns=["id", "data", "aporte", "total aportado", "rendimento", "patrimonio total"]
        )

        self.service.criar_investimento("2026-02-01", "Renda Fixa", 100.0, 0.0, 5.0, 105.0)

        self.service.investimentos_repo.inserir.assert_called_once_with(
            "2026-02-01",
            "Renda Fixa",
            100.0,
            0.0,
            5.0,
            105.0,
            data_inicio=None,
            data_fim=None,
            tipo_movimentacao=None,
        )
        self.service.investimentos_repo.recalcular_total_aportado.assert_called_once()
        self.service.investimentos_repo.recalcular_patrimonio_total.assert_called_once()

    def test_criar_investimento_bloqueia_duplicado(self):
        self.service.investimentos_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 9,
                    "data": "2026-02-10",
                    "aporte": 200.0,
                    "total aportado": 1200.0,
                    "rendimento": 10.0,
                    "patrimonio total": 1210.0,
                }
            ]
        )

        with self.assertRaises(ValueError):
            self.service.criar_investimento("2026-02-10", "Renda Fixa", 200.0, 0.0, 10.0, 1210.0)

        self.service.investimentos_repo.inserir.assert_not_called()
        self.service.investimentos_repo.recalcular_total_aportado.assert_not_called()

    def test_atualizar_despesa_ignora_mesmo_id_no_duplicado(self):
        self.service.despesas_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 5,
                    "data": "2026-02-07",
                    "categoria": "Manutenção",
                    "valor": 150.0,
                    "observacao": "",
                }
            ]
        )

        self.service.atualizar_despesa(5, "2026-02-07", "manutenção", 150.0, "")

        self.service.despesas_repo.atualizar.assert_called_once_with(
            5,
            "2026-02-07",
            "Manutenção",
            150.0,
            "",
            esfera_despesa="NEGOCIO",
        )

    def test_atualizar_investimento_ignora_mesmo_id_no_duplicado(self):
        self.service.investimentos_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 8,
                    "data": "2026-02-11",
                    "aporte": 300.0,
                    "total aportado": 2000.0,
                    "rendimento": 12.0,
                    "patrimonio total": 2012.0,
                }
            ]
        )

        self.service.atualizar_investimento(8, "2026-02-11", "Renda Fixa", 300.0, 0.0, 12.0, 2012.0)

        self.service.investimentos_repo.atualizar.assert_called_once_with(
            8,
            "2026-02-11",
            "Renda Fixa",
            300.0,
            0.0,
            12.0,
            2012.0,
            data_inicio=None,
            data_fim=None,
            tipo_movimentacao=None,
        )
        self.service.investimentos_repo.recalcular_total_aportado.assert_called_once()
        self.service.investimentos_repo.recalcular_patrimonio_total.assert_called_once()

    def test_deletar_investimento_recalcula_total_aportado(self):
        self.service.deletar_investimento(3)

        self.service.investimentos_repo.deletar.assert_called_once_with(3)
        self.service.investimentos_repo.recalcular_total_aportado.assert_called_once()
        self.service.investimentos_repo.recalcular_patrimonio_total.assert_called_once()


if __name__ == "__main__":
    unittest.main()
