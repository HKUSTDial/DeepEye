"""Package boundary checks for the core library."""

from __future__ import annotations

import ast
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[1] / "deepeye"


def _imports_backend_app(node: ast.AST) -> bool:
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        return module == "app" or module.startswith("app.")
    if isinstance(node, ast.Import):
        return any(alias.name == "app" or alias.name.startswith("app.") for alias in node.names)
    return False


def test_core_does_not_import_backend_app_modules() -> None:
    offenders: list[str] = []
    for path in CORE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(_imports_backend_app(node) for node in ast.walk(tree)):
            offenders.append(str(path.relative_to(CORE_ROOT.parent)))

    assert offenders == []
