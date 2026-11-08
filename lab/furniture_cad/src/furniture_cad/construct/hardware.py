"""Hardware registry + list rows (Phase 2)."""

from __future__ import annotations

from typing import Any

REGISTRY: dict[str, dict[str, Any]] = {
    "side_mount_250": {
        "id": "side_mount_250",
        "kind": "drawer_slide",
        "length_mm": 250,
        "pair": True,
        "vendor_sku": "generic-side-250",
    },
    "side_mount_350": {
        "id": "side_mount_350",
        "kind": "drawer_slide",
        "length_mm": 350,
        "pair": True,
        "vendor_sku": "generic-side-350",
    },
    "euro_hinge": {
        "id": "euro_hinge",
        "kind": "hinge",
        "overlay": "full",
        "pair_per_door": 2,
        "vendor_sku": "generic-euro",
    },
    "shelf_pin_5mm": {
        "id": "shelf_pin_5mm",
        "kind": "shelf_pin",
        "diameter_mm": 5,
        "vendor_sku": "generic-pin-5",
    },
    "pull_128": {
        "id": "pull_128",
        "kind": "pull",
        "cc_mm": 128,
        "vendor_sku": "generic-pull-128",
    },
}


def lookup(hw_id: str) -> dict[str, Any]:
    if hw_id not in REGISTRY:
        raise KeyError(f"unknown hardware id: {hw_id}")
    return dict(REGISTRY[hw_id])


def hardware_list_from_ir(ir: dict[str, Any]) -> dict[str, Any]:
    """Collect hardware references from IR bays / doors."""
    rows: list[dict[str, Any]] = []
    root = ir.get("root") or {}
    for bay in root.get("bays") or []:
        slide = (bay or {}).get("slide")
        n = int((bay or {}).get("n") or 1) if (bay or {}).get("kind") == "drawer_bank" else 0
        if slide and n:
            info = lookup(slide) if slide in REGISTRY else {"id": slide, "kind": "drawer_slide", "unknown": True}
            qty = n * (2 if info.get("pair") else 1)
            rows.append({**info, "qty": qty, "from": "bay.slide"})
        front = (bay or {}).get("front") or {}
        if front.get("pull"):
            info = lookup(front["pull"]) if front["pull"] in REGISTRY else {"id": front["pull"], "unknown": True}
            rows.append({**info, "qty": n or 1, "from": "bay.front.pull"})
    return {"schema": "hardware_list.v1", "items": rows, "count": len(rows)}
