"""Parts record schema for cut/material lists (Phase 1).

Dims are millimetres. Blank sizes for curved parts may differ from finished bbox.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PartRecord:
    id: str
    name: str
    qty: int
    material: str
    thickness_mm: float
    width_mm: float
    length_mm: float
    grain: str = "unknown"  # x|y|z|unknown
    how_made: str = "solid"  # solid|panel|sweep|turned|upholstery|sheet|other
    curved: bool = False
    blank_thickness_mm: float | None = None
    blank_width_mm: float | None = None
    blank_length_mm: float | None = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    estimate_flag: str = "Guessed"  # Measured|Estimated|Guessed|Shaped from blank
    fill_ratio: float | None = None
    # In-memory only — never serialized
    solid_ref: Any = field(default=None, repr=False, compare=False)

    def blank_twl(self) -> tuple[float, float, float]:
        t = self.blank_thickness_mm if self.blank_thickness_mm is not None else self.thickness_mm
        w = self.blank_width_mm if self.blank_width_mm is not None else self.width_mm
        L = self.blank_length_mm if self.blank_length_mm is not None else self.length_mm
        return float(t), float(w), float(L)

    def finished_twl(self) -> tuple[float, float, float]:
        return float(self.thickness_mm), float(self.width_mm), float(self.length_mm)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("solid_ref", None)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PartRecord:
        if not d.get("id"):
            raise ValueError("part id required")
        qty = int(d.get("qty") or 0)
        if qty < 1:
            raise ValueError(f"part {d.get('id')}: qty must be >= 1")
        for key in ("thickness_mm", "width_mm", "length_mm"):
            if d.get(key) is None or float(d[key]) <= 0:
                raise ValueError(f"part {d.get('id')}: {key} must be > 0")
        return cls(
            id=str(d["id"]),
            name=str(d.get("name") or d["id"]),
            qty=qty,
            material=str(d.get("material") or "unknown"),
            thickness_mm=float(d["thickness_mm"]),
            width_mm=float(d["width_mm"]),
            length_mm=float(d["length_mm"]),
            grain=str(d.get("grain") or "unknown"),
            how_made=str(d.get("how_made") or "solid"),
            curved=bool(d.get("curved") or False),
            blank_thickness_mm=_opt_float(d.get("blank_thickness_mm")),
            blank_width_mm=_opt_float(d.get("blank_width_mm")),
            blank_length_mm=_opt_float(d.get("blank_length_mm")),
            notes=str(d.get("notes") or ""),
            tags=list(d.get("tags") or []),
            estimate_flag=str(d.get("estimate_flag") or ("Guessed" if not d.get("tags") else (d["tags"][0] if d.get("tags") else "Guessed"))),
            fill_ratio=_opt_float(d.get("fill_ratio")),
        )


def _opt_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    return float(v)


def load_parts(path: Path | str) -> list[PartRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "parts" in data:
        rows = data["parts"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("parts JSON must be a list or {parts:[...]}")
    return [PartRecord.from_dict(r) for r in rows]


def dump_parts(parts: list[PartRecord], path: Path | str, *, meta: dict[str, Any] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "furniture_cad.parts.v1",
        "parts": [p.to_dict() for p in parts],
    }
    if meta:
        payload["meta"] = meta
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def total_qty(parts: list[PartRecord]) -> int:
    return sum(p.qty for p in parts)
