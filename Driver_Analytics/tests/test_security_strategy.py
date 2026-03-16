"""Regression tests for the hardened database security strategy."""

from __future__ import annotations

import hashlib
import pathlib
import unittest
from unittest.mock import patch

from core import auth
from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.controle_km_repository import ControleKMRepository
from repositories.investimentos_repository import InvestimentosRepository
from repositories.receitas_repository import ReceitasRepository


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent


class _Response:
    def __init__(self, data):
        self.data = data


class _RecordingTable:
    def __init__(self, client: "_RecordingClient", name: str):
        self.client = client
        self.name = name
        self.operation = "select"
        self.filters: list[tuple[str, object]] = []
        self.payload = None
        self._limit: int | None = None

    def select(self, *_args, **_kwargs):
        self.operation = "select"
        return self

    def eq(self, column, value):
        self.filters.append((str(column), value))
        return self

    def is_(self, column, value):
        expected = None if str(value).lower() == "null" else value
        self.filters.append((str(column), expected))
        return self

    def ilike(self, column, value):
        self.filters.append((f"ilike:{column}", str(value)))
        return self

    def order(self, _column):
        return self

    def limit(self, value):
        self._limit = int(value)
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def upsert(self, payload, **_kwargs):
        self.operation = "upsert"
        self.payload = payload
        return self

    def execute(self):
        self.client.calls.append(
            {
                "table": self.name,
                "operation": self.operation,
                "filters": list(self.filters),
                "payload": self.payload,
            }
        )
        rows = [dict(row) for row in self.client.data.get(self.name, [])]
        for column, value in self.filters:
            if column.startswith("ilike:"):
                raw_column = column.split(":", 1)[1]
                rows = [row for row in rows if str(row.get(raw_column, "")).casefold() == str(value).casefold()]
            else:
                rows = [row for row in rows if row.get(column) == value]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Response(rows)


class _RecordingClient:
    def __init__(self, data: dict[str, list[dict]] | None = None):
        self.data = data or {}
        self.calls: list[dict] = []

    def table(self, name: str):
        return _RecordingTable(self, str(name))


class SecurityStrategyTests(unittest.TestCase):
    def test_username_normalization_is_case_insensitive_for_mobile_keyboards(self):
        self.assertEqual(auth._normalize_username(" Admin "), "admin")
        self.assertEqual(auth._normalize_username("ALICE"), "alice")

    def test_cookie_session_roundtrip_preserves_session_credentials(self):
        encoded = auth._encode_cookie_session("sess-1", "token-1")

        decoded = auth._decode_cookie_session(encoded)

        self.assertEqual(decoded, ("sess-1", "token-1"))

    @patch("core.auth._browser_cookie_session", return_value=("sess-cookie", "tok-cookie"))
    def test_restore_session_from_cookie_rehydrates_state_for_mobile_reload(self, _cookie_mock):
        state = {}

        with patch("core.auth._session_state", return_value=state):
            restored = auth._restore_session_from_cookie()

        self.assertTrue(restored)
        self.assertEqual(state["session_id"], "sess-cookie")
        self.assertEqual(state["session_token"], "tok-cookie")

    def test_auth_schema_check_rejects_non_privileged_supabase_key(self):
        with patch("core.auth.get_supabase_key_role", return_value="anon"), patch(
            "core.auth.is_backend_supabase_key", return_value=False
        ):
            ok, message = auth._check_remote_auth_schema()

        self.assertFalse(ok)
        self.assertIn("chave privilegiada", message)
        self.assertIn("anon", message)

    def test_backend_only_tables_are_not_accessed_from_repositories(self):
        repository_sources = []
        for path in (PROJECT_ROOT / "repositories").glob("*.py"):
            repository_sources.append(path.read_text(encoding="utf-8"))
        combined = "\n".join(repository_sources)

        self.assertNotIn('table("usuarios")', combined)
        self.assertNotIn('table("auth_sessions")', combined)

    @patch("core.auth.is_backend_supabase_key", return_value=True)
    @patch("core.auth.get_supabase_key_role", return_value="service_role")
    @patch("core.auth.get_supabase_client")
    def test_auth_schema_check_only_touches_backend_auth_tables(self, get_client_mock, _key_role_mock, _backend_key_mock):
        client = _RecordingClient({"usuarios": [{"id": 1}], "auth_sessions": [{"session_id": "s1"}]})
        get_client_mock.return_value = client

        ok, message = auth._check_remote_auth_schema()

        self.assertTrue(ok)
        self.assertEqual(message, "")
        self.assertEqual([call["table"] for call in client.calls], ["usuarios", "auth_sessions"])

    @patch("core.auth.get_supabase_client")
    def test_resolve_session_keeps_auth_flow_functional_with_backend_tables(self, get_client_mock):
        token = "raw-token"
        client = _RecordingClient(
            {
                "auth_sessions": [
                    {
                        "session_id": "sess-1",
                        "user_id": 10,
                        "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                        "expires_at": "2099-01-01T00:00:00+00:00",
                        "revoked_at": None,
                        "last_seen_at": "2098-12-31T00:00:00+00:00",
                    }
                ],
                "usuarios": [{"id": 10, "username": "alice"}],
            }
        )
        get_client_mock.return_value = client

        session = auth._supabase_resolve_session("sess-1", token)

        self.assertEqual(session["user_id"], 10)
        self.assertEqual(session["username"], "alice")
        self.assertEqual([call["table"] for call in client.calls], ["auth_sessions", "auth_sessions", "usuarios"])

    @patch("core.auth.get_supabase_client")
    def test_authenticate_user_accepts_username_with_different_case(self, get_client_mock):
        password_hash = auth.legacy_hash_password("senha123")
        client = _RecordingClient({"usuarios": [{"id": 10, "username": "admin", "password_hash": password_hash}]})
        get_client_mock.return_value = client

        authenticated, user = auth._authenticate_user("Admin", "senha123")

        self.assertTrue(authenticated)
        self.assertEqual(user["username"], "admin")

    @patch("repositories.receitas_repository.ReceitasRepository._current_user_id")
    def test_private_repo_read_requires_user_context(self, current_user_id_mock):
        current_user_id_mock.return_value = None

        with self.assertRaises(RuntimeError):
            ReceitasRepository().buscar_por_id(1)

    @patch("repositories.controle_km_repository.ControleKMRepository._current_user_id")
    def test_private_repo_write_requires_user_context(self, current_user_id_mock):
        current_user_id_mock.return_value = None

        with self.assertRaises(RuntimeError):
            ControleKMRepository().inserir("2026-03-01", "2026-03-02", 120.0)

    @patch("repositories.investimentos_repository.InvestimentosRepository._current_user_id")
    @patch("repositories.investimentos_repository.InvestimentosRepository._supabase")
    def test_investimentos_recalculo_updates_remain_scoped_by_user(self, supabase_mock, current_user_id_mock):
        current_user_id_mock.return_value = 10
        client = _RecordingClient(
            {
                "investimentos": [
                    {
                        "id": 1,
                        "user_id": 10,
                        "data": "2026-02-01",
                        "aporte": 100.0,
                        "total_aportado": 100.0,
                        "rendimento": 0.0,
                        "patrimonio_total": 100.0,
                    },
                    {
                        "id": 2,
                        "user_id": 10,
                        "data": "2026-02-02",
                        "aporte": 50.0,
                        "total_aportado": 150.0,
                        "rendimento": 10.0,
                        "patrimonio_total": 160.0,
                    },
                ]
            }
        )
        supabase_mock.return_value = client

        repo = InvestimentosRepository()
        repo.recalcular_total_aportado()
        repo.recalcular_patrimonio_total()

        update_calls = [call for call in client.calls if call["operation"] == "update"]
        self.assertTrue(update_calls)
        for call in update_calls:
            self.assertIn(("user_id", 10), call["filters"])

    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._supabase")
    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._current_user_id")
    def test_hybrid_categories_without_user_return_only_global_rows(self, current_user_id_mock, supabase_mock):
        current_user_id_mock.return_value = None
        supabase_mock.return_value = _RecordingClient(
            {
                "categorias_despesas": [
                    {"id": 1, "user_id": None, "nome": "Combustível"},
                    {"id": 2, "user_id": 10, "nome": "Pedágio"},
                ]
            }
        )

        df = CategoriasDespesasRepository().listar()

        self.assertEqual(df["nome"].tolist(), ["Combustível"])

    @patch("repositories.categorias_despesas_repository.CategoriasDespesasRepository._current_user_id")
    def test_hybrid_categories_insert_requires_authenticated_user(self, current_user_id_mock):
        current_user_id_mock.return_value = None

        with self.assertRaises(RuntimeError):
            CategoriasDespesasRepository().inserir("Nova categoria")


if __name__ == "__main__":
    unittest.main()
