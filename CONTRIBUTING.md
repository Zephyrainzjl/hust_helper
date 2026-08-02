# Contributing

1. Create a virtual environment and install `pip install -e ".[dev,gui]"`.
2. Add new modules under `src/hust_helper/tools/<tool_name>/`.
3. Register tools with the `hust_helper.tools` entry-point group.
4. Keep bundled source-derived data immutable; write edits into the user overlay.
5. Run `pytest` and `python scripts/validate_data.py` before submitting changes.

For new food records, preserve provenance in the `source` field and store arbitrary
future fields under `extensions` until promoted to the stable schema.
