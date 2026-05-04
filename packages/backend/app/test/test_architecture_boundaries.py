"""Architecture boundary tests for backend layering."""

from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = APP_DIR / "services"
AGENT_DIR = APP_DIR / "agent"
AUTH_DIR = APP_DIR / "auth"
DATASOURCE_DIR = APP_DIR / "datasource"
DEPLOY_DIR = APP_DIR / "deploy"
INFRA_DIR = APP_DIR / "infra"
RUNTIME_DIR = APP_DIR / "runtime"
SESSION_DIR = APP_DIR / "session"
WORKFLOW_DIR = APP_DIR / "workflow"
LEGACY_AGENT_SERVICE_MODULES = {
    "app.services.agent_prompts",
}
LEGACY_AUTH_SERVICE_MODULES = {
    "app.services.auth_audit",
    "app.services.auth_email",
}
LEGACY_DATASOURCE_SERVICE_MODULES = {
    "app.services.datasource_connection_service",
    "app.services.datasource_file_service",
    "app.services.datasource_preview_service",
    "app.services.datasource_specs",
}
LEGACY_DEPLOY_SERVICE_MODULES = {
    "app.services.dashboard_deploy_service",
    "app.services.video_component_naming",
    "app.services.video_deploy_service",
}
LEGACY_INFRA_SERVICE_MODULES = {
    "app.services.docker_build_paths",
    "app.services.docker_control_client",
    "app.services.minio_service",
}
LEGACY_NODE_DB_UTILITY_MODULES = {
    "app.node.core.db_utils",
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
LEGACY_SESSION_SERVICE_MODULES = {
    "app.services.chat_service",
    "app.services.session_attachment_service",
    "app.services.session_service",
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


def test_datasource_domain_does_not_depend_on_node_layer() -> None:
    violations: list[str] = []
    for path in sorted(DATASOURCE_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for module in sorted(_imported_modules(path)):
            if module == "app.node" or module.startswith("app.node."):
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


def test_auth_session_agent_domains_do_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for domain_dir in (AGENT_DIR, AUTH_DIR, SESSION_DIR):
        for path in sorted(domain_dir.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            for module in sorted(_imported_modules(path)):
                if module == "app.tools" or module.startswith("app.tools."):
                    violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_deploy_and_infra_domains_do_not_depend_on_tools_layer() -> None:
    violations: list[str] = []
    for domain_dir in (DEPLOY_DIR, INFRA_DIR):
        for path in sorted(domain_dir.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            for module in sorted(_imported_modules(path)):
                if module == "app.tools" or module.startswith("app.tools."):
                    violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_services_root_contains_no_modules() -> None:
    root_modules = sorted(path.name for path in SERVICES_DIR.glob("*.py"))

    assert root_modules == []


def test_production_code_does_not_import_services_facade() -> None:
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        if APP_DIR / "test" in path.parents:
            continue
        legacy_imports = sorted(
            module
            for module in _imported_modules(path)
            if module == "app.services" or module.startswith("app.services.")
        )
        for module in legacy_imports:
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


def test_services_root_does_not_contain_auth_session_agent_modules() -> None:
    moved_modules = sorted(
        path.name
        for pattern in ("agent_prompts.py", "auth_*.py", "chat_service.py", "session_*.py")
        for path in SERVICES_DIR.glob(pattern)
    )

    assert moved_modules == []


def test_moved_deploy_and_infra_services_use_domain_import_paths() -> None:
    legacy_modules = LEGACY_DEPLOY_SERVICE_MODULES | LEGACY_INFRA_SERVICE_MODULES
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & legacy_modules)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


def test_moved_database_helpers_use_infra_import_paths() -> None:
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & LEGACY_NODE_DB_UTILITY_MODULES)
        for module in legacy_imports:
            violations.append(f"{path.relative_to(APP_DIR)} imports {module}")

    assert violations == []


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


def test_moved_auth_session_agent_services_use_domain_import_paths() -> None:
    legacy_modules = LEGACY_AGENT_SERVICE_MODULES | LEGACY_AUTH_SERVICE_MODULES | LEGACY_SESSION_SERVICE_MODULES
    violations: list[str] = []
    for path in sorted(APP_DIR.rglob("*.py")):
        legacy_imports = sorted(_imported_modules(path) & legacy_modules)
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
