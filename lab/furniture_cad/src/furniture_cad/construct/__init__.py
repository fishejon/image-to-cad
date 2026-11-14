"""IR → build123d compiler (D1 canonical engine)."""

from furniture_cad.construct.compile import compile_ir, load_ir
from furniture_cad.construct.from_observation import construct_ir_from_observation
from furniture_cad.construct.patch import apply_ir_patches, patches_from_discrepancies

__all__ = [
    "compile_ir",
    "load_ir",
    "construct_ir_from_observation",
    "apply_ir_patches",
    "patches_from_discrepancies",
]
