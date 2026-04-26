"""Compatibility wrapper for workflow artifact helpers.

New code should import from :mod:`app.workflow.artifacts`.
"""

from app.workflow.artifacts import (
    extract_workflow_artifacts,
    normalize_workflow_artifact,
    normalize_workflow_artifacts,
)

__all__ = [
    "extract_workflow_artifacts",
    "normalize_workflow_artifact",
    "normalize_workflow_artifacts",
]
