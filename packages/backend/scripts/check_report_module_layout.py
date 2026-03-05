"""Validate report_module layout after repository migration.

Usage:
  uv run --package deepeye-backend python packages/backend/scripts/check_report_module_layout.py
"""

from __future__ import annotations

import ast
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    old_dir = repo_root / "report_module"
    old_service_dir = repo_root / "packages" / "backend" / "app" / "services" / "report_module"
    new_dir = repo_root / "packages" / "backend" / "app" / "node" / "report" / "report_module"
    report_runtime_file = repo_root / "packages" / "backend" / "app" / "node" / "report" / "runtime.py"
    old_report_service_file = repo_root / "packages" / "backend" / "app" / "services" / "report_service.py"

    checks: list[tuple[str, bool]] = [
        ("old report_module dir removed", not old_dir.exists()),
        ("legacy services/report_module dir removed", not old_service_dir.exists()),
        ("new report_module dir exists", new_dir.is_dir()),
        ("pipeline.py exists", (new_dir / "pipeline.py").is_file()),
        ("DatasetContextGenerator.py exists", (new_dir / "DatasetContextGenerator.py").is_file()),
        ("utils.py exists", (new_dir / "utils.py").is_file()),
        ("template_0.html exists", (new_dir / "templates" / "template_0.html").is_file()),
        ("template_1.html exists", (new_dir / "templates" / "template_1.html").is_file()),
        ("legacy main.py removed", not (new_dir / "main.py").exists()),
        ("legacy config.py removed", not (new_dir / "config.py").exists()),
        ("legacy sample insurance.csv removed", not (new_dir / "insurance.csv").exists()),
        ("legacy services/report_service.py removed", not old_report_service_file.exists()),
    ]

    report_runtime_src = report_runtime_file.read_text(encoding="utf-8")
    checks.extend(
        [
            ("report runtime imports report module pipeline", "from .report_module.pipeline import AutoReportPipeline" in report_runtime_src),
        ]
    )

    try:
        ast.parse(report_runtime_src)
        checks.append(("runtime.py syntax valid", True))
    except SyntaxError:
        checks.append(("runtime.py syntax valid", False))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[{'OK' if ok else 'FAIL'}] {name}")

    if failed:
        print(f"\nFAILED CHECKS: {len(failed)}")
        for name in failed:
            print(f" - {name}")
        return 1

    print("\nAll report_module layout checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
