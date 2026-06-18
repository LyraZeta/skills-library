$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  throw "Virtual environment not found. Run: py -3 -m venv .venv; .\.venv\Scripts\python -m pip install -e ."
}

& $Python -m tracepro_oml_db_audit.cli probe
