"""Open a Zemax lens file and print basic system information."""

from __future__ import annotations

import argparse
from pathlib import Path

from zemax_zos_api_skill import connect


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to a .zos or .zmx file.")
    args = parser.parse_args()

    lens_file = Path(args.file).expanduser().resolve()
    with connect() as zos:
        zos.system.LoadFile(str(lens_file), False)
        print(f"File: {lens_file}")
        print(f"Title: {zos.system.SystemData.TitleNotes.Title}")
        print(f"Fields: {zos.system.SystemData.Fields.NumberOfFields}")
        print(f"Wavelengths: {zos.system.SystemData.Wavelengths.NumberOfWavelengths}")
        print(f"Surfaces: {zos.system.LDE.NumberOfSurfaces}")


if __name__ == "__main__":
    main()
