# hust_helper

`hust_helper` is an extensible HUST campus-life assistant. Its first tool,
`hust_helper.tools.hust_eater`, turns the full 49-page *HUSTer 的干饭修养* guide
into a searchable, editable, source-traceable data package with desktop/mobile
GUI and optional LLM-assisted conversation.

## What is included

- **Complete source-preserving extraction**: original PDF, 49 page-level JSON files,
  49 page-level Markdown files, all 98 embedded images, layout boxes, text spans,
  source page numbers, colors, and recommendation marks.
- **Structured food catalog**: 5 chapters, 32 sections, and 144 searchable entries.
- **Non-destructive editing**: package data stays immutable; additions, updates,
  deletions, and user images are stored in a per-user overlay directory.
- **Search**: keyword, Chinese character/bigram ranking, fuzzy matching, chapter,
  area, venue type, meal period, author-visit status, price/spice notes, and tags.
- **LLM chat**: OpenAI Responses API, OpenAI-compatible APIs (SiliconFlow,
  OpenRouter, DeepSeek, DashScope-compatible endpoints, custom endpoints), plus
  optional LiteLLM for a broad provider catalog.
- **Multiple front ends**: Python API, Jupyter notebook, CLI, Flet GUI, desktop
  executable packaging, Android APK/AAB packaging.

> Code license: MIT, Copyright (c) 2026 Jialiu Zeng. The bundled source guide and
> third-party images/screenshots are covered by `DATA_LICENSE.md`, not by the code license.

## Project layout

```text
hust_helper/
├── src/
│   ├── main.py                     # Flet packaging entry point
│   └── hust_helper/
│       ├── core/                   # models, repository, search, plugins
│       ├── llm/                    # providers and food-search agent
│       ├── tools/
│       │   └── hust_eater/         # API, service, schemas, full extracted data
│       └── ui/                     # Flet GUI
├── examples/hust_eater_api.ipynb
├── scripts/                        # extraction, validation and build scripts
├── tests/
├── pyproject.toml
├── LICENSE
└── DATA_LICENSE.md
```

## Install

Core/API only:

```bash
python -m pip install .
```

Development + GUI + notebook + broad LLM support:

```bash
python -m pip install -e ".[all,dev]"
```

## Python / notebook API

```python
from hust_helper import eater

results = eater.search("不辣 鸡汤", limit=10)
for item in results:
    print(item.name, item.section_title, item.recommended_items)

# Filters are composable.
near_hust = eater.search(
    "炸鸡",
    chapter="华科周边美食篇",
    visited="visited_by_author",
    limit=5,
)

# Full source text and images remain available.
page_10 = eater.page(10)
image_bytes = eater.image_bytes("media-p010-01")
```

## CLI

```bash
hust-helper stats
hust-helper search "热干面" --section 洪山区 --limit 10
hust-helper show e3-3-1-001-...
hust-helper export --format json --output my_food_catalog.json
hust-helper gui
```

## GUI

```bash
hust-helper gui
# or
python src/main.py
```

The GUI has Search, AI chat, Data editor, and About/Data tabs. API keys are read
from environment variables or the current UI session and are never bundled.

## LLM usage

```python
from hust_helper.llm import FoodChatAgent, LLMConfig

config = LLMConfig.from_preset(
    "openai",
    model="gpt-5.6",
    api_key="...",          # Prefer OPENAI_API_KEY in normal use.
)
agent = FoodChatAgent(config=config)
reply = agent.ask("我在东区，想吃不辣、预算低一点的晚饭")
print(reply.text)
```

OpenAI-compatible example:

```python
config = LLMConfig.from_preset(
    "siliconflow",
    model="your-model-id",
    api_key="...",
)
```

Custom provider:

```python
config = LLMConfig(
    provider="openai_compatible",
    model="vendor/model",
    api_key="...",
    base_url="https://example.com/v1",
)
```

## Build a wheel / source distribution

```bash
python -m pip install build
python -m build
```

## Build desktop executable

Install Flet first, then run the platform command on that platform:

```bash
python -m pip install -e ".[gui]"
flet build windows src   # Windows -> .exe bundle
flet build linux src
flet build macos src
```

Convenience scripts are in `scripts/build_desktop.*`.

## Build Android

```bash
python -m pip install -e ".[gui]"
flet build apk src --split-per-abi
# Recommended for Play Store publication:
flet build aab src
```

See `docs/building.md` for prerequisites and signing notes.

## Re-extract a revised PDF

```bash
python scripts/extract_hust_eater_pdf.py /path/to/guide.pdf   --output src/hust_helper/tools/hust_eater/data
python scripts/validate_data.py
```

The extractor keeps raw page records and media even when a heuristic structured
entry cannot be formed, so no source material is silently discarded.
