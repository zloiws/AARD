param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

# Run Alembic using the project's venv python on Windows (PowerShell)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path "$scriptDir\.."
$python = Join-Path $projectRoot 'venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "venv python not found at $python. Activate or create venv first."
    exit 2
}

# Ensure alembic is available in venv
& "$python" -m pip install --quiet alembic

# Build command string and execute
$argString = if ($Args) { $Args -join ' ' } else { '--help' }
$cmd = "`"$python`" -m alembic $argString"
Write-Output "Running: $cmd"
Invoke-Expression $cmd


