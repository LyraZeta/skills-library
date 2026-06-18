"""Minimal standalone ZOS-API connection example."""

from zemax_zos_api_skill import connect


def main() -> None:
    with connect() as zos:
        print(f"License status: {zos.license_status}")
        print(f"Install directory: {zos.install_dir}")
        print(f"Current surfaces: {zos.system.LDE.NumberOfSurfaces}")


if __name__ == "__main__":
    main()
