"""Base tests for metrics service."""

from __future__ import annotations

import unittest

import pandas as pd

from services.metrics_service import MetricsService


class MetricsServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = MetricsService()

    def test_metrics_with_valid_dataframes(self):
        receitas = pd.DataFrame(
            [
                {"id": 1, "data": "2026-02-01", "valor": 300.0, "km": 100.0, "tempo trabalhado": 3600, "observacao": ""},
                {"id": 2, "data": "2026-02-02", "valor": 500.0, "km": 200.0, "tempo trabalhado": 4200, "observacao": ""},
            ]
        )
        despesas = pd.DataFrame(
            [
                {"id": 1, "data": "2026-02-01", "categoria": "Combustível", "valor": 100.0, "observacao": ""},
                {"id": 2, "data": "2026-02-02", "categoria": "Manutenção", "valor": 50.0, "observacao": ""},
            ]
        )

        self.assertEqual(self.service.receita_total(receitas), 800.0)
        self.assertEqual(self.service.despesa_total(despesas), 150.0)
        self.assertAlmostEqual(self.service.receita_por_km(receitas), 800.0 / 300.0)
        self.assertAlmostEqual(self.service.lucro_bruto(receitas, despesas), 650.0)
        self.assertAlmostEqual(self.service.margem_lucro(receitas, despesas), (650.0 / 800.0) * 100)

    def test_metrics_with_empty_dataframes(self):
        empty_receitas = pd.DataFrame(columns=["id", "data", "valor", "km", "tempo trabalhado", "observacao"])
        empty_despesas = pd.DataFrame(columns=["id", "data", "categoria", "valor", "observacao"])

        self.assertEqual(self.service.receita_total(empty_receitas), 0.0)
        self.assertEqual(self.service.despesa_total(empty_despesas), 0.0)
        self.assertEqual(self.service.receita_por_km(empty_receitas), 0.0)
        self.assertEqual(self.service.lucro_por_km(empty_receitas, empty_despesas), 0.0)
        self.assertIsInstance(self.service.resumo_mensal(empty_receitas, empty_despesas), dict)

    def test_division_by_zero_guard(self):
        receitas = pd.DataFrame([{"id": 1, "data": "2026-02-01", "valor": 200.0, "km": 0.0, "tempo trabalhado": 100, "observacao": ""}])
        despesas = pd.DataFrame([{"id": 1, "data": "2026-02-01", "categoria": "X", "valor": 50.0, "observacao": ""}])
        self.assertEqual(self.service.receita_por_km(receitas), 0.0)
        self.assertEqual(self.service.lucro_por_km(receitas, despesas), 0.0)


if __name__ == "__main__":
    unittest.main()
