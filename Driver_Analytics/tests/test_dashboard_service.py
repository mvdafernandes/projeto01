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
        self.service.work_days_repo = MagicMock()
        self.service.work_km_periods_repo = MagicMock()
        self.service.controle_km_repo = MagicMock()
        self.service.controle_litros_repo = MagicMock()
        self.service.categorias_repo = MagicMock()
        self.service.categorias_repo.listar.return_value = pd.DataFrame(columns=["id", "nome"])
        self.service.work_days_repo.listar.return_value = pd.DataFrame()
        self.service.work_km_periods_repo.listar.return_value = pd.DataFrame()
        self.service.controle_km_repo.listar.return_value = pd.DataFrame()
        self.service.controle_litros_repo.listar.return_value = pd.DataFrame()

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

        self.service.receitas_repo.atualizar.assert_called_once_with(
            10,
            "2026-02-01",
            300.0,
            100.0,
            4200,
            "ok",
            km_rodado_total=0.0,
        )

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
            litros=0.0,
            recorrencia_tipo="",
            recorrencia_meses=0,
            recorrencia_serie_id="",
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

    def test_km_snapshot_soma_periodo_historico_com_intervalo_e_km_remunerado(self):
        self.service.work_km_periods_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "id": 1,
                    "start_date": "2026-03-01",
                    "end_date": "2026-03-03",
                    "km_total_periodo": 400.0,
                }
            ]
        )
        self.service.work_days_repo.listar.return_value = pd.DataFrame(
            [
                {
                    "work_date": "2026-03-04",
                    "start_km": 1200.0,
                    "end_km": 1210.0,
                    "km_remunerado": 10.0,
                    "km_nao_remunerado_antes": None,
                },
                {
                    "work_date": "2026-03-05",
                    "start_km": 1220.0,
                    "end_km": 1230.0,
                    "km_remunerado": 10.0,
                    "km_nao_remunerado_antes": 10.0,
                },
            ]
        )

        snapshot = self.service.km_snapshot("2026-03-01", "2026-03-05")

        self.assertEqual(snapshot["km_remunerado"], 20.0)
        self.assertEqual(snapshot["km_total"], 430.0)
        self.assertEqual(snapshot["km_nao_remunerado"], 410.0)

    def test_fuel_consumption_snapshot_usa_trechos_fechados_com_parciais(self):
        self.service.controle_litros_repo.listar.return_value = pd.DataFrame(
            [
                {"id": 1, "data": "2026-03-01", "odometro": 10000.0, "litros": 40.0, "tanque_cheio": True},
                {"id": 2, "data": "2026-03-03", "odometro": 10120.0, "litros": 10.0, "tanque_cheio": False},
                {"id": 3, "data": "2026-03-05", "odometro": 10250.0, "litros": 20.0, "tanque_cheio": False},
                {"id": 4, "data": "2026-03-07", "odometro": 10400.0, "litros": 25.0, "tanque_cheio": True},
            ]
        )

        snapshot = self.service.fuel_consumption_snapshot("2026-03-01", "2026-03-07")

        self.assertEqual(snapshot["segment_count"], 1)
        self.assertAlmostEqual(snapshot["km_trechos_fechados"], 400.0)
        self.assertAlmostEqual(snapshot["litros_trechos_fechados"], 55.0)
        self.assertAlmostEqual(snapshot["consumo_km_l"], 400.0 / 55.0)
        self.assertAlmostEqual(snapshot["litros_total_abastecidos"], 95.0)

    def test_fuel_consumption_snapshot_ignora_primeiro_abastecimento_isolado(self):
        self.service.controle_litros_repo.listar.return_value = pd.DataFrame(
            [
                {"id": 1, "data": "2026-03-01", "odometro": 10000.0, "litros": 40.0, "tanque_cheio": True},
                {"id": 2, "data": "2026-03-03", "odometro": 10120.0, "litros": 10.0, "tanque_cheio": False},
            ]
        )

        snapshot = self.service.fuel_consumption_snapshot("2026-03-01", "2026-03-03")

        self.assertEqual(snapshot["segment_count"], 0)
        self.assertEqual(snapshot["consumo_km_l"], 0.0)


if __name__ == "__main__":
    unittest.main()
