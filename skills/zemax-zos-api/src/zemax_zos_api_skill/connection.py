"""Connection helpers for Ansys Zemax OpticStudio ZOS-API.

The official examples duplicate a sizeable PythonStandaloneApplication class in
every script. This module keeps the same initialization pattern, but makes it a
small reusable context manager for automation scripts.
"""

from __future__ import annotations

import os
import platform
import sys
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ZemaxError(RuntimeError):
    """Base exception for local Zemax API failures."""


class ZemaxNotFoundError(ZemaxError):
    """Raised when the OpticStudio installation cannot be found."""


class ZemaxLicenseError(ZemaxError):
    """Raised when the available license does not permit API use."""


class ZemaxConnectionError(ZemaxError):
    """Raised when ZOS-API cannot create an application/session."""


def _registry_value(root, subkey: str, name: str) -> str | None:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value)
    except OSError:
        return None


def _existing_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    existing: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key not in seen and resolved.exists():
            seen.add(key)
            existing.append(resolved)
    return existing


def candidate_install_dirs() -> list[Path]:
    """Return likely OpticStudio installation directories."""

    paths: list[Path] = []

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        install = _registry_value(root, r"Software\Zemax", "InstallRoot")
        if install:
            paths.append(Path(install))

    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_name)
        if not base:
            continue
        base_path = Path(base)
        paths.extend(base_path.glob("Ansys Zemax OpticStudio*"))
        paths.extend(base_path.glob("Zemax OpticStudio*"))
        paths.extend(base_path.glob("OpticStudio*"))

    return _existing_paths(paths)


def candidate_net_helpers() -> list[Path]:
    """Return likely ZOSAPI_NetHelper.dll locations."""

    paths: list[Path] = []

    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        zemax_root = _registry_value(root, r"Software\Zemax", "ZemaxRoot")
        if zemax_root:
            paths.append(Path(zemax_root) / "ZOS-API" / "Libraries" / "ZOSAPI_NetHelper.dll")

    for install_dir in candidate_install_dirs():
        paths.append(install_dir / "ZOSAPI_NetHelper.dll")
        paths.append(install_dir / "ZOS-API" / "Libraries" / "ZOSAPI_NetHelper.dll")

    return _existing_paths(paths)


def find_net_helper() -> Path:
    helpers = candidate_net_helpers()
    if not helpers:
        raise ZemaxNotFoundError(
            "Could not find ZOSAPI_NetHelper.dll. Install OpticStudio or pass an explicit install path."
        )
    return helpers[0]


def _ensure_process_can_load_zemax_dlls(zemax_dir: Path) -> None:
    """Make OpticStudio's native dependencies visible to this Python process."""

    path_text = str(zemax_dir)
    os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        add_dll_directory(path_text)


def load_zosapi(install_dir: str | Path | None = None):
    """Initialize pythonnet and return ``(ZOSAPI, zemax_dir)``."""

    if sys.platform != "win32":
        raise ZemaxError("ZOS-API automation requires Windows.")
    if platform.architecture()[0] != "64bit":
        raise ZemaxError("OpticStudio requires a 64-bit Python interpreter.")

    try:
        import clr
    except ModuleNotFoundError as exc:
        raise ZemaxError(
            "pythonnet is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc

    net_helper = find_net_helper()
    clr.AddReference(str(net_helper))

    import ZOSAPI_NetHelper

    if install_dir is not None:
        initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(str(Path(install_dir)))
    else:
        initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
        if not initialized:
            for candidate in candidate_install_dirs():
                initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(str(candidate))
                if initialized:
                    break

    if not initialized:
        raise ZemaxNotFoundError("ZOSAPI_Initializer could not locate OpticStudio.")

    zemax_dir = Path(str(ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory())).resolve()
    _ensure_process_can_load_zemax_dlls(zemax_dir)

    clr.AddReference(str(zemax_dir / "ZOSAPI.dll"))
    clr.AddReference(str(zemax_dir / "ZOSAPI_Interfaces.dll"))

    import ZOSAPI

    return ZOSAPI, zemax_dir


@dataclass
class ZemaxSession:
    """A context-managed standalone ZOS-API application."""

    ZOSAPI: object
    connection: object
    application: object
    system: object
    install_dir: Path

    @classmethod
    def connect(cls, install_dir: str | Path | None = None) -> "ZemaxSession":
        ZOSAPI, zemax_dir = load_zosapi(install_dir)

        connection = ZOSAPI.ZOSAPI_Connection()
        if connection is None:
            raise ZemaxConnectionError("Unable to initialize ZOSAPI_Connection.")

        application = connection.CreateNewApplication()
        if application is None:
            raise ZemaxConnectionError("Unable to create a standalone OpticStudio application.")

        if not application.IsValidLicenseForAPI:
            status = getattr(application, "LicenseStatus", "unknown")
            try:
                application.CloseApplication()
            finally:
                raise ZemaxLicenseError(f"License is not valid for ZOS-API use: {status}")

        system = application.PrimarySystem
        if system is None:
            try:
                application.CloseApplication()
            finally:
                raise ZemaxConnectionError("Unable to acquire PrimarySystem.")

        return cls(ZOSAPI=ZOSAPI, connection=connection, application=application, system=system, install_dir=zemax_dir)

    def close(self) -> None:
        if self.application is not None:
            self.application.CloseApplication()
            self.application = None
        self.connection = None
        self.system = None

    def __enter__(self) -> "ZemaxSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def samples_dir(self) -> Path:
        return Path(str(self.application.SamplesDir))

    @property
    def data_dir(self) -> Path:
        return Path(str(self.application.ZemaxDataDir))

    @property
    def license_status(self) -> str:
        return str(self.application.LicenseStatus)


def connect(install_dir: str | Path | None = None) -> ZemaxSession:
    """Create a standalone OpticStudio session."""

    return ZemaxSession.connect(install_dir=install_dir)
