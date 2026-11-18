"""Set-of-marks labeling — model returns enum labels only (no lengths)."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

LABEL_ENUM = (
    "drawer_front",
    "door",
    "open_bay",
    "top",
    "case_bottom_rail",
    "leg",
    "end_block",
    "back",
    "divider",
    "shelf",
    "pull",
    "none",
)


def render_set_of_marks(
    image: Any,
    regions: list[dict[str, Any]],
) -> Any:
    """Draw numbered overlays for candidate regions; return a PIL image."""
    from PIL import Image, ImageDraw, ImageFont

    if hasattr(image, "convert"):
        img = image.convert("RGB").copy()
    else:
        img = Image.fromarray(np.asarray(image)).convert("RGB")
    draw = ImageDraw.Draw(img)
    for r in regions:
        x0, y0, x1, y1 = r["bbox_px"]
        draw.rectangle([x0, y0, x1, y1], outline=(220, 40, 40), width=2)
        label = str(r["id"])
        draw.rectangle([x0, y0, x0 + 18, y0 + 14], fill=(220, 40, 40))
        draw.text((x0 + 3, y0 + 1), label, fill=(255, 255, 255))
    return img


def heuristic_labels(
    regions: list[dict[str, Any]],
    *,
    image_size: tuple[int, int],
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deterministic labels for offline tests / when the model is unavailable."""
    w, h = image_size
    profile = profile or {}
    case_top = profile.get("case_top_row")
    case_bot = profile.get("case_bottom_row")
    out: list[dict[str, Any]] = []
    for r in regions:
        x0, y0, x1, y1 = r["bbox_px"]
        cy = (y0 + y1) / 2
        cx = (x0 + x1) / 2
        bw, bh = x1 - x0, y1 - y0
        aspect = bw / max(1.0, bh)
        label = "none"
        conf = 0.55
        if case_top is not None and y1 <= case_top + 8 and aspect > 2.5:
            label, conf = "top", 0.7
        elif case_bot is not None and cy > case_bot:
            label, conf = "leg", 0.65
        elif aspect > 1.6 and bh < h * 0.25 and case_top is not None and cy > case_top:
            label, conf = "drawer_front", 0.6
        elif bh > h * 0.35 and bw < w * 0.45:
            label, conf = "door" if cx < w * 0.45 or cx > w * 0.55 else "open_bay", 0.55
        elif bw < w * 0.12 and bh > h * 0.2:
            label, conf = "end_block", 0.55
        out.append({**r, "label": label, "conf": conf, "label_source": "heuristic"})
    return out


def label_regions_with_model(
    marked_image: Any,
    regions: list[dict[str, Any]],
    *,
    api_key: str | None,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict[str, Any]] | None:
    """Ask Claude for labels keyed by overlay id. Returns None if no key / failure.

    The model must not return lengths — only ``{id, label, conf}``.
    """
    if not api_key:
        return None
    try:
        import anthropic
        import base64
        import io
        from PIL import Image
    except ImportError:
        return None

    if hasattr(marked_image, "save"):
        buf = io.BytesIO()
        marked_image.save(buf, format="JPEG", quality=85)
        data = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    else:
        return None

    prompt = (
        "You label furniture photo regions. For each numbered overlay, return ONLY a JSON array of "
        '{"id": <int>, "label": <enum>, "conf": <0-1>}. '
        f"label enum: {list(LABEL_ENUM)}. "
        "Do not return any lengths, sizes, or measurements. Unknown → label none."
    )
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    text = "".join(getattr(b, "text", "") for b in msg.content)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < 0:
        return None
    try:
        rows = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    by_id = {int(r["id"]): r for r in rows if "id" in r and "label" in r}
    out: list[dict[str, Any]] = []
    for r in regions:
        lab = by_id.get(int(r["id"]))
        if not lab or lab.get("label") not in LABEL_ENUM:
            out.append({**r, "label": "none", "conf": 0.3, "label_source": "model"})
        else:
            out.append(
                {
                    **r,
                    "label": lab["label"],
                    "conf": float(lab.get("conf") or 0.5),
                    "label_source": "model",
                }
            )
    return out
