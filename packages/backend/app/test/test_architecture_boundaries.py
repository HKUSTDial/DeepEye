"""Architecture boundary tests for backend layering."""

from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = APP_DIR / "services"
DATASOURCE_DIR = APP_DIR / "datasource"
RUNTIME_DIR = APP_DIR / "runtime"
WORKFLOW_DIR = APP_DIR / "workflow"
LEGACY_DATASOURCE_SERVICE_MODULES = {
    "app.services.datasource_connection_service",
    "app.services.datasource_file_service",
    "app.services.datasource_preview_service",
    "app.services.datasource_specs",
}
LEGACY_WORKFLOW_SERVICE_MODULES = {
    "app.services.workflow_agent_drafts",
    "app.services.workflow_agent_response",
    "app.services.workflow_agent_runs",
    "app.services.workflow_artifacts",
    "app.services.workflow_datasets",
    "app.services.workflow_engine",
    "app.services.workflow_events",
    "app.services.workflow_file_service",
    "app.services.workflow_prompts",
    "app.services.workflow_repair_state",
    "app.services.workflow_runtime_registry",
    "app.services.workflow_run_events",
    "app.services.workflow_run_preparation",
    "app.services.workflow_run_result",
    "app.services.workflow_service",
    "app.services.workflow_targets",
    "app.services.workflow_tracking_service",
    "app.services.workflow_workspace_state",
}
LEGACY_RUNTIME_SERVICE_MODULES = {
    "app.services.preview_runtime",
    "app.services.preview_runtime_manager",
    "app.services.runtime_metrics",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
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


def test_workflow_domain_does_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for path in sorted(WORKFLOW_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for module in sorted(_imported_modules(path)):
            if module == "app.tools" or module.startswith("app.tools."):
                violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_datasource_domain_does_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for path in sorted(DATASOURCE_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for module in sorted(_imported_modules(path)):
            if module == "app.tools" or module.startswith("app.tools."):
                violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_runtime_domain_does_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for path in sorted(RUNTIME_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for module in sorted(_imported_modules(path)):
            if module == "app.tools" or module.startswith("app.tools."):
                violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_services_root_does_not_contain_workflow_modules() -> None:
    workflow_modules = sorted(path.name for path in SERVICES_DIR.glob("workflow_*.py"))

    assert workflow_modules == []


def test_services_root_does_not_contain_datasource_modules() -> None:
    datasource_modules = sorted(path.name for path in SERVICES_DIR.glob("datasource_*.py"))

    assert datasource_modules == []


def test_services_root_does_not_contain_runtime_modules() -> None:
    runtime_modules = sorted(
        path.name
        for pattern in ("preview_runtime*.py", "runtime_metrics.py")
        for path in SERVICES_DIR.glob(pattern)
    )

    assert runtime_modules == []


def test_moved_datasource_services_use_domain_import_paths() -> None:
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & LEGACY_DATASOURCE_SERVICE_MODULES)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_moved_runtime_services_use_domain_import_paths() -> None:
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & LEGACY_RUNTIME_SERVICE_MODULES)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_moved_workflow_services_use_domain_import_paths() -> None:
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & LEGACY_WORKFLOW_SERVICE_MODULES)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []
