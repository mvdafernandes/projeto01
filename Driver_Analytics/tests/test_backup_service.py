"""Tests for backup service export/import flow."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

import pandas as pd

from services.backup_service import BackupService


class BackupServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = BackupService()
        self.service.receitas_repo = MagicMock()
        self.service.despesas_repo = MagicMock()
        self.service.investimentos_repo = MagicMock()
        self.service.controle_km_repo = MagicMock()
        self.service.controle_litros_repo = MagicMock()
        self.service.categorias_repo = MagicMock()
        self.service.receitas_repo._current_user_id.return_value = 10

    def test_export_payload_includes_format_and_counts(self):
        self.service.receitas_repo.listar.return_value = pd.DataFrame([{"data": "2026-02-01", "valor": 100.0}])
        self.service.despesas_repo.listar.return_value = pd.DataFrame([{"data": "2026-02-01", "valor": 20.0}])
        self.service.investimentos_repo.listar.return_value = pd.DataFrame()
        self.service.controle_km_repo.listar.return_value = pd.DataFrame()
        self.service.controle_litros_repo.listar.return_value = pd.DataFrame()
        self.service.categorias_repo.listar.return_value = pd.DataFrame([{"nome": "Combustível"}])

        payload = self.service.export_payload()

        self.assertEqual(payload["format"], "driver_analytics_backup")
        self.assertEqual(payload["version"], 1)
        self.assertEqual(int(payload["counts"]["receitas"]), 1)
        self.assertEqual(int(payload["counts"]["despesas"]), 1)
        self.assertEqual(int(payload["counts"]["categorias_despesas"]), 1)

    def test_import_payload_inserts_records_and_recalculates_investimentos(self):
        payload = {
            "format": "driver_analytics_backup",
            "version": 1,
            "data": {
                "categorias_despesas": [{"nome": "Combustível"}],
                "receitas": [
                    {
                        "data": "2026-02-01",
                        "valor": 300.0,
                        "km": 100.0,
                        "km_rodado_total": 120.0,
                        "tempo trabalhado": 3600,
                        "observacao": "ok",
                    }
                ],
                "despesas": [
                    {
                        "data": "2026-02-01",
                        "categoria": "Combustível",
                        "valor": 90.0,
                        "observacao": "",
                        "tipo_despesa": "VARIAVEL",
                        "subcategoria_fixa": "",
                        "esfera_despesa": "NEGOCIO",
                        "litros": 20.0,
                    }
                ],
                "investimentos": [
                    {
                        "data": "2026-02-01",
                        "data_inicio": "2026-02-01",
                        "data_fim": "2026-02-01",
                        "tipo_movimentacao": "APORTE",
                        "categoria": "Renda Fixa",
                        "aporte": 200.0,
                        "total aportado": 200.0,
                        "rendimento": 0.0,
                        "patrimonio total": 200.0,
                    }
                ],
                "controle_km": [{"data_inicio": "2026-02-01", "data_fim": "2026-02-01", "km_total_rodado": 120.0}],
                "controle_litros": [{"data": "2026-02-01", "litros": 20.0}],
            },
        }

        result = self.service.import_payload(payload, replace_existing=False)

        self.service.categorias_repo.inserir.assert_called_once_with("Combustível")
        self.assertEqual(self.service.receitas_repo.inserir.call_count, 1)
        self.assertEqual(self.service.despesas_repo.inserir.call_count, 1)
        self.assertEqual(self.service.investimentos_repo.inserir.call_count, 1)
        self.assertEqual(self.service.controle_km_repo.inserir.call_count, 1)
        self.assertEqual(self.service.controle_litros_repo.inserir.call_count, 1)
        self.service.investimentos_repo.recalcular_total_aportado.assert_called_once()
        self.service.investimentos_repo.recalcular_patrimonio_total.assert_called_once()
        self.assertEqual(int(result["receitas"]), 1)
        self.assertEqual(int(result["despesas"]), 1)
        self.assertEqual(int(result["investimentos"]), 1)

    def test_import_payload_rejects_invalid_format(self):
        with self.assertRaises(ValueError):
            self.service.import_payload({"format": "nao_suportado", "version": 1, "data": {}}, replace_existing=False)


if __name__ == "__main__":
    unittest.main()
