"""Reusable helpers for connecting to Ansys Zemax OpticStudio through ZOS-API."""

from .connection import (
    ZemaxConnectionError,
    ZemaxError,
    ZemaxLicenseError,
    ZemaxNotFoundError,
    ZemaxSession,
    connect,
)

__all__ = [
    "ZemaxConnectionError",
    "ZemaxError",
    "ZemaxLicenseError",
    "ZemaxNotFoundError",
    "ZemaxSession",
    "connect",
]
