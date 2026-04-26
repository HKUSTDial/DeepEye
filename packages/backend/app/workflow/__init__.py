"""Workflow domain package.

Import concrete helpers from submodules such as ``app.workflow.artifacts`` or
``app.workflow.lifecycle`` so importing one workflow concern does not eagerly
load event publishing and runtime dependencies.
"""
