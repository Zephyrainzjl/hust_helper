#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-linux}"
python -m pip install -e ".[gui]"
flet build "$TARGET" src --product "HUST Helper"
