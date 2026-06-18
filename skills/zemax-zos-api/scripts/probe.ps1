param(
  [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  throw "Virtual environment not found. Run: py -3 -m venv .venv; .\.venv\Scripts\python -m pip install -e ."
}

if ($InstallDir) {
  & $Python -m zemax_zos_api_skill.cli --install-dir $InstallDir probe
} else {
  & $Python -m zemax_zos_api_skill.cli probe
}
