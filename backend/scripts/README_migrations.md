Run Alembic migrations reliably using the project's virtual environment.

PowerShell:

```powershell
# Upgrade to head:
.\run_venv_migrations.ps1 -Action upgrade -Revision head

# Create autogenerate revision:
.\run_venv_migrations.ps1 -Action revision -Message "add X"

# Show current head:
.\run_venv_migrations.ps1 -Action current
```

Unix / Git Bash:

```bash
# Upgrade to head:
./run_venv_migrations.sh upgrade head

# Create autogenerate revision:
./run_venv_migrations.sh revision "add X"

# Show current head:
./run_venv_migrations.sh current
```

Notes:
- These scripts call the venv python executable directly and do not rely on PATH.
- Ensure `venv` exists under `backend/venv` and that `pip install -r requirements.txt` has been run inside the venv.
- For safety, create a DB backup or run `alembic current` to check current revision before applying upgrades.


