"""Perceive v2 detail attributes — fixed enums + majority self-consistency."""

from __future__ import annotations

from collections import Counter
from typing import Any

# Spec WP3 enumerated vocabulary
ATTR_ENUMS: dict[str, tuple[str, ...]] = {
    "leg_style": ("square", "tapered", "flared", "two_profile_flared", "cabriole", "turned", "none", "unknown"),
    "foot_style": ("square", "tapered", "pad", "spade", "bun", "none", "unknown"),
    "end_profile": ("flat", "rounded_bottom", "swept", "swept_leaning", "pill", "wishbone", "unknown"),
    "top_edge": ("square", "eased", "roundover", "chamfer", "ogee", "bullnose", "unknown"),
    "drawer_front_style": ("flush_inset", "inset_beaded", "overlay", "shaker", "slab", "unknown"),
    "pull_style": ("none", "knob", "bar", "cup", "integrated", "unknown"),
    "back_style": ("thin_panel", "frame_panel", "solid", "open", "unknown"),
    "visible_joinery": (
        "through_dovetail",
        "half_blind_dovetail",
        "box_joint",
        "wedged_tenon",
        "finger_joint",
        "mortise_tenon",
        "none",
        "unknown",
    ),
    "grain_direction": ("length", "vertical", "cross", "unknown"),
}


def majority_vote(samples: list[dict[str, Any]], *, keys: list[str] | None = None) -> dict[str, Any]:
    """Accept majority label per key; mark ``ask`` when there is no majority."""
    keys = keys or list(ATTR_ENUMS.keys())
    out: dict[str, Any] = {"attrs": {}, "asks": [], "ties": []}
    for key in keys:
        vals = [str(s.get(key) or "unknown") for s in samples if s.get(key) is not None]
        if not vals:
            out["attrs"][key] = "unknown"
            continue
        counts = Counter(vals)
        top, n = counts.most_common(1)[0]
        if n > len(vals) / 2:
            out["attrs"][key] = top
        else:
            out["attrs"][key] = "unknown"
            out["ties"].append(key)
            choices = [c for c, _ in counts.most_common(2)]
            out["asks"].append(
                {
                    "key": key,
                    "prompt": f"Which {key}? (no majority across samples)",
                    "choices": choices[:2],
                }
            )
    return out


def normalize_attrs(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw or {}
    out: dict[str, str] = {}
    for key, allowed in ATTR_ENUMS.items():
        v = str(raw.get(key) or "unknown").lower().strip().replace(" ", "_").replace("-", "_")
        # Map legacy end_form / leg_style aliases
        if key == "end_profile" and v in ("leaning", "swept_leaning", "flat"):
            pass
        if key == "leg_style" and v == "two_profile":
            v = "two_profile_flared"
        out[key] = v if v in allowed else "unknown"
    # Optional wood guess
    if raw.get("wood_guess"):
        out["wood_guess"] = str(raw["wood_guess"])
        out["wood_guess_conf"] = str(raw.get("wood_guess_conf") or raw.get("wood_conf") or "")
    return out
