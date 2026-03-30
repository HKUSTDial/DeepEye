# DeepEye Core

Shared agent, datasource, sandbox, and workflow primitives used by the DeepEye backend.

## Scope

This package is primarily the internal foundation for:

- workflow graph models and execution engine
- agent wrappers built on LangGraph / LangChain
- datasource metadata and extractor helpers
- sandbox abstractions used by backend runtime services

Direct usage is possible, but most agent entrypoints require you to supply:

- a configured chat model
- tool bindings
- optional checkpointer / runtime integrations

## Development

Run core tests from the repository root:

```bash
uv run pytest packages/core/tests -q
```
