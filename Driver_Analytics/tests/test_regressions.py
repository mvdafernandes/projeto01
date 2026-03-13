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


if __name__ == "__main__":
    unittest.main()
