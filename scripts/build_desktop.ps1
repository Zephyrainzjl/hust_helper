param([string]$Target = "windows")
$ErrorActionPreference = "Stop"
python -m pip install -e ".[gui]"
flet build $Target src --product "HUST Helper"
