# Zemax ZOS-API Skill

Reusable Python helpers for connecting to Ansys Zemax OpticStudio through
ZOS-API.

Start with [`SKILL.md`](SKILL.md).

## Quick Start

```powershell
cd skills\zemax-zos-api
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m zemax_zos_api_skill.cli probe
```

## Minimal Python

```python
from zemax_zos_api_skill import connect

with connect() as zos:
    print(zos.license_status)
    print(zos.system.LDE.NumberOfSurfaces)
```
