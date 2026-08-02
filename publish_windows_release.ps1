param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^v?\d+\.\d+\.\d+([\-+][0-9A-Za-z\.-]+)?$")]
    [string]$Version,

    [string]$Repo = "Zephyrainzjl/hust_helper",

    [switch]$SkipBuild,
    [switch]$InstallDependencies,
    [switch]$Draft
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not $Version.StartsWith("v")) {
    $Version = "v$Version"
}

$BuildScript = Join-Path $ProjectRoot "build_exe_fast.ps1"
$RawExe = Join-Path $ProjectRoot "dist\hust_helper.exe"
$ReleaseExe = Join-Path $ProjectRoot "dist\hust_helper-windows-x64.exe"
$ChecksumFile = "$ReleaseExe.sha256"

if (-not $SkipBuild) {
    if (-not (Test-Path $BuildScript)) {
        throw "Cannot find build_exe_fast.ps1 in the project root."
    }

    Write-Host "==> Building one-file Windows executable..." -ForegroundColor Cyan

    if ($InstallDependencies) {
        & powershell -ExecutionPolicy Bypass -File $BuildScript -OneFile
    }
    else {
        & powershell -ExecutionPolicy Bypass -File $BuildScript -OneFile -SkipInstall
    }

    if ($LASTEXITCODE -ne 0) {
        throw "EXE build failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $RawExe)) {
    throw "Cannot find the built executable: $RawExe"
}

Copy-Item $RawExe $ReleaseExe -Force

$Hash = (Get-FileHash $ReleaseExe -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash  hust_helper-windows-x64.exe" |
    Set-Content -Path $ChecksumFile -Encoding ascii

Write-Host "==> Release executable: $ReleaseExe" -ForegroundColor Green
Write-Host "==> SHA-256: $Hash" -ForegroundColor Green

$Gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $Gh) {
    throw @"
GitHub CLI (gh) is not installed.
Install it from https://cli.github.com/ and then run:
    gh auth login
"@
}

& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI is not authenticated. Run: gh auth login"
}

# Query the release list instead of intentionally calling `gh release view`
# on a tag that may not exist. With `$ErrorActionPreference = "Stop"`,
# the expected "release not found" stderr message would otherwise terminate
# Windows PowerShell before `$LASTEXITCODE` can be inspected.
$ReleaseListJson = & gh release list `
    --repo $Repo `
    --limit 100 `
    --json tagName

if ($LASTEXITCODE -ne 0) {
    throw "Unable to list GitHub Releases for $Repo."
}

$ReleaseExists = @(
    $ReleaseListJson |
        ConvertFrom-Json |
        Where-Object { $_.tagName -eq $Version }
).Count -gt 0

if ($ReleaseExists) {
    Write-Host "==> Release $Version exists; replacing its assets..." -ForegroundColor Yellow
    & gh release upload $Version `
        $ReleaseExe `
        $ChecksumFile `
        --repo $Repo `
        --clobber

    if ($LASTEXITCODE -ne 0) {
        throw "Uploading release assets failed."
    }

    if (-not $Draft) {
        & gh release edit $Version --repo $Repo --latest
    }
}
else {
    Write-Host "==> Creating GitHub Release $Version..." -ForegroundColor Cyan

    $CreateArgs = @(
        "release", "create", $Version,
        $ReleaseExe,
        $ChecksumFile,
        "--repo", $Repo,
        "--title", "HUST Helper $Version",
        "--generate-notes",
        "--target", "main"
    )

    if ($Draft) {
        $CreateArgs += "--draft"
    }
    else {
        $CreateArgs += "--latest"
    }

    & gh @CreateArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Creating the GitHub Release failed."
    }
}

$DirectUrl = "https://github.com/$Repo/releases/latest/download/hust_helper-windows-x64.exe"
$ChecksumUrl = "$DirectUrl.sha256"

Write-Host ""
Write-Host "Release completed." -ForegroundColor Green
Write-Host "Direct EXE download:" -ForegroundColor Cyan
Write-Host $DirectUrl
Write-Host "SHA-256 file:" -ForegroundColor Cyan
Write-Host $ChecksumUrl
