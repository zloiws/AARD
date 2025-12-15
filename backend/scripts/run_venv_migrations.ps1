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


