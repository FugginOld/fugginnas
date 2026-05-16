# fugginnas

## Local Checks

Run the full local validation suite with one command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
```

This runs:
- `ruff check .`
- `mypy .`
- `pytest -q`

### Windows note

On some Windows setups, Python/uv interpreter discovery can fail without elevation.
If that happens, run PowerShell as Administrator and execute the same command.
