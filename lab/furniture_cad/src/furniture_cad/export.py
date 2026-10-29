"""Export solids to STEP / STL under lab out/."""

from __future__ import annotations

import argparse
from pathlib import Path

from build123d import Box, export_step, export_stl

from furniture_cad.validate import check_solid

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "out"


def ensure_out(path: Path | None = None) -> Path:
    out = path or DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    return out


def export_solid(solid: object, dest_stem: Path, *, formats: tuple[str, ...] = ("stl", "step")) -> dict[str, Path]:
    check_solid(solid, label=dest_stem.name)
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for fmt in formats:
        if fmt == "stl":
            p = dest_stem.with_suffix(".stl")
            export_stl(solid, str(p))
            written["stl"] = p
        elif fmt == "step":
            p = dest_stem.with_suffix(".step")
            export_step(solid, str(p))
            written["step"] = p
        else:
            raise ValueError(f"unsupported format {fmt!r}")
    return written


def demo_box(out_dir: Path | None = None) -> Path:
    """Smoke solid: 100×50×25 mm box. Writes STL (+ STEP)."""
    out = ensure_out(out_dir)
    solid = Box(100, 50, 25)
    paths = export_solid(solid, out / "demo_box", formats=("stl", "step"))
    return paths["stl"]


def export_assembly(result: dict, out_dir: Path, *, name: str | None = None) -> dict[str, Path]:
    """Export full assembly and optional per-part STLs."""
    out = ensure_out(out_dir)
    stem = name or result.get("template", "assembly")
    assembly = result["assembly"]
    written = export_solid(assembly, out / stem, formats=("stl", "step"))
    parts_dir = out / "parts"
    for part_name, solid in result.get("parts", {}).items():
        export_solid(solid, parts_dir / part_name, formats=("stl",))
    return written


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="furniture_cad export (offline lab)")
    p.add_argument("--demo", choices=["box"], help="Write a smoke-test solid")
    p.add_argument("--out", type=Path, default=None, help="Output directory (default: lab/furniture_cad/out)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.demo == "box":
        path = demo_box(args.out)
        print(f"wrote {path}")
        return 0
    build_parser().print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
