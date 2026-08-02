# Source extraction report

- Source: *HUSTer 的干饭修养——HUST 求学七年的干饭经验*
- Content credit: 许少 著 (PDF metadata: 恩赐 许)
- Source PDF pages: **49**
- Chapter records: **5**
- Section records: **32**
- Structured entries: **144**
- Embedded images extracted: **98 / 98 detected**
- Page records: **49 JSON + 49 Markdown**
- Source PDF SHA-256: `16df86c127beccedf27c49667eadb03777a62999d423c46bdb94a085f4438178`

## Preservation strategy

The structured `entities.jsonl` is a convenience index, not the only copy of the
content. Every page also has a layout-aware JSON record containing full plain text,
line ordering, bounding boxes, fonts, colors, red recommendation spans, and image
placements. Human-readable page Markdown and the original PDF are bundled as an
audit trail. Consequently, text or images that do not fit an entry heuristic remain
available and are not silently discarded.

The PDF states that red text represents recommendations and red text with yellow
background represents an especially strong recommendation. The extractor preserves
text colors. It detected yellow only in the explanatory legend, not as an additional
recommendation rectangle elsewhere.

Run `python scripts/validate_data.py` to verify counts and every image SHA-256.
