param(
    [switch]$OneFile,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Always build from the project root containing this script.
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Prefer the project's virtual environment.
$Python = if (Test-Path ".venv\Scripts\python.exe") {
    (Resolve-Path ".venv\Scripts\python.exe").Path
} else {
    "python"
}

Write-Host "==> Python: $Python" -ForegroundColor Cyan

if (-not $SkipInstall) {
    Write-Host "==> Installing build dependencies..." -ForegroundColor Cyan
    & $Python -m pip install --upgrade pip
    & $Python -m pip install --upgrade flet pyinstaller pillow
    & $Python -m pip install -e ".[gui,realtime]"
}

# Locate flet.exe from the same Python environment.
$Flet = (& $Python -c "import shutil; print(shutil.which('flet') or '')").Trim()
if (-not $Flet) {
    throw "flet executable was not found. Run: $Python -m pip install flet"
}

# Remove stale build output only; caches and installed packages are preserved.
Remove-Item ".\build\hust_helper" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\dist\hust_helper" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\dist\hust_helper.exe" -Force -ErrorAction SilentlyContinue

$PackArgs = @(
    "pack",
    "src/main.py",
    "--name", "hust_helper",
    "--product-name", "HUST Helper",
    "--company-name", "Jialiu Zeng",
    "--product-version", "0.1.0",
    "--file-version", "0.1.0.0",
    "--file-description", "HUST campus dining and life helper",
    "--copyright", "Copyright (c) 2026 Jialiu Zeng",
    "--add-data",
        "src/hust_helper/tools/hust_eater/data:hust_helper/tools/hust_eater/data",
        "src/hust_helper/tools/hust_eater/schema:hust_helper/tools/hust_eater/schema",
    "--hidden-import",
        "hust_helper.realtime",
        "hust_helper.llm",
    "--yes"
)

# Fastest mode: one-folder bundle. Use -OneFile only for final distribution.
if (-not $OneFile) {
    $PackArgs += "--onedir"
}

# Optional icon: place docs/assets/hust_helper.ico in the project.
if (Test-Path ".\docs\assets\hust_helper.ico") {
    $PackArgs += @("--icon", "docs/assets/hust_helper.ico")
}

Write-Host "==> Building HUST Helper..." -ForegroundColor Cyan
& $Flet @PackArgs

if ($LASTEXITCODE -ne 0) {
    throw "Build failed with exit code $LASTEXITCODE."
}

if ($OneFile) {
    $Output = Join-Path $ProjectRoot "dist\hust_helper.exe"
} else {
    $Output = Join-Path $ProjectRoot "dist\hust_helper\hust_helper.exe"
}

if (-not (Test-Path $Output)) {
    throw "Build finished, but the expected executable was not found: $Output"
}

Write-Host ""
Write-Host "Build completed successfully." -ForegroundColor Green
Write-Host "EXE: $Output" -ForegroundColor Green

if (-not $OneFile) {
    Write-Host "Distribute the entire dist\hust_helper folder, not only the EXE." -ForegroundColor Yellow
}
