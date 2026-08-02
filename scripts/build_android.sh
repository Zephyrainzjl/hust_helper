#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-apk}"
python -m pip install -e ".[gui]"
if [[ "$MODE" == "aab" ]]; then
  flet build aab src --product "HUST Helper"
else
  flet build apk src --split-per-abi --product "HUST Helper"
fi
