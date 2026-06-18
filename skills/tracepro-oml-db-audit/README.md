# TracePro OML/DB Audit Skill

Reusable Python helpers for auditing TracePro `.oml` files and TracePro SQLite
property databases.

Start with [`SKILL.md`](SKILL.md).

## Quick Start

```powershell
cd skills\tracepro-oml-db-audit
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli probe
```

Audit an OML file:

```powershell
.\.venv\Scripts\python -m tracepro_oml_db_audit.cli audit "C:\path\to\model.oml" --output outputs\tracepro_audit
```
