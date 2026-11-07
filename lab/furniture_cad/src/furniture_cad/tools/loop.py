"""CLI tool-use runner: offline tool scripts or Messages API loop.

Phase 1: prove build + lists. render/check/compare stub until Phase 2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from furniture_cad.tools.contract import anthropic_tools, limits as contract_limits, load_contract, tool_names
from furniture_cad.tools.handlers import ToolContext, dispatch

# Prefer app aliases (same as browser Create); override with FURNITURE_CAD_MODEL.
DEFAULT_MODEL = os.environ.get("FURNITURE_CAD_MODEL", "claude-haiku-4-5")

SYSTEM = """You are a furniture CAD worker. Use tools to build a parts model and cut/material lists.
Inside build(script) you may use: block(name), blocks, four_leg_chair(params), stool(params), PartRecord, Box, Pos, Compound.
PartRecord / part dict fields (mm): id, name, qty, material, thickness_mm, width_mm, length_mm; optional grain, how_made, curved, blank_thickness_mm, blank_width_mm, blank_length_mm.
Script must set `parts = [...]`. Optionally set `assembly` (a solid) for STL/STEP export.
Prefer four_leg_chair({...}) then derive parts from params when building chairs.
After a successful build, call lists(). Use measure() to verify dims. ask_user only when stuck on scale/material.
Do not invent tools. Keep scripts short. Fix tool errors on the next round."""


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
    }
    if overrides:
        out.update({k: v for k, v in overrides.items() if v is not None})
    return out


def _approx_cost_usd(*, input_tokens: int, output_tokens: int) -> float:
    # Rough Sonnet-class estimate for spend caps; not billing-accurate.
    return (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 15.0


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
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    spent = 0.0
    started = time.monotonic()
    rounds = 0
    max_rounds = int(limits["max_rounds"])
    max_spend = float(limits["max_spend_usd_per_job"])
    max_wall = float(limits["max_wall_time_s"])
    max_tokens = int(limits["max_tokens_per_request"])
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
        if not tool_uses:
            stop_reason = getattr(resp, "stop_reason", None) or "end_turn"
            break

        tool_results: list[dict[str, Any]] = []
        needs_user = False
        for block in tool_uses:
            name = block.name
            args = block.input if isinstance(block.input, dict) else {}
            result = dispatch(ctx, name, args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                    "is_error": not bool(result.get("ok")),
                }
            )
            if result.get("needs_user"):
                needs_user = True
        messages.append({"role": "user", "content": tool_results})
        if needs_user:
            stop_reason = "needs_user"
            break
        if getattr(resp, "stop_reason", None) == "end_turn" and not tool_uses:
            stop_reason = "end_turn"
            break
    else:
        stop_reason = "max_rounds"

    return {
        "ok": stop_reason in ("end_turn", "needs_user") or bool(ctx.parts),
        "stop_reason": stop_reason,
        "rounds": rounds,
        "spent_usd_approx": round(spent, 4),
        "limits": limits,
        "parts_count": len(ctx.parts),
        "log": ctx.log,
        "last_build": ctx.last_build,
        "last_plan_totals": (ctx.last_plan or {}).get("totals"),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="furniture_cad tool-use runner (Phase 1)")
    p.add_argument("--work", type=Path, default=Path("out/run"), help="job workspace directory")
    p.add_argument("--photo", type=Path, default=None, help="optional reference photo path (stored on context)")
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
        help="run offline freeze scripts (default: chair_04 chair_02 case_01)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.contract:
        c = load_contract()
        print(json.dumps({"schema": c["schema"], "tools": tool_names(), "limits": c.get("limits")}, indent=2))
        return 0

    if args.freeze_set is not None:
        from furniture_cad.tools.freeze_set import FREEZE_PIECES, freeze_tool_calls

        ids = list(args.freeze_set) if args.freeze_set else list(FREEZE_PIECES.keys())
        summary: dict[str, Any] = {"mode": "freeze_set", "pieces": {}}
        ok_all = True
        for pid in ids:
            if pid not in FREEZE_PIECES:
                summary["pieces"][pid] = {"ok": False, "error": "unknown freeze piece"}
                ok_all = False
                continue
            meta = FREEZE_PIECES[pid]
            piece_dir = Path(args.work) / pid
            pctx = ToolContext(work_dir=piece_dir)
            results = run_tool_script(pctx, freeze_tool_calls(pid))
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
