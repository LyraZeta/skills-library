"""Conservative TracePro OML and property database audit helpers.

TracePro OML files may contain ACIS/TracePro attribute records such as
``LAM_SURF_PROPERTY`` and ``LAM_MAT_PROPERTY``. In some TracePro versions these
records refer to internal ``1V...`` tokens. This module records those facts and
cross-checks local SQLite property databases, but it does not guess token
meanings.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TRACEPRO_ATTRS = [
    "LAM_SURF_PROPERTY",
    "LAM_SURF_PROPERTY_CATALOG",
    "LAM_SURF_COATING_USER_PARAM",
    "LAM_MAT_PROPERTY",
    "LAM_MAT_CATALOG",
    "LAM_FACE_TNDX",
    "LAM_BODY_TNDX",
    "ATTRIB_XACIS_NAME",
]

DEFAULT_MATERIAL_SEARCH = ["HWS2", "HWS9", "SILICON", "ZNSE", "Silicon", "ZnSe"]


@dataclass(frozen=True)
class TraceProPaths:
    """Common TracePro installation/user database locations."""

    install_dir: Path | None
    install_db: Path | None
    user_db: Path
    user_ini: Path


@dataclass
class AttrOccurrence:
    line_no: int
    attr: str
    value: str
    source_line: str
    nearest_face_line: int | None = None
    nearest_face_id: str = ""
    nearest_face_z: str = ""


@dataclass
class FaceRecord:
    line_no: int
    face_id: str
    face_tndx: str
    direction: str
    surface_kind: str
    z_min: float | None
    z_max: float | None
    nearby_surface_property: str
    nearby_surface_catalog: str
    nearby_material_property: str
    nearby_material_catalog: str
    note: str


@dataclass
class AuditResult:
    oml_file: Path
    db_files: list[Path]
    faces: list[FaceRecord]
    occurrences: list[AttrOccurrence]
    surface_properties: list[list[object]]
    stack_properties: list[list[object]]
    coating_materials: list[list[object]]
    coating_indices: list[list[object]]
    material_hits: list[list[object]]
    conclusions: list[list[object]]


def default_tracepro_paths() -> TraceProPaths:
    """Return common TracePro paths for the current Windows user."""

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidates = sorted(Path(program_files).glob(r"Lambda Research Corporation\TracePro*\PropertyDatabase\TracePro.db"))
    install_db = candidates[-1] if candidates else None
    install_dir = install_db.parents[1] if install_db else None
    roaming = Path.home() / "AppData" / "Roaming" / "Lambda Research Corporation" / "TracePro"
    return TraceProPaths(
        install_dir=install_dir,
        install_db=install_db,
        user_db=roaming / "TracePro.db",
        user_ini=roaming / "TracePro.ini",
    )


def read_oml_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="ignore").splitlines()


def attr_value(line: str, attr: str) -> str | None:
    match = re.search(r"@" + str(len(attr)) + r"\s+" + re.escape(attr) + r"\s+(?:@\d+\s+)?([^\s#]+)", line)
    return match.group(1) if match else None


def parse_bbox_from_face(line: str) -> tuple[float | None, float | None]:
    parts = line.split()
    if " T " not in line and " T" not in line:
        return None, None
    try:
        idx = parts.index("T")
    except ValueError:
        return None, None
    nums: list[float] = []
    for token in parts[idx + 1 :]:
        try:
            nums.append(float(token))
        except ValueError:
            break
        if len(nums) == 6:
            break
    if len(nums) == 6:
        return nums[2], nums[5]
    return None, None


def short_z(z_min: float | None, z_max: float | None) -> str:
    if z_min is None or z_max is None:
        return ""
    return f"{z_min:.6g} - {z_max:.6g}"


def find_surface_kind(lines: list[str], index: int) -> str:
    for line in lines[index + 1 : min(len(lines), index + 8)]:
        token = line.split(" ", 1)[0] if line else ""
        if token.endswith("-surface"):
            return token
        if line.startswith("face "):
            break
    return ""


def nearby_attr(lines: list[str], index: int, attr: str, before: int = 8, after: int = 4) -> str:
    values: list[str] = []
    for line in lines[max(0, index - before) : min(len(lines), index + after + 1)]:
        value = attr_value(line, attr)
        if value is not None:
            values.append(value)
    return "; ".join(dict.fromkeys(values))


def parse_faces(lines: list[str]) -> list[FaceRecord]:
    records: list[FaceRecord] = []
    for i, line in enumerate(lines):
        if not line.startswith("face "):
            continue
        parts = line.split()
        face_id = parts[1] if len(parts) > 1 else ""
        direction = ""
        for value in ("forward", "reversed"):
            if value in parts:
                direction = value
                break
        z_min, z_max = parse_bbox_from_face(line)
        records.append(
            FaceRecord(
                line_no=i + 1,
                face_id=face_id,
                face_tndx=nearby_attr(lines, i, "LAM_FACE_TNDX"),
                direction=direction,
                surface_kind=find_surface_kind(lines, i),
                z_min=z_min,
                z_max=z_max,
                nearby_surface_property=nearby_attr(lines, i, "LAM_SURF_PROPERTY"),
                nearby_surface_catalog=nearby_attr(lines, i, "LAM_SURF_PROPERTY_CATALOG"),
                nearby_material_property=nearby_attr(lines, i, "LAM_MAT_PROPERTY"),
                nearby_material_catalog=nearby_attr(lines, i, "LAM_MAT_CATALOG"),
                note="Nearby attribute window is for audit positioning only; use TracePro GUI/API exports for controlled object properties.",
            )
        )
    return records


def parse_attr_occurrences(lines: list[str], faces: list[FaceRecord]) -> list[AttrOccurrence]:
    face_by_line = sorted(faces, key=lambda row: row.line_no)
    occurrences: list[AttrOccurrence] = []
    for i, line in enumerate(lines):
        for attr in TRACEPRO_ATTRS:
            value = attr_value(line, attr)
            if value is None:
                continue
            nearest = min(face_by_line, key=lambda row: abs(row.line_no - (i + 1))) if face_by_line else None
            occurrences.append(
                AttrOccurrence(
                    line_no=i + 1,
                    attr=attr,
                    value=value,
                    source_line=line[:500],
                    nearest_face_line=nearest.line_no if nearest else None,
                    nearest_face_id=nearest.face_id if nearest else "",
                    nearest_face_z=short_z(nearest.z_min, nearest.z_max) if nearest else "",
                )
            )
    return occurrences


def connect_db(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("select 1 from sqlite_master where type='table' and name=?", (name,)).fetchone()
    return row is not None


def fetch_rows(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    return con.execute(sql, params).fetchall()


def iter_dbs(paths: Iterable[Path]) -> Iterable[tuple[str, Path, sqlite3.Connection]]:
    seen: set[Path] = set()
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        con = connect_db(resolved)
        if con is not None:
            label = "user TracePro.db" if "Roaming" in str(resolved) else "install TracePro.db"
            yield label, resolved, con


def surface_property_rows(db_paths: Iterable[Path]) -> list[list[object]]:
    rows: list[list[object]] = []
    for label, path, con in iter_dbs(db_paths):
        if not table_exists(con, "SurfaceProperties"):
            continue
        for row in fetch_rows(
            con,
            'select Name, Description, SolveName, StackName, StackCatalog, MatlCatalog_Side1, MatlProperty_Side1, MatlCatalog_Side2, MatlProperty_Side2 from "SurfaceProperties" order by Name',
        ):
            rows.append([label, str(path), *row])
    return rows


def stack_rows(db_paths: Iterable[Path]) -> list[list[object]]:
    rows: list[list[object]] = []
    for label, path, con in iter_dbs(db_paths):
        if not (table_exists(con, "StackProperty") and table_exists(con, "StackPropData")):
            continue
        props = fetch_rows(con, 'select Name, Description, StackType from "StackProperty" order by Name')
        for name, desc, stack_type in props:
            layers = fetch_rows(
                con,
                'select LayerNumber, Thickness, MaterialName, MaterialCat from "StackPropData" where Name=? order by LayerNumber',
                (name,),
            )
            if not layers:
                rows.append([label, str(path), name, desc, stack_type, "", "", "", ""])
            for layer in layers:
                rows.append([label, str(path), name, desc, stack_type, *layer])
    return rows


def coating_material_rows(db_paths: Iterable[Path], wavelength_min: float, wavelength_max: float) -> list[list[object]]:
    rows: list[list[object]] = []
    for label, path, con in iter_dbs(db_paths):
        if not table_exists(con, "MATL-Coating"):
            continue
        mats = fetch_rows(
            con,
            'select Name, Description, WavelengthStart, WavelengthEnd from "MATL-Coating" order by Name',
        )
        for name, desc, w0, w1 in mats:
            covers = bool(w0 is not None and w1 is not None and float(w0) <= wavelength_min and float(w1) >= wavelength_max)
            rows.append([label, str(path), name, desc, w0, w1, "yes" if covers else "no"])
    return rows


def coating_index_rows(db_paths: Iterable[Path], wavelength_min: float, wavelength_max: float) -> list[list[object]]:
    rows: list[list[object]] = []
    for label, path, con in iter_dbs(db_paths):
        if not table_exists(con, "MATL-Coating-Data"):
            continue
        data = fetch_rows(
            con,
            'select Name, Temperature, Wavelength, "Index-real", "Index-imag" from "MATL-Coating-Data" where Wavelength between ? and ? order by Name, Wavelength',
            (wavelength_min, wavelength_max),
        )
        for row in data:
            rows.append([label, str(path), *row])
    return rows


def material_search_rows(db_paths: Iterable[Path], material_names: Iterable[str]) -> list[list[object]]:
    rows: list[list[object]] = []
    for label, path, con in iter_dbs(db_paths):
        table_names = [r[0] for r in con.execute("select name from sqlite_master where type='table'").fetchall()]
        for material in material_names:
            for table in table_names:
                cols = con.execute(f'PRAGMA table_info("{table}")').fetchall()
                col_names = [c[1] for c in cols]
                if not {"Name", "Description", "WavelengthStart", "WavelengthEnd"}.issubset(set(col_names)):
                    continue
                if "Type" in col_names:
                    sql = f'select Name, Description, WavelengthStart, WavelengthEnd, Type from "{table}" where Name like ? order by Name limit 20'
                else:
                    sql = f'select Name, Description, WavelengthStart, WavelengthEnd, "" from "{table}" where Name like ? order by Name limit 20'
                for row in fetch_rows(con, sql, (f"%{material}%",)):
                    rows.append([label, str(path), material, table, *row])
    unique: list[list[object]] = []
    seen: set[tuple] = set()
    for row in rows:
        key = tuple(row)
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def attr_stats_rows(occurrences: list[AttrOccurrence]) -> list[list[object]]:
    counter = Counter((row.attr, row.value) for row in occurrences)
    return [[attr, value, count] for (attr, value), count in sorted(counter.items(), key=lambda x: (x[0][0], -x[1], x[0][1]))]


def occurrence_rows(occurrences: list[AttrOccurrence]) -> list[list[object]]:
    return [
        [row.line_no, row.attr, row.value, row.nearest_face_line or "", row.nearest_face_id, row.nearest_face_z, row.source_line]
        for row in occurrences
    ]


def face_rows(faces: list[FaceRecord]) -> list[list[object]]:
    return [
        [
            row.line_no,
            row.face_id,
            row.face_tndx,
            row.direction,
            row.surface_kind,
            short_z(row.z_min, row.z_max),
            row.nearby_surface_catalog,
            row.nearby_surface_property,
            row.nearby_material_catalog,
            row.nearby_material_property,
            row.note,
        ]
        for row in faces
    ]


def conclusion_rows(
    oml_file: Path,
    occurrences: list[AttrOccurrence],
    coating_materials: list[list[object]],
    material_hits: list[list[object]],
    wavelength_min: float,
    wavelength_max: float,
) -> list[list[object]]:
    surf_codes = Counter(row.value for row in occurrences if row.attr == "LAM_SURF_PROPERTY")
    coating_user_params = Counter(row.value for row in occurrences if row.attr == "LAM_SURF_COATING_USER_PARAM")
    mat_codes = Counter(row.value for row in occurrences if row.attr == "LAM_MAT_PROPERTY")
    covering_materials = sorted({str(row[2]) for row in coating_materials if row[-1] == "yes"})
    return [
        ["TracePro OML file", str(oml_file), "Read as text; ACIS/TracePro attribute records were audited."],
        ["Surface property tokens", f"{len(surf_codes)} unique / {sum(surf_codes.values())} occurrences", "Token values are internal records unless separately exported by TracePro."],
        ["Coating user parameters", ", ".join(f"{k}({v})" for k, v in coating_user_params.items()) or "none", "Do not treat these values as layer materials, order, or thickness."],
        ["Material property tokens", f"{len(mat_codes)} unique / {sum(mat_codes.values())} occurrences", "OML text alone did not decode these tokens into controlled material names."],
        ["Material database search", f"{len(material_hits)} matching rows", "Database hits show available library entries, not necessarily object assignments in the OML."],
        [f"Coating materials covering {wavelength_min:g}-{wavelength_max:g} um", ", ".join(covering_materials) if covering_materials else "none found", "Use as audit candidates only; not as a released coating prescription."],
        ["TracePro GUI/API export", "not performed by this offline audit", "If a controlled per-surface TracePro export is available, attach it as the authority for actual assignments."],
        ["Release guidance", "do not guess", "Do not publish unverified coating layer count, materials, order, or thickness from internal tokens."],
    ]


def audit_tracepro(
    oml_file: Path,
    db_paths: Iterable[Path] | None = None,
    material_names: Iterable[str] = DEFAULT_MATERIAL_SEARCH,
    wavelength_min: float = 3.0,
    wavelength_max: float = 5.0,
) -> AuditResult:
    oml_file = oml_file.expanduser().resolve()
    lines = read_oml_lines(oml_file)
    faces = parse_faces(lines)
    occurrences = parse_attr_occurrences(lines, faces)

    if db_paths is None:
        defaults = default_tracepro_paths()
        raw_paths = [defaults.user_db]
        if defaults.install_db is not None:
            raw_paths.append(defaults.install_db)
        db_paths = raw_paths
    resolved_db_paths = [p.expanduser().resolve() for p in db_paths if p.expanduser().exists()]

    surface_props = surface_property_rows(resolved_db_paths)
    stacks = stack_rows(resolved_db_paths)
    coating_materials = coating_material_rows(resolved_db_paths, wavelength_min, wavelength_max)
    coating_indices = coating_index_rows(resolved_db_paths, wavelength_min, wavelength_max)
    material_hits = material_search_rows(resolved_db_paths, material_names)
    conclusions = conclusion_rows(oml_file, occurrences, coating_materials, material_hits, wavelength_min, wavelength_max)

    return AuditResult(
        oml_file=oml_file,
        db_files=resolved_db_paths,
        faces=faces,
        occurrences=occurrences,
        surface_properties=surface_props,
        stack_properties=stacks,
        coating_materials=coating_materials,
        coating_indices=coating_indices,
        material_hits=material_hits,
        conclusions=conclusions,
    )


def write_csv(path: Path, headers: Iterable[str], rows: Iterable[Iterable[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(headers))
        writer.writerows(rows)


def write_outputs(result: AuditResult, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    tables = {
        "conclusions": (
            "tracepro_audit_conclusions.csv",
            ["item", "value", "note"],
            result.conclusions,
        ),
        "attribute_stats": (
            "tracepro_oml_attribute_stats.csv",
            ["attribute", "value", "count"],
            attr_stats_rows(result.occurrences),
        ),
        "attribute_occurrences": (
            "tracepro_oml_attribute_occurrences.csv",
            ["line_no", "attribute", "value", "nearest_face_line", "nearest_face_id", "nearest_face_z", "source_line"],
            occurrence_rows(result.occurrences),
        ),
        "face_nearby_attributes": (
            "tracepro_oml_face_nearby_attributes.csv",
            [
                "line_no",
                "face_id",
                "face_tndx",
                "direction",
                "surface_kind",
                "z_range",
                "nearby_surface_catalog",
                "nearby_surface_property",
                "nearby_material_catalog",
                "nearby_material_property",
                "note",
            ],
            face_rows(result.faces),
        ),
        "surface_properties": (
            "tracepro_db_surface_properties.csv",
            [
                "db_label",
                "db_path",
                "name",
                "description",
                "solve_name",
                "stack_name",
                "stack_catalog",
                "material_catalog_side1",
                "material_property_side1",
                "material_catalog_side2",
                "material_property_side2",
            ],
            result.surface_properties,
        ),
        "stack_properties": (
            "tracepro_db_stack_properties.csv",
            ["db_label", "db_path", "stack_name", "description", "stack_type", "layer_number", "thickness", "material_name", "material_catalog"],
            result.stack_properties,
        ),
        "coating_materials": (
            "tracepro_db_coating_materials.csv",
            ["db_label", "db_path", "name", "description", "wavelength_start_um", "wavelength_end_um", "covers_target_band"],
            result.coating_materials,
        ),
        "coating_indices": (
            "tracepro_db_coating_indices.csv",
            ["db_label", "db_path", "name", "temperature", "wavelength_um", "index_real", "index_imag"],
            result.coating_indices,
        ),
        "material_search": (
            "tracepro_db_material_search.csv",
            ["db_label", "db_path", "search_term", "table", "name", "description", "wavelength_start_um", "wavelength_end_um", "type"],
            result.material_hits,
        ),
    }

    for key, (filename, headers, rows) in tables.items():
        path = output_dir / filename
        write_csv(path, headers, rows)
        files[key] = str(path)

    summary = {
        "oml_file": str(result.oml_file),
        "db_files": [str(path) for path in result.db_files],
        "face_count": len(result.faces),
        "attribute_occurrence_count": len(result.occurrences),
        "surface_property_rows": len(result.surface_properties),
        "stack_property_rows": len(result.stack_properties),
        "coating_material_rows": len(result.coating_materials),
        "coating_index_rows": len(result.coating_indices),
        "material_search_rows": len(result.material_hits),
        "outputs": files,
        "warning": "Internal TracePro tokens are recorded, not decoded. Do not release guessed coating layer data.",
    }
    summary_path = output_dir / "tracepro_audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    files["summary"] = str(summary_path)
    return files
