"""Regression tests for recently fixed security and import issues."""

from __future__ import annotations

import ast
import importlib
import pathlib
import py_compile
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent


class RegressionTests(unittest.TestCase):
    def test_auth_source_does_not_persist_session_in_query_params(self):
        auth_path = PROJECT_ROOT / "core" / "auth.py"
        source = auth_path.read_text(encoding="utf-8")

        self.assertNotIn("query_params", source)
        self.assertNotIn("_AUTH_QUERY_PARAM_KEY", source)
        self.assertNotIn("_read_persisted_session", source)
        self.assertNotIn("_persist_session", source)
        self.assertNotIn("_clear_persisted_session", source)

    def test_auth_imports_without_streamlit_and_fails_ui_calls_safely(self):
        original_auth = sys.modules.get("core.auth")
        sys.modules.pop("core.auth", None)
        try:
            with patch.dict(sys.modules, {"streamlit": None}):
                auth_module = importlib.import_module("core.auth")

            self.assertEqual(auth_module.get_logged_username(), "")
            self.assertIsNone(auth_module.get_logged_user_id())
            with self.assertRaises(RuntimeError):
                auth_module.login_required()
            with self.assertRaises(RuntimeError):
                auth_module.render_logout_button()
        finally:
            sys.modules.pop("core.auth", None)
            if original_auth is not None:
                sys.modules["core.auth"] = original_auth

    def test_investimentos_ui_is_parseable_and_exposes_page_entrypoint(self):
        module_path = PROJECT_ROOT / "UI" / "investimentos_ui.py"
        source = module_path.read_text(encoding="utf-8")

        self.assertNotEqual(source.strip(), "a")
        py_compile.compile(str(module_path), doraise=True)

        tree = ast.parse(source, filename=str(module_path))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        self.assertIn("pagina_investimentos", function_names)
        self.assertIn("_render_projection", function_names)

    def test_latest_rls_migration_does_not_depend_on_supabase_auth_claims(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260316090000__align_rls_with_custom_auth_backend.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertNotIn("auth.uid()", source)
        self.assertNotIn("request.jwt.claims", source)
        self.assertIn("drop function if exists public.app_current_user_id()", source)
        self.assertNotIn("public.app_current_user_id(", source.replace("drop function if exists public.app_current_user_id()", ""))
        self.assertIn("grant usage on schema public to service_role", source)

    def test_build_id_uses_current_revision_or_env_override(self):
        from core import build_info

        build_info.get_build_id.cache_clear()
        with patch.dict("os.environ", {"STREAMLIT_BUILD_ID": "release-20260317"}, clear=False):
            self.assertEqual(build_info.get_build_id(), "release-")

        build_info.get_build_id.cache_clear()
        with patch.dict("os.environ", {}, clear=True):
            with patch("core.build_info.subprocess.run") as run_mock:
                run_mock.return_value.stdout = "abcdef12\n"
                self.assertEqual(build_info.get_build_id(), "abcdef12")

    def test_visual_record_numbering_is_descending_and_gapless(self):
        import pandas as pd
        from UI.cadastros_ui import _display_record_number, _receita_label, _with_display_order

        df = pd.DataFrame(
            [
                {"id": 20, "data": "2026-03-17", "valor": 100.0},
                {"id": 18, "data": "2026-03-16", "valor": 90.0},
                {"id": 17, "data": "2026-03-15", "valor": 80.0},
            ]
        )

        ordered = _with_display_order(df)
        self.assertEqual(ordered["registro"].tolist(), [1, 2, 3])
        self.assertEqual(ordered["id"].tolist(), [20, 18, 17])
        self.assertEqual(_display_record_number(df, 20), 1)
        self.assertEqual(_display_record_number(df, 18), 2)
        self.assertTrue(_receita_label(df, 18).startswith("Registro 2 |"))

    def test_function_search_path_migration_targets_flagged_functions(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260318100000__harden_function_search_paths.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertIn("('app', 'current_user_id')", source)
        self.assertIn("('public', 'app_current_user_id')", source)
        self.assertIn("('public', 'fn_investimentos_defaults')", source)
        self.assertIn("('public', 'set_work_days_updated_at')", source)
        self.assertIn("('public', 'set_work_km_periods_updated_at')", source)
        self.assertIn("set search_path = ''", source)

    def test_rls_policy_cleanup_migration_drops_redundant_service_policies(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260319100000__drop_redundant_service_policies.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertIn("drop policy if exists usuarios_service_all on public.usuarios", source)
        self.assertIn("drop policy if exists auth_sessions_service_all on public.auth_sessions", source)

    def test_duplicate_investimentos_index_migration_keeps_explicit_index_name(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260319101000__drop_duplicate_investimentos_index.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertIn("drop index if exists public.idx_investimentos_tipo", source)
        self.assertNotIn("idx_investimentos_tipo_movimentacao", source)

    def test_unused_index_cleanup_migration_targets_only_redundant_indexes(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260319102000__drop_redundant_unused_indexes.sql"
        source = migration_path.read_text(encoding="utf-8")

        for index_name in [
            "idx_receitas_user_id_data",
            "idx_despesas_user_id_data",
            "idx_investimentos_user_id_data",
            "idx_investimentos_user_id_data_fim",
            "idx_work_km_periods_user_id",
            "idx_categorias_despesas_user_id",
            "idx_controle_km_data_inicio",
            "idx_controle_km_data_fim",
            "idx_controle_litros_data",
        ]:
            self.assertIn(index_name, source)

    def test_backend_only_work_tables_gain_explicit_deny_policies(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260319103000__explicit_backend_only_work_table_policies.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertIn("create policy work_days_backend_only", source)
        self.assertIn("create policy work_day_events_backend_only", source)
        self.assertIn("create policy work_km_periods_backend_only", source)
        self.assertIn("using (false)", source)
        self.assertIn("with check (false)", source)

    def test_auth_rate_limit_migration_is_backend_only(self):
        migration_path = PROJECT_ROOT / "sql" / "migrations" / "20260321100000__add_auth_rate_limits.sql"
        source = migration_path.read_text(encoding="utf-8")

        self.assertIn("create table if not exists public.auth_rate_limits", source)
        self.assertIn("enable row level security", source)
        self.assertIn("grant select, insert, update, delete on table public.auth_rate_limits to service_role", source)
        self.assertIn("create policy auth_rate_limits_backend_only", source)


if __name__ == "__main__":
    unittest.main()
