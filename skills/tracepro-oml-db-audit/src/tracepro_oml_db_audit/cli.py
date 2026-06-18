"""CLI for the TracePro OML/property database audit skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_tracepro, default_tracepro_paths, write_outputs


def command_probe(args: argparse.Namespace) -> int:
    paths = default_tracepro_paths()
    payload = {
        "install_dir": str(paths.install_dir) if paths.install_dir else "",
        "install_db": str(paths.install_db) if paths.install_db else "",
        "install_db_exists": bool(paths.install_db and paths.install_db.exists()),
        "user_db": str(paths.user_db),
        "user_db_exists": paths.user_db.exists(),
        "user_ini": str(paths.user_ini),
        "user_ini_exists": paths.user_ini.exists(),
    }
    print(json.dumps(payload, indent=2))
    return 0


def command_audit(args: argparse.Namespace) -> int:
    db_paths = [Path(value) for value in args.db] if args.db else None
    result = audit_tracepro(
        Path(args.oml),
        db_paths=db_paths,
        material_names=args.material,
        wavelength_min=args.wavelength_min,
        wavelength_max=args.wavelength_max,
    )
    files = write_outputs(result, Path(args.output))
    print(
        json.dumps(
            {
                "oml_file": str(result.oml_file),
                "db_files": [str(path) for path in result.db_files],
                "face_count": len(result.faces),
                "attribute_occurrence_count": len(result.occurrences),
                "output_dir": str(Path(args.output).resolve()),
                "files": files,
                "warning": "Internal TracePro tokens were recorded, not decoded.",
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit TracePro OML attributes and TracePro SQLite property databases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="Show likely TracePro database locations.")
    probe.set_defaults(func=command_probe)

    audit = subparsers.add_parser("audit", help="Audit an OML file and write CSV/JSON outputs.")
    audit.add_argument("oml", help="Path to a TracePro .oml file.")
    audit.add_argument("--output", default="outputs/tracepro_audit", help="Output directory for CSV/JSON audit files.")
    audit.add_argument("--db", action="append", default=[], help="TracePro.db path. Can be repeated. Defaults to user/install databases.")
    audit.add_argument("--material", action="append", default=["HWS2", "HWS9", "SILICON", "ZNSE"], help="Material name substring to search in databases. Can be repeated.")
    audit.add_argument("--wavelength-min", type=float, default=3.0, help="Minimum wavelength in micrometers for coating material audit.")
    audit.add_argument("--wavelength-max", type=float, default=5.0, help="Maximum wavelength in micrometers for coating material audit.")
    audit.set_defaults(func=command_audit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
