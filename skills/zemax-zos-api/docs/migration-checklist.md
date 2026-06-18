# Migration Checklist

Use this checklist when moving the Zemax ZOS-API skill to another computer.

## Machine

- Windows 64-bit is installed.
- Ansys Zemax OpticStudio is installed locally.
- OpticStudio launches normally from the desktop/start menu.
- The active license allows ZOS-API.
- 64-bit Python 3.10+ is installed.

## Skill Setup

```powershell
cd skills\zemax-zos-api
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m zemax_zos_api_skill.cli probe
```

## Validation

- `probe` returns `connected: true`.
- `license_status` is not an API-invalid status.
- `demo-quickfocus` creates `outputs\quickfocus_demo.zos`.
- A known `.zos` or `.zmx` file can be opened with `inspect`.

## Common Fixes

- Use `--install-dir` when the registry does not point to the desired
  OpticStudio installation.
- Use absolute paths for lens files when running scripts from another directory.
- Recreate the virtual environment after changing Python bitness or major
  OpticStudio versions.
