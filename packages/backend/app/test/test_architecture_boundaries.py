"""Architecture boundary tests for backend layering."""

from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = APP_DIR / "services"
WORKFLOW_DIR = APP_DIR / "workflow"
MOVED_WORKFLOW_SERVICE_MODULES = {
    "app.services.workflow_agent_drafts",
    "app.services.workflow_agent_response",
    "app.services.workflow_agent_runs",
    "app.services.workflow_datasets",
    "app.services.workflow_prompts",
    "app.services.workflow_repair_state",
    "app.services.workflow_run_events",
    "app.services.workflow_run_preparation",
    "app.services.workflow_run_result",
    "app.services.workflow_targets",
    "app.services.workflow_tracking_service",
    "app.services.workflow_workspace_state",
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


def test_moved_workflow_services_use_domain_import_paths() -> None:
    violations: list[str] = []
    legacy_wrapper_paths = {
        SERVICES_DIR / "workflow_agent_drafts.py",
        SERVICES_DIR / "workflow_agent_response.py",
        SERVICES_DIR / "workflow_agent_runs.py",
        SERVICES_DIR / "workflow_datasets.py",
        SERVICES_DIR / "workflow_prompts.py",
        SERVICES_DIR / "workflow_repair_state.py",
        SERVICES_DIR / "workflow_run_events.py",
        SERVICES_DIR / "workflow_run_preparation.py",
        SERVICES_DIR / "workflow_run_result.py",
        SERVICES_DIR / "workflow_targets.py",
        SERVICES_DIR / "workflow_tracking_service.py",
        SERVICES_DIR / "workflow_workspace_state.py",
    }
    for path in sorted(APP_DIR.rglob("*.py")):
        if path in legacy_wrapper_paths:
            continue
        legacy_imports = sorted(_imported_modules(path) & MOVED_WORKFLOW_SERVICE_MODULES)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []
