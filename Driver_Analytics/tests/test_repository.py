"""Base tests for repository dataframe normalization."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from repositories.base_repository import BaseRepository, normalize_dataframe
from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.receitas_repository import ReceitasRepository


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, data):
        self._data = data
        self._filters: list[tuple[str, object]] = []
        self._order_by: str | None = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((str(column), value))
        return self

    def is_(self, column, value):
        expected = None if str(value).lower() == "null" else value
        self._filters.append((str(column), expected))
        return self

    def ilike(self, column, value):
        self._filters.append((f"ilike:{column}", str(value)))
        return self

    def order(self, column):
        self._order_by = str(column)
        return self

    def execute(self):
        rows = [dict(row) for row in self._data]
        for column, value in self._filters:
            if column.startswith("ilike:"):
                raw_column = column.split(":", 1)[1]
                rows = [row for row in rows if str(row.get(raw_column, "")).casefold() == str(value).casefold()]
            else:
                rows = [row for row in rows if row.get(column) == value]
        if self._order_by:
            rows = sorted(rows, key=lambda row: row.get(self._order_by))
        return _FakeResponse(rows)


class _FakeClient:
    def __init__(self, data):
        self._data = data

    def table(self, _name):
        return _FakeTable(self._data)


class _TestBaseRepository(BaseRepository):
    table_name = "fake"


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

    @patch("repositories.receitas_repository.ReceitasRepository._current_user_id")
    @patch("repositories.receitas_repository.ReceitasRepository._supabase")
    def test_listar_receitas_from_supabase_returns_standard_dataframe(self, supabase_mock, current_user_id_mock):
        current_user_id_mock.return_value = 10
        supabase_mock.return_value = _FakeClient(
            [
                {
                    "id": 1,
                    "user_id": 10,
                    "data": "2026-02-01",
                    "valor": 100.0,
                    "km": 30.0,
                    "km_rodado_total": 45.0,
                    "tempo_trabalhado": 3600,
                    "observacao": "ok",
                },
                {
                    "id": 2,
                    "user_id": 99,
                    "data": "2026-02-02",
                    "valor": 999.0,
                    "km": 99.0,
                    "km_rodado_total": 120.0,
                    "tempo_trabalhado": 3600,
                    "observacao": "outro",
                },
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

    @patch("repositories.base_repository.BaseRepository._supabase")
    @patch("repositories.base_repository.BaseRepository._current_user_id")
    def test_list_remote_rows_returns_only_authenticated_user_rows(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = 10
        supabase_mock.return_value = _FakeClient(
            [
                {"id": 1, "user_id": 10, "valor": 100.0},
                {"id": 2, "user_id": 99, "valor": 999.0},
            ]
        )

        repo = _TestBaseRepository()
        rows = repo._list_remote_rows()

        self.assertEqual(rows, [{"id": 1, "user_id": 10, "valor": 100.0}])

    @patch("repositories.base_repository.BaseRepository._supabase")
    @patch("repositories.base_repository.BaseRepository._current_user_id")
    def test_list_remote_rows_without_user_returns_empty(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = None
        supabase_mock.return_value = _FakeClient(
            [
                {"id": 1, "user_id": 10, "valor": 100.0},
                {"id": 2, "user_id": 99, "valor": 999.0},
            ]
        )

        repo = _TestBaseRepository()
        rows = repo._list_remote_rows()

        self.assertEqual(rows, [])

    @patch("repositories.receitas_repository.ReceitasRepository._supabase")
    @patch("repositories.receitas_repository.ReceitasRepository._current_user_id")
    def test_busca_por_id_nao_expoe_registro_de_outro_usuario(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = 10
        supabase_mock.return_value = _FakeClient(
            [
                {
                    "id": 7,
                    "user_id": 99,
                    "data": "2026-02-01",
                    "valor": 500.0,
                    "km": 30.0,
                    "km_rodado_total": 40.0,
                    "tempo_trabalhado": 3600,
                    "observacao": "privado",
                }
            ]
        )

        repo = ReceitasRepository()
        df = repo.buscar_por_id(7)

        self.assertTrue(df.empty)

    @patch("repositories.base_repository.BaseRepository._current_user_id")
    def test_with_user_id_requires_authenticated_user(self, current_user_id_mock):
        current_user_id_mock.return_value = None
        repo = _TestBaseRepository()

        with self.assertRaises(RuntimeError):
            repo._with_user_id({"valor": 100.0})

    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._supabase")
    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._current_user_id")
    def test_listar_categorias_mescla_globais_e_do_usuario_sem_expor_terceiros(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = 10
        supabase_mock.return_value = _FakeClient(
            [
                {"id": 1, "user_id": None, "nome": "Combustível"},
                {"id": 2, "user_id": 10, "nome": "Pedágio"},
                {"id": 3, "user_id": 99, "nome": "Privada Outro"},
            ]
        )

        repo = CategoriasDespesasRepository()
        df = repo.listar()

        self.assertEqual(sorted(df["nome"].tolist()), ["Combustível", "Pedágio"])

    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._supabase")
    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._current_user_id")
    def test_busca_categoria_prefere_personalizada_ao_invés_da_global(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = 10
        supabase_mock.return_value = _FakeClient(
            [
                {"id": 1, "user_id": None, "nome": "Combustível"},
                {"id": 2, "user_id": 10, "nome": "Combustível"},
            ]
        )

        repo = CategoriasDespesasRepository()
        df = repo.buscar_por_nome("Combustível")

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["nome"], "Combustível")


if __name__ == "__main__":
    unittest.main()
