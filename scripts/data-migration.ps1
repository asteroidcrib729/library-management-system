[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments)]
    [string[]]$MigrationArguments
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python virtual environment not found at $python. Follow README.md setup first."
}

Push-Location $repositoryRoot
try {
    & $python -m scripts.migrate_data @MigrationArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Data migration command failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
