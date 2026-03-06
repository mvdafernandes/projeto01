"""Base tests for repository dataframe normalization."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from repositories.base_repository import normalize_dataframe
from repositories.receitas_repository import ReceitasRepository


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, data):
        self._data = data

    def select(self, *_args, **_kwargs):
        return self

    def execute(self):
        return _FakeResponse(self._data)


class _FakeClient:
    def __init__(self, data):
        self._data = data

    def table(self, _name):
        return _FakeTable(self._data)


class RepositoryTests(unittest.TestCase):
    def test_normalize_dataframe_keeps_schema_when_empty(self):
        df = normalize_dataframe(
            pd.DataFrame(),
            columns=["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"],
            numeric_columns=["id", "valor", "km", "km_rodado_total", "tempo trabalhado"],
        )
        self.assertEqual(
            list(df.columns),
            ["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"],
        )
        self.assertTrue(df.empty)

    @patch("repositories.receitas_repository.ReceitasRepository._supabase")
    def test_listar_receitas_from_supabase_returns_standard_dataframe(self, supabase_mock):
        supabase_mock.return_value = _FakeClient(
            [
                {
                    "id": 1,
                    "data": "2026-02-01",
                    "valor": 100.0,
                    "km": 30.0,
                    "km_rodado_total": 45.0,
                    "tempo_trabalhado": 3600,
                    "observacao": "ok",
                }
            ]
        )

        repo = ReceitasRepository()
        df = repo.listar()

        self.assertEqual(
            list(df.columns),
            ["id", "data", "valor", "km", "km_rodado_total", "tempo trabalhado", "observacao"],
        )
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(float(df.iloc[0]["valor"]), 100.0)
        self.assertEqual(int(df.iloc[0]["tempo trabalhado"]), 3600)


if __name__ == "__main__":
    unittest.main()
