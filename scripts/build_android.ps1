param([ValidateSet("apk", "aab")][string]$Mode = "apk")
$ErrorActionPreference = "Stop"
python -m pip install -e ".[gui]"
if ($Mode -eq "aab") {
  flet build aab src --product "HUST Helper"
} else {
  flet build apk src --split-per-abi --product "HUST Helper"
}
