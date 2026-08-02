# `hust_eater` data model

Each JSONL entity contains:

- identity: `id`, `ordinal`, `name`, `category`, `heading`
- hierarchy: `chapter_id`, `section_id`, chapter/section titles
- source trace: `source_pages`, captions, media IDs, source author/document
- content: verbatim `description`, red/highlighted segments, parsed recommended items
- search facets: visit status, venue type, meal periods, spice/price notes, tags
- extension points: `extensions` and `user_editable`

`catalog.json` stores hierarchy and counts. `media/manifest.json` stores media IDs,
page, bounding box, dimensions, hash, caption, and optional related entry. `pages/`
contains complete page records and human-readable Markdown.

The JSON Schema at `schema/entity.schema.json` documents the stable minimum while
allowing additional fields for future campus-guide modules.
