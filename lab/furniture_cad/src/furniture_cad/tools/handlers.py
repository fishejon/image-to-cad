"""Tool handlers for the Phase 1 CLI runner."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from furniture_cad.allowlist import BLOCK_FNS, AllowlistError, get_block
from furniture_cad.lists import material_plan
from furniture_cad.parts import PartRecord, dump_parts, load_parts


SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "len": len,
    "range": range,
    "enumerate": enumerate,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "True": True,
    "False": False,
    "None": None,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
}


@dataclass
class ToolContext:
    """Mutable job workspace for one runner session."""

    work_dir: Path
    parts: list[PartRecord] = field(default_factory=list)
    last_build: dict[str, Any] | None = None
    last_plan: dict[str, Any] | None = None
    reference_photo: Path | None = None
    targets_mm: dict[str, float] = field(default_factory=dict)
    log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.work_dir = Path(self.work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def _err(message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, **extra}


def _build_namespace() -> dict[str, Any]:
    """Allowlisted helpers available inside build(script)."""
    from build123d import Box, Compound, Pos

    from furniture_cad.templates import TEMPLATE_FNS, four_leg_chair, stool

    return {
        "__builtins__": SAFE_BUILTINS,
        "blocks": dict(BLOCK_FNS),
        "block": get_block,
        "PartRecord": PartRecord,
        "AllowlistError": AllowlistError,
        "templates": dict(TEMPLATE_FNS),
        "four_leg_chair": four_leg_chair,
        "stool": stool,
        # Small build123d surface for placing / combining block solids
        "Box": Box,
        "Pos": Pos,
        "Compound": Compound,
    }


def tool_build(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    script = args.get("script")
    if not isinstance(script, str) or not script.strip():
        return _err("script must be a non-empty string")
    name = str(args.get("name") or "assembly")
    ns = _build_namespace()
    try:
        exec(script, ns, ns)  # noqa: S102 — sandboxed builtins + allowlisted helpers only
    except Exception as e:
        return _err(
            f"{type(e).__name__}: {e}",
            traceback="".join(traceback.format_exception_only(type(e), e)).strip(),
        )

    records_raw = ns.get("parts") or ns.get("part_records")
    if records_raw is None:
        return _err("script must set `parts` to a list of PartRecord or dicts")

    try:
        parts = [r if isinstance(r, PartRecord) else PartRecord.from_dict(r) for r in records_raw]
    except Exception as e:
        return _err(f"invalid parts: {e}")

    ctx.parts = parts
    parts_path = dump_parts(parts, ctx.work_dir / f"{name}.parts.json", meta={"name": name, "source": "build"})
    assembly = ns.get("assembly")
    ctx.last_build = {
        "name": name,
        "parts_path": str(parts_path),
        "part_count": len(parts),
        "piece_count": sum(p.qty for p in parts),
        "has_assembly": assembly is not None,
        "script_bytes": len(script.encode("utf-8")),
    }
    # Optional: export solids if assembly present
    if assembly is not None:
        try:
            from furniture_cad.export import export_solid

            export_solid(assembly, ctx.work_dir / name, formats=("stl", "step"))
            ctx.last_build["exported"] = True
        except Exception as e:
            ctx.last_build["exported"] = False
            ctx.last_build["export_error"] = f"{type(e).__name__}: {e}"

    return _ok({"build": ctx.last_build, "parts": [p.to_dict() for p in parts]})


def tool_lists(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    raw = args.get("parts")
    try:
        if raw is not None:
            parts = [r if isinstance(r, PartRecord) else PartRecord.from_dict(r) for r in raw]
        elif ctx.parts:
            parts = ctx.parts
        else:
            # fall back to any *.parts.json in work dir
            candidates = sorted(ctx.work_dir.glob("*.parts.json"))
            if not candidates:
                return _err("no parts model; call build first or pass parts[]")
            parts = load_parts(candidates[-1])
            ctx.parts = parts
    except Exception as e:
        return _err(f"invalid parts: {e}")

    plan = material_plan(parts)
    ctx.last_plan = plan
    out = ctx.work_dir / "lists.json"
    out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return _ok({"plan_path": str(out), "totals": plan["totals"], "summary": plan["summary"], "cut_list": plan["cut_list"]})


def tool_measure(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    pid = str(args.get("part") or "")
    if not pid:
        return _err("part id required")
    for p in ctx.parts:
        if p.id == pid:
            ft, fw, fl = p.finished_twl()
            bt, bw, bl = p.blank_twl()
            return _ok(
                {
                    "id": p.id,
                    "name": p.name,
                    "qty": p.qty,
                    "finished_mm": [ft, fw, fl],
                    "blank_mm": [bt, bw, bl],
                    "material": p.material,
                    "how_made": p.how_made,
                    "curved": p.curved,
                }
            )
    return _err(f"unknown part {pid!r}", known=[p.id for p in ctx.parts])


def tool_render(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    views = args.get("views") or []
    if not isinstance(views, list) or not views:
        return _err("views must be a non-empty array")
    return _err("render not implemented yet — Phase 1 stub", views=views, hint="reuse STL IoU headless in Phase 2")


def tool_check(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    targets = args.get("targets_mm") or ctx.targets_mm or {}
    return _err(
        "check not implemented yet — Phase 1 stub",
        targets_mm=targets,
        hint="bbox + overlaps + IoU after render",
    )


def tool_compare(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    return _err(
        "compare not implemented yet — Phase 1 stub",
        has_photo=bool(ctx.reference_photo),
        views=args.get("views"),
    )


def tool_ask_user(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    q = str(args.get("question") or "").strip()
    if not q:
        return _err("question required")
    return {
        "ok": True,
        "needs_user": True,
        "question": q,
        "choices": args.get("choices") or [],
        "hint": "Phase 3 wires pause/resume; CLI prints needs_user and stops the loop",
    }


HANDLERS = {
    "build": tool_build,
    "lists": tool_lists,
    "measure": tool_measure,
    "render": tool_render,
    "check": tool_check,
    "compare": tool_compare,
    "ask_user": tool_ask_user,
}


def dispatch(ctx: ToolContext, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    fn = HANDLERS.get(name)
    if not fn:
        result = _err(f"unknown tool {name!r}")
    else:
        try:
            result = fn(ctx, args)
        except Exception as e:
            result = _err(f"handler crash: {type(e).__name__}: {e}")
    ctx.log.append({"tool": name, "input": args, "result_ok": bool(result.get("ok")), "needs_user": bool(result.get("needs_user"))})
    return result
