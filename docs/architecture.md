# Architecture

## Layering

1. `core`: stable domain models, immutable base + user overlay repository, search engine,
   plugin discovery.
2. `tools`: independent campus-life features. `hust_eater` is the first tool.
3. `llm`: provider-neutral chat messages, OpenAI Responses, OpenAI-compatible chat,
   optional LiteLLM, and a local `search_food` tool.
4. `ui`: Flet presentation. It only calls the public service layer.
5. entry points: Python API, notebook, CLI, and Flet app.

## Extension contract

A tool implements `name`, `description`, and `service()` and can be registered with
Python package entry points under `hust_helper.tools`. New tools do not modify the
core package.

## Data strategy

The package includes a read-only base dataset. User changes are stored as:

```json
{
  "schema_version": "1.0",
  "upserts": {"entity-id": {"...": "complete entity"}},
  "deleted_ids": ["entity-id"],
  "media": {"media-id": {"file": "media/..."}}
}
```

This allows upgrades to replace the base package while preserving local edits.
Every base entry points back to source pages. Raw page JSON/Markdown and all extracted
media remain available as an audit trail.
