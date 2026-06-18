# Zemax ZOS-API Connection Skill

## Purpose

Use this skill when you need to connect Python automation to Ansys Zemax
OpticStudio through ZOS-API on a Windows workstation. It creates a standalone
server-mode OpticStudio application, checks that the license permits API use,
and exposes the primary optical system as a context-managed Python object.

This skill is intentionally project-neutral. It does not include lens files,
customer data, output reports, or manufacturing documents.

## When To Use

- Probe whether a computer can run ZOS-API automation.
- Open and inspect `.zos` or `.zmx` files from Python.
- Build task scripts that call OpticStudio analyses, editors, and tools.
- Run repeatable smoke tests on a newly configured OpticStudio machine.

## Requirements

- Windows 64-bit.
- Ansys Zemax OpticStudio installed locally.
- A valid OpticStudio license that allows ZOS-API.
- Python 3.10 or newer, 64-bit.
- `pythonnet>=3.0.3,<4`.

OpticStudio must be installed on the same machine where the script runs. ZOS-API
is a local automation interface, not a remote cloud API.

## Install On A New Computer

From this skill directory:

```powershell
cd skills\zemax-zos-api
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

If `py -3` launches 32-bit Python, install a 64-bit Python and use its absolute
path instead.

## Verify The Connection

```powershell
.\.venv\Scripts\python -m zemax_zos_api_skill.cli probe
```

Expected result: JSON with `connected: true`, the OpticStudio install directory,
license status, sample directory, data directory, and number of surfaces in the
new primary system.

If OpticStudio is installed in a non-standard location:

```powershell
.\.venv\Scripts\python -m zemax_zos_api_skill.cli --install-dir "C:\Program Files\Ansys Zemax OpticStudio 2024 R1.00" probe
```

## Run The Built-In Smoke Test

```powershell
.\.venv\Scripts\python -m zemax_zos_api_skill.cli demo-quickfocus --output outputs\quickfocus_demo.zos
```

This creates a simple sequential lens, runs Quick Focus, saves the file, and
prints a JSON summary. It is useful for confirming that API tools work, not only
that the DLLs load.

## Inspect A Lens File

```powershell
.\.venv\Scripts\python -m zemax_zos_api_skill.cli inspect "C:\path\to\lens.zos"
```

The command opens the file and reports title, number of fields, wavelengths, and
surface count.

## Use In A Task Script

```python
from zemax_zos_api_skill import connect

with connect() as zos:
    system = zos.system
    ZOSAPI = zos.ZOSAPI

    print(system.SystemData.TitleNotes.Title)
    print(system.LDE.NumberOfSurfaces)
```

For a specific OpticStudio installation:

```python
from zemax_zos_api_skill import connect

with connect(r"C:\Program Files\Ansys Zemax OpticStudio 2024 R1.00") as zos:
    print(zos.license_status)
```

## How It Works

1. Confirms the process is running on 64-bit Windows.
2. Locates `ZOSAPI_NetHelper.dll` by checking Zemax registry keys and common
   Program Files install directories.
3. Loads `ZOSAPI_NetHelper.dll` through `pythonnet`.
4. Calls `ZOSAPI_Initializer.Initialize(...)`.
5. Adds the OpticStudio install directory to the DLL search path.
6. Loads `ZOSAPI.dll` and `ZOSAPI_Interfaces.dll`.
7. Creates `ZOSAPI_Connection().CreateNewApplication()`.
8. Checks `IsValidLicenseForAPI`.
9. Returns the `PrimarySystem`.

## Troubleshooting

### `ZOS-API automation requires Windows`

Run this skill on the Windows computer where OpticStudio is installed.

### `OpticStudio requires a 64-bit Python interpreter`

Install and select a 64-bit Python. ZOS-API cannot be loaded from 32-bit Python.

### `pythonnet is not installed`

Run:

```powershell
.\.venv\Scripts\python -m pip install -e .
```

### `Could not find ZOSAPI_NetHelper.dll`

OpticStudio was not found through registry/common install paths. Pass
`--install-dir` or reinstall/repair OpticStudio so its registry keys are
available.

### `License is not valid for ZOS-API use`

OpticStudio was found, but the current license does not permit API automation or
is unavailable. Open OpticStudio normally and check license status, then ask the
license administrator whether ZOS-API is enabled.

### DLL load errors after finding OpticStudio

Make sure the Python process, OpticStudio, and installed Visual C++/.NET
runtime dependencies are compatible. Restart the terminal after changing
OpticStudio installations.

## Safety And Publishing Notes

- Do not commit proprietary lens files, generated reports, material databases,
  or customer data with this skill.
- Keep examples generic and reproducible.
- Prefer standalone mode for batch automation.
- Always close the session with a context manager or call `close()`.
