from __future__ import annotations

from pathlib import Path


def _project_root_from_anchor(anchor_file: str) -> Path:
    for parent in Path(anchor_file).resolve().parents:
        if (parent / "packages" / "backend").is_dir() and (parent / "docker").is_dir():
            return parent
    return Path(anchor_file).resolve().parents[4]


def resolve_docker_build_target(
    *,
    dockerfile_setting: str,
    default_context_root: str,
    anchor_file: str,
) -> tuple[str, str, Path]:
    dockerfile_path = Path(dockerfile_setting)
    if dockerfile_path.is_absolute():
        resolved = dockerfile_path.resolve()
        return str(resolved.parent), resolved.name, resolved

    anchor_root = _project_root_from_anchor(anchor_file)
    candidates: list[Path] = []
    for root in (
        Path(default_context_root),
        Path("/app/project"),
        anchor_root,
        Path.cwd(),
    ):
        if root not in candidates:
            candidates.append(root)

    for root in candidates:
        candidate = (root / dockerfile_path).resolve()
        if candidate.exists():
            return str(root.resolve()), dockerfile_setting, candidate

    fallback = (Path(default_context_root) / dockerfile_path).resolve()
    return str(Path(default_context_root).resolve()), dockerfile_setting, fallback
