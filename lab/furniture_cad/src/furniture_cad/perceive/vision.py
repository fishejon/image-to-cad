"""Vision Perceive — observation.v1 via Anthropic (P3)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from furniture_cad.perceive.observe import perceive_casegood
from furniture_cad.tools.loop import _approx_cost_usd, _photo_content_block


COUNT_KEYS = ("drawer", "door", "shelf", "leg", "open_cubby", "pull", "end_block_carved")

SYSTEM = """You are a furniture perception module. Look at the photo and return ONLY valid JSON
matching observation.v1 (no markdown). Count visible features carefully.
Schema:
{
  "schema": "observation.v1",
  "class": "casegood.console|casegood.bookcase|casegood.sideboard|casegood.cabinet|other",
  "counts": {
    "drawer": int, "door": int, "shelf": int, "leg": int,
    "open_cubby": int, "pull": int, "end_block_carved": int
  },
  "components": [{"id": str, "type": str, "count": int, "style": str, "conf": 0-1}],
  "unknowns": [{"q": str, "default": any, "ask": bool}],
  "end_form": "flat|leaning|swept|swept_leaning|unknown",
  "leg_style": "square|tapered|flared|two_profile_flared|none|unknown"
}
Rules:
- Do not invent pulls if none are visible.
- Prefer lower counts when unsure — except legs: freestanding casegoods almost always have 4 legs;
  if only two front legs are visible, still count leg=4 (rear legs inferred).
- end_block_carved = carved/sculpted solid wood end panels (not plain box ends).
- Open recessed shelf bay above drawers = open_cubby=1 AND shelf=1 (the bay floor/ceiling is the shelf).
- Temperature 0."""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def _norm_counts(raw: dict[str, Any] | None) -> dict[str, int]:
    raw = raw or {}
    return {k: int(raw.get(k) or 0) for k in COUNT_KEYS}


def _counts_pass(client: Any, model: str, image_block: dict[str, Any]) -> dict[str, int]:
    resp = client.messages.create(
        model=model,
        max_tokens=256,
        system=(
            "Return ONLY JSON counts: "
            '{"drawer":n,"door":n,"shelf":n,"leg":n,"open_cubby":n,"pull":n,"end_block_carved":n}'
        ),
        messages=[
            {
                "role": "user",
                "content": [
                    image_block,
                    {
                        "type": "text",
                        "text": (
                            "Count drawers, doors, shelves, legs, open cubbies, pulls, "
                            "and carved end blocks. Freestanding pieces: leg=4 even if only "
                            "front legs are visible. Open shelf bay above drawers → "
                            "open_cubby=1 and shelf=1."
                        ),
                    },
                ],
            }
        ],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    return _norm_counts(_extract_json(text)), resp


def perceive_vision(
    intake: dict[str, Any],
    *,
    class_hint: str = "casegood.console",
    known_mm: dict[str, float] | None = None,
    photo: Path | str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Two-pass vision observation. Falls back to heuristic if no key/photo."""
    base = perceive_casegood(intake, class_hint=class_hint, known_mm=known_mm)
    path = Path(photo) if photo else Path(intake.get("path") or "")
    key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("FURNITURE_CAD_ANTHROPIC_KEY")
    if not key or not path.is_file():
        base["meta"] = {
            **(base.get("meta") or {}),
            "perceive": "heuristic_fallback",
            "reason": "no_key_or_photo",
        }
        return base

    import anthropic

    model = model or os.environ.get("FURNITURE_CAD_PERCEIVE_MODEL") or os.environ.get(
        "FURNITURE_CAD_MODEL", "claude-haiku-4-5"
    )
    client = anthropic.Anthropic(api_key=key)
    image_block = _photo_content_block(path)
    if not image_block:
        base["meta"] = {
            **(base.get("meta") or {}),
            "perceive": "heuristic_fallback",
            "reason": "bad_image",
        }
        return base

    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    image_block,
                    {
                        "type": "text",
                        "text": (
                            f"Class hint: {class_hint}. Known overall mm: {known_mm or {}}. "
                            "Return observation JSON."
                        ),
                    },
                ],
            }
        ],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
    data = _extract_json(text)
    counts1 = _norm_counts(data.get("counts"))
    counts2, resp2 = _counts_pass(client, model, image_block)

    unknowns = list(data.get("unknowns") or [])
    # Drop heuristic "does it have drawers?" when vision answered.
    unknowns = [u for u in unknowns if "drawers" not in str(u.get("q") or "").lower()]
    # Reconcile disagreement:
    # - pull/door: min (don't invent hardware)
    # - end_block_carved / open_cubby / shelf: max (easy to miss from one pass)
    # - else: dedicated counts pass (pass2)
    # Always ask_user on disagreement.
    reconciled: dict[str, int] = {}
    for k in COUNT_KEYS:
        a, b = counts1.get(k, 0), counts2.get(k, 0)
        if a != b:
            if k in ("pull", "door"):
                chosen = min(a, b)
            elif k in ("end_block_carved", "open_cubby", "shelf"):
                chosen = max(a, b)
            else:
                chosen = b
            unknowns.append(
                {
                    "q": f"How many {k}s? (pass1={a}, pass2={b})",
                    "default": chosen,
                    "ask": True,
                }
            )
            reconciled[k] = chosen
        else:
            reconciled[k] = b
    # Freestanding casegood: if either pass saw ≥4 legs, keep 4.
    if str(data.get("class") or class_hint).startswith("casegood") and max(
        counts1.get("leg", 0), reconciled.get("leg", 0)
    ) >= 4:
        reconciled["leg"] = 4
    # Front-on photos often miss end sculpture: infer carved ends from end_form,
    # or from console class when end_form is unknown.
    end_form = str(data.get("end_form") or "").lower().strip()
    class_name = str(data.get("class") or class_hint).lower()
    if reconciled.get("end_block_carved", 0) == 0:
        swept = any(x in end_form for x in ("swept", "leaning"))
        console_unknown = "console" in class_name and end_form in ("", "unknown", "none")
        if swept or console_unknown:
            reconciled["end_block_carved"] = 2
            unknowns.append(
                {
                    "q": "Carved end blocks present (inferred from end_form/class)?",
                    "default": 2,
                    "ask": True,
                }
            )
    counts2 = reconciled

    components = data.get("components") or []
    if not components:
        for typ, n in counts2.items():
            if n > 0:
                components.append(
                    {
                        "id": f"c_{typ}",
                        "type": typ,
                        "count": n,
                        "conf": 0.7,
                        "attrs": {},
                        "evidence": ["vision_pass2"],
                    }
                )

    usage1 = getattr(resp, "usage", None)
    usage2 = getattr(resp2, "usage", None)
    in_tok = int(getattr(usage1, "input_tokens", 0) or 0) + int(getattr(usage2, "input_tokens", 0) or 0)
    out_tok = int(getattr(usage1, "output_tokens", 0) or 0) + int(getattr(usage2, "output_tokens", 0) or 0)
    spend = _approx_cost_usd(input_tokens=in_tok, output_tokens=out_tok)

    return {
        "schema": "observation.v1",
        "class": data.get("class") or class_hint,
        "views": base.get("views") or [],
        "components": components,
        "dims_mm": base.get("dims_mm") or {},
        "counts": counts2,
        "counts_pass1": counts1,
        "end_form": data.get("end_form"),
        "leg_style": data.get("leg_style"),
        "unknowns": unknowns,
        "meta": {
            "perceive": "vision_v1",
            "model": model,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "spend_usd_approx": round(spend, 4),
        },
    }


def feature_counts_from_observation(obs: dict[str, Any]) -> dict[str, int]:
    counts = obs.get("counts")
    if isinstance(counts, dict) and counts:
        return _norm_counts(counts)
    out = {k: 0 for k in COUNT_KEYS}
    for c in obs.get("components") or []:
        t = str(c.get("type") or "")
        n = int(c.get("count") or 1)
        if t in out:
            out[t] += n
        elif t == "drawer_bank":
            out["drawer"] += n
    return out
