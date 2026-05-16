Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repoRoot ".uv-python"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-Step "ruff" { uvx --no-python-downloads ruff check . }

Invoke-Step "mypy" { uvx --no-python-downloads mypy . }

Invoke-Step "pytest" {
    py -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        uvx --no-python-downloads --from pytest pytest -q
    }
}

Write-Host "All checks passed."
