Param(
    [string]$Action = "upgrade",
    [string]$Message = "autogen",
    [string]$Revision = "head"
)

Write-Output "Running migrations via venv python"

$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $backendRoot
try {
    $venvPython = Join-Path $backendRoot "venv\Scripts\python.exe"
    if (-Not (Test-Path $venvPython)) {
        Write-Error "venv python not found at $venvPython. Activate venv or create it first."
        exit 1
    }

    switch ($Action) {
        "revision" {
            & $venvPython -m alembic revision --autogenerate -m $Message
        }
        "upgrade" {
            & $venvPython -m alembic upgrade $Revision
        }
        "current" {
            & $venvPython -m alembic current
        }
        default {
            Write-Error "Unknown action: $Action"
            exit 2
        }
    }
} finally {
    Pop-Location
}

<#
Windows PowerShell helper to run Alembic migrations using the local Python virtual environment.
Does not modify existing data beyond applying migrations.
#>
<#
Prerequisites:
- A working Python venv at backend/venv with Alembic and project dependencies installed.
- Alembic migration file(s) under backend/alembic/versions/.
#>
$ErrorActionPreference = "Stop"

try {
    # Move to backend directory
    Set-Location -Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) "..")
    # Activate the virtual environment (PowerShell script)
    $activateScript = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
    } else {
        Write-Host "Activate.ps1 not found, trying direct Python invocation..."
    }

    # Run alembic upgrade head non-interactively
    $alembicExe = ".\venv\Scripts\alembic.exe"
    if (Test-Path $alembicExe) {
        & $alembicExe upgrade head
    } else {
        $pythonExe = ".\venv\Scripts\python.exe"
        if (Test-Path $pythonExe) {
            & $pythonExe -m alembic upgrade head
        } else {
            # Fallback to system Python if venv tools are not available
            python -m alembic upgrade head
        }
    }
} catch {
    Write-Error "Migration script failed: $_"
    exit 1
}


