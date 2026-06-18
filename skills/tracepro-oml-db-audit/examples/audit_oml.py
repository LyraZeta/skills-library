"""Run a conservative TracePro OML/database audit."""

from __future__ import annotations

import argparse
from pathlib import Path

from tracepro_oml_db_audit import audit_tracepro
from tracepro_oml_db_audit.audit import write_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("oml", help="Path to a TracePro .oml file.")
    parser.add_argument("--output", default="outputs/tracepro_audit")
    args = parser.parse_args()

    result = audit_tracepro(Path(args.oml))
    write_outputs(result, Path(args.output))
    print(f"Faces audited: {len(result.faces)}")
    print(f"Attribute occurrences: {len(result.occurrences)}")
    print(f"Output directory: {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
