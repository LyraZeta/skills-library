"""Command line helpers for checking and exercising the local Zemax connection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .connection import ZemaxSession


def _session_info(session: ZemaxSession) -> dict[str, str | bool | int]:
    app = session.application
    system = session.system
    return {
        "connected": True,
        "install_dir": str(session.install_dir),
        "mode": str(app.Mode),
        "license_status": session.license_status,
        "samples_dir": str(session.samples_dir),
        "data_dir": str(session.data_dir),
        "number_of_surfaces": int(system.LDE.NumberOfSurfaces),
    }


def command_probe(args: argparse.Namespace) -> int:
    with ZemaxSession.connect(args.install_dir) as session:
        print(json.dumps(_session_info(session), indent=2))
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    target = Path(args.file).expanduser().resolve()
    with ZemaxSession.connect(args.install_dir) as session:
        session.system.LoadFile(str(target), False)
        info = _session_info(session)
        info.update(
            {
                "file": str(target),
                "title": str(session.system.SystemData.TitleNotes.Title),
                "fields": int(session.system.SystemData.Fields.NumberOfFields),
                "wavelengths": int(session.system.SystemData.Wavelengths.NumberOfWavelengths),
            }
        )
        print(json.dumps(info, indent=2))
    return 0


def command_demo_quickfocus(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZemaxSession.connect(args.install_dir) as session:
        ZOSAPI = session.ZOSAPI
        system = session.system

        system.New(False)
        system.SystemData.TitleNotes.Title = "ZOS-API QuickFocus smoke test"
        system.SystemData.MaterialCatalogs.AddCatalog("SCHOTT")
        system.SystemData.Aperture.ApertureValue = 40
        system.SystemData.Wavelengths.SelectWavelengthPreset(ZOSAPI.SystemData.WavelengthPreset.d_0p587)
        system.SystemData.Fields.AddField(0, 5.0, 1.0)

        lde = system.LDE
        lde.InsertNewSurfaceAt(2)
        lde.InsertNewSurfaceAt(2)
        stop = lde.GetSurfaceAt(1)
        front = lde.GetSurfaceAt(2)
        rear = lde.GetSurfaceAt(3)

        stop.Thickness = 50.0
        stop.Comment = "Stop is free to move"
        front.Radius = 100.0
        front.Thickness = 10.0
        front.Material = "N-BK7"
        front.Comment = "front of lens"
        rear.Comment = "rear of lens"

        solver = rear.RadiusCell.CreateSolveType(ZOSAPI.Editors.SolveType.FNumber)
        solver._S_FNumber.FNumber = 10
        rear.RadiusCell.SetSolveData(solver)

        quick_focus = system.Tools.OpenQuickFocus()
        quick_focus.Criterion = ZOSAPI.Tools.General.QuickFocusCriterion.SpotSizeRadial
        quick_focus.UseCentroid = True
        quick_focus.RunAndWaitForCompletion()
        quick_focus.Close()

        system.SaveAs(str(output))

        print(
            json.dumps(
                {
                    "connected": True,
                    "created": str(output),
                    "license_status": session.license_status,
                    "number_of_surfaces": int(system.LDE.NumberOfSurfaces),
                    "image_thickness": float(system.LDE.GetSurfaceAt(system.LDE.NumberOfSurfaces - 1).Thickness),
                },
                indent=2,
            )
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Drive Ansys Zemax OpticStudio through ZOS-API.")
    parser.add_argument("--install-dir", help="Optional OpticStudio installation directory.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="Start OpticStudio and print connection details.")
    probe.set_defaults(func=command_probe)

    inspect = subparsers.add_parser("inspect", help="Open a Zemax file and print basic system details.")
    inspect.add_argument("file", help="Path to a .zos/.zmx file.")
    inspect.set_defaults(func=command_inspect)

    demo = subparsers.add_parser("demo-quickfocus", help="Create a simple sequential lens and run QuickFocus.")
    demo.add_argument("--output", default="outputs/quickfocus_demo.zos", help="Output .zos path.")
    demo.set_defaults(func=command_demo_quickfocus)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
