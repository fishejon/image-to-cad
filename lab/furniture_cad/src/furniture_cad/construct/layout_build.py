"""Build a bay-aware layout tree from Perceive counts + style attrs.

Console stays a flat ``drawer_bank`` + ``open`` list. Credenza / sideboard forms
become ``bay`` / ``divider`` sequences so compile can emit V1, SH1, DR1 and
stacked drawers.
"""

from __future__ import annotations

from typing import Any


def _door_type(door_style: str) -> str:
    s = (door_style or "").lower()
    if "sliding" in s:
        return "sliding"
    return "hinged"


def _stacked(drawer_layout: str, doors: int, drawers: int) -> bool:
    s = (drawer_layout or "").lower()
    if "side" in s and "stack" not in s:
        return False
    if "stack" in s:
        return True
    # Multi-bay casegoods almost always stack drawers in one bay
    return doors > 0 and drawers > 1


def build_layout_children(
    *,
    drawers: int,
    doors: int,
    open_cubby: int,
    shelf: int,
    wall: float,
    reveal: float,
    bank_frac: float | None,
    drawer_layout: str = "",
    door_style: str = "",
    layout_facing: str = "",
) -> tuple[list[dict[str, Any]], str]:
    """Return (layout children, split axis)."""
    drawers = max(0, int(drawers))
    doors = max(0, int(doors))
    open_cubby = max(0, int(open_cubby))
    shelf = max(0, int(shelf))
    stacked = _stacked(drawer_layout, doors, drawers)
    dtype = _door_type(door_style)

    def front_spec() -> dict[str, Any]:
        return {"t": 19.0, "reveal": reveal, "corner": "square"}

    def door_spec(leaf_count: int = 1) -> dict[str, Any]:
        return {"type": dtype, "leaf_count": max(1, leaf_count), "t": 19.0, "reveal": reveal}

    def bank(*, rows: int, cols: int, align: str = "fill") -> dict[str, Any]:
        b: dict[str, Any] = {
            "kind": "drawer_bank",
            "rows": max(1, rows),
            "cols": max(1, cols),
            "front": front_spec(),
            "align": align,
        }
        if bank_frac is not None:
            b["bank_frac"] = float(bank_frac)
        return b

    # --- multi-bay: doors on the sides, drawers in the middle (sideboard) ---
    if doors >= 2 and drawers > 0:
        rows = drawers if stacked else 1
        cols = 1 if stacked else drawers
        shelves_per_door_bay = 1 if shelf >= 2 else 0
        door_stack: list[dict[str, Any]] = []
        if shelves_per_door_bay:
            door_stack.append({"kind": "shelf", "setback": wall})
        door_stack.append({"kind": "open", "setback": wall})
        mid_stack = [bank(rows=rows, cols=cols, align="fill")]
        children = [
            {"kind": "bay", "door": door_spec(1), "stack": door_stack},
            {"kind": "divider", "t": wall},
            {"kind": "bay", "stack": mid_stack},
            {"kind": "divider", "t": wall},
            {"kind": "bay", "door": door_spec(1), "stack": list(door_stack)},
        ]
        return children, "x"

    # --- two-bay: one door bay + drawer(/cubby) bay (credenza) ---
    if doors == 1 and drawers > 0:
        rows = drawers if stacked else 1
        cols = 1 if stacked else drawers
        align = "top" if open_cubby > 0 else "fill"
        drawer_stack: list[dict[str, Any]] = [bank(rows=rows, cols=cols, align=align)]
        if open_cubby > 0:
            drawer_stack.append({"kind": "open", "setback": wall})
        door_bay: dict[str, Any] = {
            "kind": "bay",
            "door": door_spec(1),
            "stack": [{"kind": "open", "setback": wall}],
        }
        drawer_bay: dict[str, Any] = {"kind": "bay", "stack": drawer_stack}
        left_is_door = "right" not in (layout_facing or "").lower()
        if "stacked_right" in (drawer_layout or "").lower():
            left_is_door = True
        if left_is_door:
            children = [door_bay, {"kind": "divider", "t": wall}, drawer_bay]
        else:
            children = [drawer_bay, {"kind": "divider", "t": wall}, door_bay]
        return children, "x"

    # --- single-bay / console legacy (flat children) ---
    children = []
    if drawers > 0:
        if stacked:
            children.append(bank(rows=drawers, cols=1, align="top" if open_cubby else "fill"))
        else:
            b = bank(rows=1, cols=drawers, align="fill")
            # Preserve legacy field name used by older IR / patch ops
            b["cols"] = drawers
            children.append(b)
    if open_cubby > 0 or (shelf > 0 and doors == 0):
        children.append({"kind": "open", "setback": wall})
    if not children:
        children.append({"kind": "open", "setback": wall})
    return children, "z"
