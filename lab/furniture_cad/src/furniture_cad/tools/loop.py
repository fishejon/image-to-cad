"""CLI tool-use runner: offline tool scripts or Messages API loop.

R1: photo image blocks, real render/check/compare, known-size targets.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

from furniture_cad.tools.contract import anthropic_tools, limits as contract_limits, load_contract, tool_names
from furniture_cad.tools.handlers import ToolContext, dispatch

# Prefer app aliases (same as browser Create); override with FURNITURE_CAD_MODEL.
DEFAULT_MODEL = os.environ.get("FURNITURE_CAD_MODEL", "claude-haiku-4-5")

# Few-shot for open MCM casegoods — scale W/D/H to the user-known size.
CASEGOOD_FEWSHOT = r'''
Example casegood (set W,D,H from the known overall size in mm):
```
W, D, H = 1219.0, 305.0, 1803.0
post_s, shelf_t, foot_h, overhang, clearance, fin_w = 32.0, 18.0, 64.0, 90.0, 48.0, 70.0
run_t = post_s + 8.0
shelf_w = W
post_h = H - foot_h
bay = (post_h - clearance - 5 * shelf_t) / 4.0
hx, hy = W / 2.0 - overhang - post_s / 2.0, D / 2.0 - 18.0
posts = [Pos(sx * hx, sy * hy, foot_h + post_h / 2.0) * Box(post_s, post_s, post_h)
         for sx in (-1, 1) for sy in (-1, 1)]
shelves = [Pos(0, 0, foot_h + clearance + shelf_t / 2.0 + i * (shelf_t + bay)) * Box(shelf_w, D, shelf_t)
           for i in range(5)]
feet = [
  Pos(-hx, 0, foot_h / 2.0) * Box(run_t, D, foot_h),
  Pos(hx, 0, foot_h / 2.0) * Box(run_t, D, foot_h),
  Pos(-hx + run_t / 2.0 + fin_w / 2.0, 0, foot_h * 0.4) * Box(fin_w, D * 0.55, foot_h * 0.8),
  Pos(hx - run_t / 2.0 - fin_w / 2.0, 0, foot_h * 0.4) * Box(fin_w, D * 0.55, foot_h * 0.8),
]
assembly = Compound(children=posts + shelves + feet)
parts = [
  PartRecord(id='post', name='Vertical post', qty=4, material='walnut', thickness_mm=36, width_mm=36, length_mm=H-foot_h, grain='z', how_made='solid'),
  PartRecord(id='shelf', name='Shelf board', qty=5, material='walnut', thickness_mm=20, width_mm=D, length_mm=W, grain='x', how_made='solid'),
  PartRecord(id='sled_foot', name='Sled foot', qty=2, material='walnut', thickness_mm=44, width_mm=70, length_mm=D, grain='y', how_made='solid', curved=True),
]
```
'''.strip()

SYSTEM = f"""You are a furniture CAD worker. You MUST use tools — never answer with text only.

Procedure each job:
1) Read the photo + known overall size (mm). Classify: casegood | chair | stool | other.
2) List the visible parts mentally, then build(script) with assembly= set (solids export required).
3) render(views=["front","side","iso"]) and look at the returned images.
4) check(targets_mm) with the known W/D/H; compare() against the photo (IoU + overlay).
5) If check/compare fail, fix with another build, then render/check/compare again.
6) lists() when the solid is acceptable.
Optional: ask_user only for missing material/hidden structure — never for overall size if given.

Object class (match the PHOTO):
- Open shelving / bookcase / etagere → CASEGOOD with Box, Pos, Compound (post, shelf, sled_foot). Never chair parts.
- Chair / stool → four_leg_chair({{...}}) or stool({{...}}); assembly = result['assembly'].

{CASEGOOD_FEWSHOT}

Inside build(script): block, blocks, four_leg_chair, stool, PartRecord, Box, Pos, Compound.
PartRecord fields (mm): id, name, qty, material, thickness_mm, width_mm, length_mm; optional grain, how_made, curved, blanks.
At most three render images are returned per round. Keep scripts short. Ending without build+assembly+render+lists is a failure."""


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def resolve_limits(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = contract_limits()
    out = {
        "max_rounds": _env_int("FURNITURE_CAD_MAX_ROUNDS", int(base.get("max_rounds", 8))),
        "max_tokens_per_request": _env_int(
            "FURNITURE_CAD_MAX_TOKENS", int(base.get("max_tokens_per_request", 16000))
        ),
        "max_spend_usd_per_job": _env_float(
            "FURNITURE_CAD_MAX_SPEND_USD_PER_JOB", float(base.get("max_spend_usd_per_job", 2.0))
        ),
        "max_spend_usd_per_day": _env_float(
            "FURNITURE_CAD_MAX_SPEND_USD_PER_DAY", float(base.get("max_spend_usd_per_day", 25.0))
        ),
        "max_wall_time_s": _env_int("FURNITURE_CAD_MAX_WALL_TIME_S", int(base.get("max_wall_time_s", 900))),
        "max_images_per_round": _env_int("FURNITURE_CAD_MAX_IMAGES_PER_ROUND", int(base.get("max_images_per_round", 3))),
    }
    if overrides:
        out.update({k: v for k, v in overrides.items() if v is not None})
    return out


def _approx_cost_usd(*, input_tokens: int, output_tokens: int) -> float:
    # Rough Sonnet-class estimate for spend caps; not billing-accurate.
    return (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0


def _downscale_image_bytes(data: bytes, *, max_edge: int = 1024) -> tuple[bytes, str]:
    """Return (jpeg_bytes, media_type), downscaled to max_edge on the long side."""
    from io import BytesIO

    from PIL import Image, ImageOps

    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    elif img.mode == "L":
        img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, float(max_edge) / float(max(w, h)))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.BILINEAR)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue(), "image/jpeg"


def _photo_content_block(path: Path, *, max_edge: int = 1024) -> dict[str, Any] | None:
    """Anthropic image block from a local photo path, or None if unreadable."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data:
        return None
    try:
        data, mime = _downscale_image_bytes(data, max_edge=max_edge)
    except Exception:
        mime, _ = mimetypes.guess_type(str(path))
        if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            mime = "image/jpeg"
        if len(data) > 4_000_000:
            return None
    b64 = base64.standard_b64encode(data).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": mime, "data": b64},
    }


def _format_known_size(targets: dict[str, float]) -> str:
    if not targets:
        return "Known overall size: not provided — ask_user only if scale is ambiguous."
    parts = []
    labels = {"w": "width", "d": "depth", "h": "height"}
    for k in ("w", "d", "h"):
        if k in targets and targets[k]:
            parts.append(f"{labels[k]}={float(targets[k]):.0f} mm")
    return "Known overall size (from user, authoritative): " + ", ".join(parts) + "."


def _user_content(prompt: str, photo: Path | None, targets: dict[str, float] | None = None) -> str | list[dict[str, Any]]:
    """Labeled photo + known size + brief for the first Messages turn."""
    targets = targets or {}
    text = (
        f"{prompt}\n\n"
        f"{_format_known_size(targets)}\n"
        "Image label: front (primary reference).\n"
        "Procedure: classify from the PHOTO → build(assembly=) scaled to known size → "
        "render front/side/iso → check(targets_mm) → compare → lists. Fix if check/compare fail."
    )
    if not photo or not photo.is_file():
        return text
    img = _photo_content_block(photo)
    if not img:
        return text
    return [
        {"type": "text", "text": "Reference photo (front):"},
        img,
        {"type": "text", "text": text},
    ]


def _tool_result_content(result: dict[str, Any], *, max_images: int = 3) -> str | list[dict[str, Any]]:
    """JSON tool result, optionally with downscaled PNG/JPEG image blocks (≤ max_images)."""
    paths = list(result.get("image_paths") or [])[:max_images]
    payload = {k: v for k, v in result.items() if k != "image_paths"}
    text = json.dumps(payload)
    if not paths:
        return text
    blocks: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for p in paths:
        path = Path(p)
        if not path.is_file():
            continue
        block = _photo_content_block(path, max_edge=768)
        if block:
            blocks.append({"type": "text", "text": f"image:{path.name}"})
            blocks.append(block)
    return blocks if len(blocks) > 1 else text


def run_tool_script(ctx: ToolContext, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute a JSON list of {tool, input} without the model (tests / dry-run)."""
    known = set(tool_names())
    results: list[dict[str, Any]] = []
    for i, step in enumerate(calls):
        name = str(step.get("tool") or step.get("name") or "")
        args = step.get("input") or step.get("arguments") or {}
        if name not in known:
            results.append({"index": i, "tool": name, "result": {"ok": False, "error": f"unknown tool {name!r}"}})
            continue
        if not isinstance(args, dict):
            results.append({"index": i, "tool": name, "result": {"ok": False, "error": "input must be object"}})
            continue
        result = dispatch(ctx, name, args)
        results.append({"index": i, "tool": name, "result": result})
        if result.get("needs_user"):
            break
    return results


def run_messages_loop(
    ctx: ToolContext,
    *,
    prompt: str,
    limits: dict[str, Any],
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Messages API tool-use loop. Stops on end_turn, ask_user, or caps."""
    try:
        import anthropic
    except ImportError as e:
        raise SystemExit("anthropic package required for live loop: pip install anthropic") from e

    key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("FURNITURE_CAD_ANTHROPIC_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY (or FURNITURE_CAD_ANTHROPIC_KEY) required for live loop")

    client = anthropic.Anthropic(api_key=key)
    tools = anthropic_tools()
    photo = ctx.reference_photo if isinstance(ctx.reference_photo, Path) else None
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _user_content(prompt, photo, ctx.targets_mm)}
    ]
    spent = 0.0
    started = time.monotonic()
    rounds = 0
    max_rounds = int(limits["max_rounds"])
    max_spend = float(limits["max_spend_usd_per_job"])
    max_wall = float(limits["max_wall_time_s"])
    max_tokens = int(limits["max_tokens_per_request"])
    max_images = int(limits.get("max_images_per_round", 3))
    stop_reason = "incomplete"

    while rounds < max_rounds:
        if time.monotonic() - started > max_wall:
            stop_reason = "wall_time"
            break
        if spent >= max_spend:
            stop_reason = "spend_cap"
            break

        rounds += 1
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            spent += _approx_cost_usd(
                input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            )

        content = resp.content
        messages.append({"role": "assistant", "content": content})

        tool_uses = [b for b in content if getattr(b, "type", None) == "tool_use"]
        built = bool(ctx.parts)
        has_assembly = bool(ctx.last_build and (ctx.last_build.get("has_assembly") or ctx.last_build.get("exported")))
        rendered = bool(ctx.last_renders)
        if not tool_uses:
            stop_reason = getattr(resp, "stop_reason", None) or "end_turn"
            if (not built or not has_assembly or not rendered) and rounds < max_rounds:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Not done. Use the PHOTO + known size. "
                            "build with assembly= (casegood Box/Pos/Compound if bookshelf), "
                            "then render([\"front\",\"side\",\"iso\"]), check(targets_mm), compare(), lists()."
                        ),
                    }
                )
                continue
            break

        tool_results: list[dict[str, Any]] = []
        needs_user = False
        for block in tool_uses:
            name = block.name
            args = block.input if isinstance(block.input, dict) else {}
            # Inject known targets into check if the model omitted them
            if name == "check" and ctx.targets_mm and not (args.get("targets_mm")):
                args = {**args, "targets_mm": dict(ctx.targets_mm)}
            result = dispatch(ctx, name, args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": _tool_result_content(result, max_images=max_images),
                    "is_error": not bool(result.get("ok")),
                }
            )
            if result.get("needs_user"):
                needs_user = True
        messages.append({"role": "user", "content": tool_results})
        if needs_user:
            stop_reason = "needs_user"
            break
        has_assembly = bool(ctx.last_build and (ctx.last_build.get("has_assembly") or ctx.last_build.get("exported")))
        rendered = bool(ctx.last_renders)
        if ctx.last_plan and ctx.parts and not has_assembly and rounds < max_rounds:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "lists() ran but assembly was never set — no STL. Rebuild with "
                        "assembly = result['assembly'] (chair/stool) or Compound(...) (casegood), then render/check/lists."
                    ),
                }
            )
            continue
        if ctx.parts and has_assembly and ctx.last_plan and not rendered and rounds < max_rounds:
            messages.append(
                {
                    "role": "user",
                    "content": 'Call render(views=["front","side","iso"]) then check and compare before finishing.',
                }
            )
            continue
        if (
            ctx.parts
            and has_assembly
            and rendered
            and not ctx.last_plan
            and rounds < max_rounds
            and ctx.last_check is not None
        ):
            # Dims may pass while IoU is still Wrong — still emit lists so the project is complete.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "You have assembly + renders + check. Call lists() now to finish. "
                        "Further likeness fixes can be a later round if spend remains."
                    ),
                }
            )
            continue
        # Done when parts + assembly + render + lists
        if ctx.parts and has_assembly and ctx.last_plan and rendered:
            stop_reason = "end_turn"
            break
    else:
        stop_reason = "max_rounds"

    built = bool(ctx.parts)
    listed = bool(ctx.last_plan)
    has_assembly = bool(ctx.last_build and (ctx.last_build.get("has_assembly") or ctx.last_build.get("exported")))
    exported = bool(ctx.last_build and ctx.last_build.get("exported"))
    rendered = bool(ctx.last_renders)
    ok = stop_reason == "needs_user" or (
        stop_reason == "end_turn" and built and listed and has_assembly and exported and rendered
    )
    reason = stop_reason
    if stop_reason == "end_turn" and not ok:
        if not built:
            reason = "end_turn_no_build"
        elif not has_assembly or not exported:
            reason = "end_turn_no_assembly"
        elif not rendered:
            reason = "end_turn_no_render"
        elif not listed:
            reason = "end_turn_no_lists"
    return {
        "ok": ok,
        "mode": "live",
        "stop_reason": reason,
        "rounds": rounds,
        "spent_usd_approx": round(spent, 4),
        "limits": limits,
        "parts_count": len(ctx.parts),
        "log": ctx.log,
        "last_build": ctx.last_build,
        "last_plan_totals": (ctx.last_plan or {}).get("totals"),
        "last_check": ctx.last_check,
        "last_compare": ctx.last_compare,
        "renders": dict(ctx.last_renders),
        "had_photo": bool(photo and photo.is_file()),
        "targets_mm": dict(ctx.targets_mm),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="furniture_cad tool-use runner (Phase 1)")
    p.add_argument("--work", type=Path, default=Path("out/run"), help="job workspace directory")
    p.add_argument("--photo", type=Path, default=None, help="reference photo path (sent as image block)")
    p.add_argument(
        "--known-mm",
        nargs=3,
        type=float,
        metavar=("W", "D", "H"),
        default=None,
        help="user-known overall size in mm (width depth height)",
    )
    p.add_argument("--prompt", type=str, default=None, help="user prompt for live Messages loop")
    p.add_argument(
        "--script",
        type=Path,
        default=None,
        help="JSON file: list of {tool, input} for offline dry-run (no API)",
    )
    p.add_argument("--model", type=str, default=DEFAULT_MODEL)
    p.add_argument("--max-rounds", type=int, default=None)
    p.add_argument("--max-spend", type=float, default=None, help="USD cap per job")
    p.add_argument("--call", nargs=2, metavar=("TOOL", "JSON"), help="dispatch one tool and exit")
    p.add_argument("--contract", action="store_true", help="print frozen tool contract summary and exit")
    p.add_argument(
        "--freeze-set",
        nargs="*",
        metavar="ID",
        help="run offline oracle scripts (hand-tuned; not baseline A). alias: --freeze-set",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.contract:
        c = load_contract()
        print(json.dumps({"schema": c["schema"], "tools": tool_names(), "limits": c.get("limits")}, indent=2))
        return 0

    if args.freeze_set is not None:
        from furniture_cad.tools.oracle_set import ORACLE_PIECES, oracle_tool_calls

        ids = list(args.freeze_set) if args.freeze_set else list(ORACLE_PIECES.keys())
        summary: dict[str, Any] = {"mode": "oracle_set", "pieces": {}}
        ok_all = True
        for pid in ids:
            if pid not in ORACLE_PIECES:
                summary["pieces"][pid] = {"ok": False, "error": "unknown oracle piece"}
                ok_all = False
                continue
            meta = ORACLE_PIECES[pid]
            piece_dir = Path(args.work) / pid
            pctx = ToolContext(work_dir=piece_dir)
            results = run_tool_script(pctx, oracle_tool_calls(pid))
            build_ok = bool(results and results[0]["result"].get("ok"))
            lists_ok = bool(len(results) > 1 and results[1]["result"].get("ok"))
            exported = bool((pctx.last_build or {}).get("exported"))
            piece_ok = build_ok and lists_ok and exported and len(pctx.parts) == meta["expect_types"]
            if sum(p.qty for p in pctx.parts) != meta["expect_pieces"]:
                piece_ok = False
            summary["pieces"][pid] = {
                "ok": piece_ok,
                "build_ok": build_ok,
                "lists_ok": lists_ok,
                "exported": exported,
                "part_types": len(pctx.parts),
                "piece_count": sum(p.qty for p in pctx.parts),
                "expect_types": meta["expect_types"],
                "expect_pieces": meta["expect_pieces"],
                "totals": (pctx.last_plan or {}).get("totals"),
                "hand_check": meta.get("hand_check"),
                "work": str(piece_dir),
            }
            ok_all = ok_all and piece_ok
        out = Path(args.work) / "freeze_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0 if ok_all else 1

    lim = resolve_limits(
        {
            "max_rounds": args.max_rounds,
            "max_spend_usd_per_job": args.max_spend,
        }
    )
    ctx = ToolContext(work_dir=args.work)
    if args.photo:
        ctx.reference_photo = Path(args.photo)
    if args.known_mm:
        ctx.targets_mm = {"w": float(args.known_mm[0]), "d": float(args.known_mm[1]), "h": float(args.known_mm[2])}

    if args.call:
        name, raw = args.call
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"invalid JSON input: {e}", file=sys.stderr)
            return 2
        if not isinstance(payload, dict):
            print("tool input must be a JSON object", file=sys.stderr)
            return 2
        result = dispatch(ctx, name, payload)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.script:
        calls = json.loads(Path(args.script).read_text(encoding="utf-8"))
        if not isinstance(calls, list):
            print("--script must be a JSON array of tool calls", file=sys.stderr)
            return 2
        results = run_tool_script(ctx, calls)
        summary = {
            "mode": "offline",
            "work": str(ctx.work_dir),
            "results": results,
            "parts_count": len(ctx.parts),
            "last_build": ctx.last_build,
            "last_plan_totals": (ctx.last_plan or {}).get("totals"),
        }
        out = ctx.work_dir / "run_summary.json"
        out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        ok = all(r["result"].get("ok") for r in results) or bool(ctx.parts)
        return 0 if ok else 1

    if not args.prompt:
        print("provide --prompt for live loop, or --script / --call / --contract", file=sys.stderr)
        return 2

    summary = run_messages_loop(ctx, prompt=args.prompt, limits=lim, model=args.model)
    summary["mode"] = "messages"
    summary["work"] = str(ctx.work_dir)
    out = ctx.work_dir / "run_summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
