# TracePro OML/DB Audit Skill

## Purpose

Use this skill when you need to audit a TracePro `.oml` file together with
local TracePro property databases. It is designed for conservative engineering
work: record what can be read directly, cross-check TracePro SQLite property
libraries, and clearly mark what cannot be decoded without a TracePro-native
export.

This skill was created after testing TracePro 7.4 behavior on Windows. The
observed reliable path was offline reading of:

- TracePro `.oml` text/ACIS attribute records;
- user and install `PropertyDatabase\TracePro.db` SQLite databases.

DDE/Scheme/GUI export paths may exist in TracePro, but were not stable enough
to make this skill depend on them.

## Requirements

- Python 3.10+.
- TracePro `.oml` file to audit.
- Optional: local TracePro installation or copied `TracePro.db` files.

No third-party Python packages are required.

## Install

```powershell
cd skills\tracepro-oml-db-audit
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
```

## Probe TracePro Database Locations

```powershell
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli probe
```

The probe checks common locations such as:

- `%APPDATA%\Lambda Research Corporation\TracePro\TracePro.db`
- `C:\Program Files\Lambda Research Corporation\TracePro*\PropertyDatabase\TracePro.db`

## Audit An OML File

```powershell
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli audit "C:\path\to\model.oml" --output outputs\tracepro_audit
```

Use explicit database paths when needed:

```powershell
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli audit "C:\path\to\model.oml" `
  --db "C:\path\to\TracePro.db" `
  --output outputs\tracepro_audit
```

## Outputs

The audit writes CSV/JSON files:

- `tracepro_audit_summary.json`
- `tracepro_audit_conclusions.csv`
- `tracepro_oml_attribute_stats.csv`
- `tracepro_oml_attribute_occurrences.csv`
- `tracepro_oml_face_nearby_attributes.csv`
- `tracepro_db_surface_properties.csv`
- `tracepro_db_stack_properties.csv`
- `tracepro_db_coating_materials.csv`
- `tracepro_db_coating_indices.csv`
- `tracepro_db_material_search.csv`

## What The Skill Reads

From OML:

- `LAM_SURF_PROPERTY`
- `LAM_SURF_PROPERTY_CATALOG`
- `LAM_SURF_COATING_USER_PARAM`
- `LAM_MAT_PROPERTY`
- `LAM_MAT_CATALOG`
- `LAM_FACE_TNDX`
- `LAM_BODY_TNDX`
- `ATTRIB_XACIS_NAME`
- nearby `face` records and approximate z ranges for audit orientation

From TracePro SQLite databases:

- `SurfaceProperties`
- `StackProperty`
- `StackPropData`
- `MATL-Coating`
- `MATL-Coating-Data`
- material-library rows matching requested substrings

## Important Interpretation Rule

Do not translate TracePro internal `1V...` tokens into coating names, layer
counts, layer materials, layer order, or thickness unless you have an
independent TracePro-native export that proves the mapping.

Database entries are library entries. They are not automatically proof that a
given surface in the OML file uses that surface property, stack, or coating
material.

## Use In Python

```python
from pathlib import Path

from tracepro_oml_db_audit import audit_tracepro
from tracepro_oml_db_audit.audit import write_outputs

result = audit_tracepro(Path("model.oml"))
write_outputs(result, Path("outputs/tracepro_audit"))
print(len(result.occurrences))
```

## Release Guidance

When this skill is used for supplier/manufacturing documents, state the limit
plainly:

- OML internal tokens were recorded but not decoded.
- TracePro database rows are audit candidates, not released assignments.
- Supplier coating prescriptions still need controlled coating design files,
  witness-sample data, and spectral measurement reports.
