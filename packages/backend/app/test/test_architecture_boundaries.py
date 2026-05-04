"""Architecture boundary tests for backend layering."""

from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = APP_DIR / "services"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_services_do_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for path in sorted(SERVICES_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for module in sorted(_imported_modules(path)):
            if module == "app.tools" or module.startswith("app.tools."):
                violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []
