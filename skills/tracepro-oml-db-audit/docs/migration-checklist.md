# Migration Checklist

Use this checklist when moving the TracePro OML/database audit skill to another
computer.

## Machine

- Windows is recommended when you want automatic discovery of TracePro database
  paths.
- TracePro is installed locally if you want to read its installed property
  database.
- Python 3.10+ is installed.

## Skill Setup

```powershell
cd skills\tracepro-oml-db-audit
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli probe
```

## Validation

- `probe` reports any existing user or install `TracePro.db` files.
- `audit path\to\model.oml` writes CSV and JSON files.
- The conclusions CSV states that internal TracePro tokens are not decoded.

## Important Limit

This skill is an offline audit helper. It does not claim to export controlled
per-surface properties through TracePro GUI, DDE, or Scheme automation. If a
TracePro-native export is available, attach that export as the authority for
actual surface/coating assignments.
