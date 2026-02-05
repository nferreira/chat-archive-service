"""Tests for alembic migrations env.py.

Note: The env.py module cannot be imported directly as it runs code at
module level that requires Alembic's EnvironmentContext to be established.
These tests verify the file exists and has the expected structure.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _get_env_py_path() -> Path:
    """Get path to the env.py file."""
    return Path(__file__).parent / "env.py"


def _parse_env_py_ast():
    """Parse env.py as AST without executing it."""
    env_path = _get_env_py_path()
    return ast.parse(env_path.read_text())


class TestEnvPyStructure:
    def test_env_py_exists(self):
        assert _get_env_py_path().exists()

    def test_has_get_url_function(self):
        tree = _parse_env_py_ast()
        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "get_url" in function_names

    def test_has_run_migrations_offline_function(self):
        tree = _parse_env_py_ast()
        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "run_migrations_offline" in function_names

    def test_has_run_migrations_online_function(self):
        tree = _parse_env_py_ast()
        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "run_migrations_online" in function_names

    def test_has_do_run_migrations_function(self):
        tree = _parse_env_py_ast()
        function_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ]
        assert "do_run_migrations" in function_names

    def test_has_run_async_migrations_function(self):
        tree = _parse_env_py_ast()
        function_names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert "run_async_migrations" in function_names

    def test_imports_alembic_context(self):
        tree = _parse_env_py_ast()
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "alembic":
                    imports.extend(alias.name for alias in node.names)
        assert "context" in imports

    def test_imports_base_metadata(self):
        tree = _parse_env_py_ast()
        content = _get_env_py_path().read_text()
        assert "from chat_archive.infrastructure.db.orm import Base" in content
        assert "target_metadata = Base.metadata" in content

    def test_imports_database_url(self):
        tree = _parse_env_py_ast()
        content = _get_env_py_path().read_text()
        assert "from chat_archive.infrastructure.db.engine import DATABASE_URL" in content

    def test_get_url_uses_environ(self):
        content = _get_env_py_path().read_text()
        # Verify get_url reads from environment
        assert 'os.environ.get("DATABASE_URL"' in content or "os.environ.get('DATABASE_URL'" in content
