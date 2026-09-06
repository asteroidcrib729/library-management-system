[CmdletBinding()]
param(
    [switch]$SkipFrontendBuild,
    [switch]$Postgres
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source

function Invoke-Checked {
    param(
        [Parameter(Mandatory)] [string]$Label,
        [Parameter(Mandatory)] [scriptblock]$Command
    )

    Write-Host "`n==> $Label" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python virtual environment not found at $python. Follow README.md setup first."
}
if (-not $npm) {
    throw "npm.cmd was not found on PATH. Install the Node.js major listed in web/.nvmrc."
}
if ($Postgres -and -not $env:LMS_TEST_POSTGRES_ADMIN_URL) {
    throw "Set LMS_TEST_POSTGRES_ADMIN_URL to the loopback admin database before -Postgres."
}
if ($Postgres -and -not $env:LMS_TEST_POSTGRES_CONTAINER) {
    $env:LMS_TEST_POSTGRES_CONTAINER = "supabase_db_library-management-system"
}

Push-Location $repositoryRoot
try {
    Invoke-Checked "Ruff lint" { & $python -m ruff check . }
    Invoke-Checked "Ruff formatting" { & $python -m ruff format --check . }
    Invoke-Checked "Pytest" { & $python -m pytest }
    Invoke-Checked "Pyrefly" { & $python -m pyrefly check }
    Invoke-Checked "OpenAPI contract" { & $python -m scripts.export_openapi --check }
    Invoke-Checked "Deployment contracts" { & $python -m scripts.validate_deployment }

    Push-Location (Join-Path $repositoryRoot "web")
    try {
        if ($SkipFrontendBuild) {
            Invoke-Checked "Frontend contract" { & $npm run check:api }
            Invoke-Checked "Frontend lint" { & $npm run lint }
            Invoke-Checked "Frontend types" { & $npm run typecheck }
            Invoke-Checked "Frontend tests" { & $npm run test }
        }
        else {
            Invoke-Checked "Frontend checks and production build" { & $npm run check }
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}

Write-Host "`nAll selected checks passed." -ForegroundColor Green
