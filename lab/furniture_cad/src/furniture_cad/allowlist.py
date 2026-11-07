"""Allowlisted build123d / block API for Phase 1 scripts.

Default path: only catalog blocks + a small set of build123d constructors.
Freeform / unrestricted imports require experimental=True.
"""

from __future__ import annotations

from typing import Any, Callable

from furniture_cad.blocks import BLOCK_FNS
from furniture_cad.catalog import BLOCK_CATALOG, list_blocks

# Names Claude (or a human) may call without --experimental.
ALLOWED_BLOCK_IDS: frozenset[str] = frozenset(BLOCK_FNS.keys())

# build123d surface we intend to support in allowlisted scripts (names only;
# actual imports happen inside trusted modules / experimental runners).
ALLOWED_BUILD123D_NAMES: frozenset[str] = frozenset(
    {
        "Box",
        "Cylinder",
        "Sphere",
        "Cone",
        "extrude",
        "revolve",
        "sweep",
        "fillet",
        "chamfer",
        "offset",
        "mirror",
        "Location",
        "Locations",
        "Axis",
        "Plane",
        "Vector",
        "Pos",
        "Rot",
        "Mode",
        "BuildPart",
        "BuildSketch",
        "BuildLine",
        "export_stl",
        "export_step",
    }
)

FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pathlib",
        "shutil",
        "http",
        "urllib",
        "ctypes",
        "importlib",
        "builtins",
    }
)


class AllowlistError(PermissionError):
    """Raised when a script asks for a non-allowlisted symbol."""


def is_allowed_block(name: str) -> bool:
    return name in ALLOWED_BLOCK_IDS


def is_allowed_build123d(name: str) -> bool:
    return name in ALLOWED_BUILD123D_NAMES


def get_block(name: str) -> Callable[..., Any]:
    if name not in BLOCK_FNS:
        raise AllowlistError(f"unknown block {name!r}; known: {sorted(ALLOWED_BLOCK_IDS)}")
    return BLOCK_FNS[name]


def api_surface(*, experimental: bool = False) -> dict[str, Any]:
    """Return the dict of callables a sandboxed script may use."""
    surface: dict[str, Any] = {
        "blocks": {k: BLOCK_FNS[k] for k in sorted(BLOCK_FNS)},
        "block": get_block,
        "list_blocks": list_blocks,
        "catalog": {k: BLOCK_CATALOG[k] for k in BLOCK_CATALOG},
        "experimental": experimental,
    }
    if experimental:
        surface["note"] = "experimental=True: caller may import build123d freely (not for default Create)."
    else:
        surface["allowed_build123d"] = sorted(ALLOWED_BUILD123D_NAMES)
        surface["forbidden_modules"] = sorted(FORBIDDEN_MODULES)
    return surface


def check_import(module: str, *, experimental: bool = False) -> None:
    """Gate imports for a future script runner."""
    root = module.split(".", 1)[0]
    if experimental:
        return
    if root in FORBIDDEN_MODULES:
        raise AllowlistError(f"import of {module!r} blocked outside experimental mode")
    if root == "build123d":
        return  # attribute-level checks happen at getattr time in the runner
    if root in ("furniture_cad", "math", "typing", "dataclasses", "json"):
        return
    raise AllowlistError(f"import of {module!r} not on the Phase 1 allowlist (use experimental)")
