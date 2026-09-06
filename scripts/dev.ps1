[CmdletBinding()]
param(
    [switch]$StartDatabase
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
$npx = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
$cliVersionFile = Join-Path $repositoryRoot "supabase\CLI_VERSION"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python virtual environment not found at $python. Follow README.md setup first."
}
if (-not $npm -or -not $npx) {
    throw "npm.cmd and npx.cmd must be available on PATH."
}
if (-not (Test-Path -LiteralPath $cliVersionFile -PathType Leaf)) {
    throw "Pinned Supabase CLI version file is missing: $cliVersionFile"
}

$cliVersion = (Get-Content -LiteralPath $cliVersionFile -Raw).Trim()
$dockerReady = $false
try {
    & docker info *> $null
    $dockerReady = $LASTEXITCODE -eq 0
}
catch {
    $dockerReady = $false
}

if ($StartDatabase) {
    if (-not $dockerReady) {
        throw "Docker Desktop's Linux engine is not running. Start Docker Desktop and retry."
    }
    Push-Location $repositoryRoot
    try {
        Write-Host "Starting the repository's local Supabase stack only..." -ForegroundColor Cyan
        & $npx --yes "supabase@$cliVersion" start
        if ($LASTEXITCODE -ne 0) {
            throw "Local Supabase startup failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
elseif (-not $dockerReady) {
    Write-Warning "Docker Desktop's Linux engine is stopped; local PostgreSQL cannot start yet."
}

$apiCommand = "& '$python' -m library_management.api"
$webCommand = "Set-Location '$repositoryRoot\web'; & '$npm' run dev"

Write-Host "`nDevelopment prerequisites are valid." -ForegroundColor Green
Write-Host "Run these commands in two separate PowerShell tabs:" -ForegroundColor Cyan
Write-Host "  API:       $apiCommand"
Write-Host "  Dashboard: $webCommand"
Write-Host "`nUse -StartDatabase to explicitly start the local Supabase stack first."
Write-Host "This script never links to or modifies a hosted Supabase project."
