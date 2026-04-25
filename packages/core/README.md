# DeepEye Core

Shared agent, datasource, sandbox, and workflow primitives used by DeepEye runtime services.

## Scope

This package is primarily the internal foundation for:

- workflow graph models and execution engine
- agent wrappers built on LangGraph / LangChain
- datasource metadata and extractor helpers
- sandbox abstractions implemented by application runtimes

## Package Boundary

`packages/core` is the reusable engine layer. It should not import `app.*` or
other backend modules. Runtime integrations such as FastAPI, SQLAlchemy session
management, Docker sandbox implementations, task queues, and object storage live
in `packages/backend` and are passed into core through protocols, callbacks, or
tool lists.

Direct usage is possible, but most agent entrypoints require you to supply:

- a configured chat model
- tool bindings
- optional checkpointer / runtime integrations

## Development

Run core tests from the repository root:

```bash
uv run pytest packages/core/tests -q
```
