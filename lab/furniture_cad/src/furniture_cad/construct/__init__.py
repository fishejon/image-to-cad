"""IR → build123d compiler (D1 canonical engine)."""

from furniture_cad.construct.compile import compile_ir, load_ir
from furniture_cad.construct.patch import apply_ir_patches, patches_from_discrepancies

__all__ = ["compile_ir", "load_ir", "apply_ir_patches", "patches_from_discrepancies"]
