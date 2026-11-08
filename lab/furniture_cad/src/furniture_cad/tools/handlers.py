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
    assembly: Any = None
    last_stl: Path | None = None
    last_renders: dict[str, str] = field(default_factory=dict)
    last_check: dict[str, Any] | None = None
    last_compare: dict[str, Any] | None = None
    log: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.work_dir = Path(self.work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def find_stl(self) -> Path | None:
        if self.last_stl and Path(self.last_stl).is_file():
            return Path(self.last_stl)
        if self.last_build and self.last_build.get("name"):
            cand = self.work_dir / f"{self.last_build['name']}.stl"
            if cand.is_file():
                return cand
        stls = sorted(self.work_dir.glob("*.stl"))
        return stls[-1] if stls else None


def _ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def _err(message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": message, **extra}


def _build_namespace() -> dict[str, Any]:
    """Allowlisted helpers available inside build(script)."""
    from build123d import Box, Compound, Pos

    from furniture_cad.blocks import HELPER_DOCS, open_etagere, carcass, panel, shelf_board
    from furniture_cad.derive import part
    from furniture_cad.templates import TEMPLATE_FNS, four_leg_chair, stool

    return {
        "__builtins__": SAFE_BUILTINS,
        "blocks": dict(BLOCK_FNS),
        "block": get_block,
        "helper_docs": dict(HELPER_DOCS),
        "PartRecord": PartRecord,
        "part": part,
        "panel": panel,
        "shelf_board": shelf_board,
        "open_etagere": open_etagere,
        "carcass": carcass,
        "AllowlistError": AllowlistError,
        # Templates kept as few-shot/examples (oracle chairs); prefer helpers for new work
        "templates": dict(TEMPLATE_FNS),
        "four_leg_chair": four_leg_chair,
        "stool": stool,
        "Box": Box,
        "Pos": Pos,
        "Compound": Compound,
    }


def _safe_build_name(raw: str) -> str:
    """Filesystem-safe artifact basename (no spaces) for STL/parts downloads."""
    import re

    s = re.sub(r"[^A-Za-z0-9._\-]+", "_", (raw or "assembly").strip())
    s = re.sub(r"_+", "_", s).strip("._") or "assembly"
    return s[:80]


def tool_build(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    script = args.get("script")
    if not isinstance(script, str) or not script.strip():
        return _err("script must be a non-empty string")
    name = _safe_build_name(str(args.get("name") or "assembly"))
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
    # Persist script for Phase 4 param rebuild (no model)
    try:
        from furniture_cad.rebuild import save_project_script

        save_project_script(ctx.work_dir, script, name=name)
    except Exception:
        pass
    assembly = ns.get("assembly")
    ctx.assembly = assembly
    ctx.last_stl = None
    ctx.last_build = {
        "name": name,
        "parts_path": str(parts_path),
        "part_count": len(parts),
        "piece_count": sum(p.qty for p in parts),
        "has_assembly": assembly is not None,
        "script_bytes": len(script.encode("utf-8")),
    }
    if assembly is not None:
        try:
            from furniture_cad.export import export_solid
            from furniture_cad.geom_check import bbox_mm_from_solid

            written = export_solid(assembly, ctx.work_dir / name, formats=("stl", "step"))
            ctx.last_build["exported"] = True
            if "stl" in written:
                ctx.last_stl = written["stl"]
                ctx.last_build["stl"] = str(written["stl"])
            try:
                ctx.last_build["bbox_mm"] = {
                    k: round(v, 2) if isinstance(v, float) else v
                    for k, v in bbox_mm_from_solid(assembly).items()
                    if k in ("w", "d", "h")
                }
            except Exception:
                pass
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
    try:
        from furniture_cad.derive import consistency_report

        plan["consistency"] = consistency_report(parts, ctx.assembly)
    except Exception as e:
        plan["consistency"] = {"warnings": [f"consistency skipped: {type(e).__name__}: {e}"]}
    ctx.last_plan = plan
    out = ctx.work_dir / "lists.json"
    out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return _ok(
        {
            "plan_path": str(out),
            "totals": plan["totals"],
            "summary": plan["summary"],
            "cut_list": plan["cut_list"],
            "consistency": plan.get("consistency"),
        }
    )


def tool_measure(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    pid = str(args.get("part") or "")
    if not pid:
        return _err("part id required")
    if pid in ("assembly", "overall", "*"):
        from furniture_cad.geom_check import bbox_mm_from_solid, bbox_mm_from_stl

        if ctx.assembly is not None:
            bb = bbox_mm_from_solid(ctx.assembly)
            return _ok({"id": "assembly", "source": "solid", "bbox_mm": {k: round(bb[k], 2) for k in ("w", "d", "h")}})
        stl = ctx.find_stl()
        if stl:
            bb = bbox_mm_from_stl(stl)
            return _ok({"id": "assembly", "source": "stl", "bbox_mm": {k: round(bb[k], 2) for k in ("w", "d", "h")}, "stl": str(stl)})
        return _err("no assembly solid or STL; call build with assembly= first")
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
                    "source": "part_record",
                }
            )
    return _err(f"unknown part {pid!r}", known=[p.id for p in ctx.parts] + ["assembly"])


def tool_render(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    views = args.get("views") or []
    if not isinstance(views, list) or not views:
        return _err("views must be a non-empty array")
    stl = ctx.find_stl()
    if not stl:
        return _err("no STL to render; call build with assembly= first")
    from furniture_cad.render_views import render_stl_views

    out = ctx.work_dir / "renders"
    try:
        meta = render_stl_views(stl, out, [str(v) for v in views])
    except Exception as e:
        return _err(f"render failed: {type(e).__name__}: {e}")
    ctx.last_renders = dict(meta.get("views") or {})
    (out / "views.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    # Cap images returned to the model (loop attaches PNG bytes)
    image_paths = [ctx.last_renders[v] for v in ("front", "side", "iso", "top", "back") if v in ctx.last_renders][:3]
    return _ok(
        {
            "render_dir": str(out),
            "views": ctx.last_renders,
            "raster": True,
            "stl": str(stl),
            "image_paths": image_paths,
        }
    )


def tool_check(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    from furniture_cad.geom_check import bbox_mm_from_solid, bbox_mm_from_stl, compare_targets

    targets = dict(args.get("targets_mm") or ctx.targets_mm or {})
    stl = ctx.find_stl()
    bbox: dict[str, float] | None = None
    source = None
    if ctx.assembly is not None:
        try:
            bbox = bbox_mm_from_solid(ctx.assembly)
            source = "solid"
        except Exception:
            bbox = None
    if bbox is None and stl:
        bbox = bbox_mm_from_stl(stl)
        source = "stl"
    if bbox is None:
        return _err("no solid/STL for bbox; call build with assembly= first")

    cmp = compare_targets(bbox, targets)
    iou = None
    iou_rating = None
    iou_min = args.get("iou_min")
    pass_iou = None
    if ctx.reference_photo and Path(ctx.reference_photo).is_file() and stl:
        try:
            from furniture_cad.silhouette import rating_for_iou, silhouette_iou

            m = silhouette_iou(ctx.reference_photo, stl)
            iou = m["iou"]
            iou_rating = rating_for_iou(float(iou))
            if iou_min is not None:
                pass_iou = float(iou) >= float(iou_min)
        except Exception as e:
            iou = None
            iou_rating = f"error:{type(e).__name__}"

    overlaps_note = "per-part mesh overlap not computed (single assembly mesh); use unit tests for AABB overlap helpers"
    passed = True
    if cmp["within_5pct"] is False:
        passed = False
    if pass_iou is False:
        passed = False

    result = {
        "bbox_mm": {k: round(float(bbox[k]), 2) for k in ("w", "d", "h")},
        "bbox_source": source,
        "targets_mm": targets,
        "within_5pct": cmp["within_5pct"],
        "issues": cmp["issues"],
        "detail": cmp.get("detail"),
        "iou": iou,
        "iou_rating": iou_rating,
        "iou_min": iou_min,
        "iou_pass": pass_iou,
        "pass": passed,
        "overlaps": overlaps_note,
        "piece_count": sum(p.qty for p in ctx.parts) if ctx.parts else None,
        "part_types": len(ctx.parts) if ctx.parts else None,
        "stl": str(stl) if stl else None,
    }
    ctx.last_check = result
    return _ok(result)


def tool_compare(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    expected = args.get("expected_qty") or {}
    notes: list[str] = []
    matches: dict[str, Any] = {}
    if expected and ctx.parts:
        by_id = {p.id: p.qty for p in ctx.parts}
        for k, v in expected.items():
            got = by_id.get(str(k))
            matches[str(k)] = {"expected": v, "got": got, "ok": got == v}
            if got != v:
                notes.append(f"{k}: expected {v} got {got}")

    stl = ctx.find_stl()
    photo = ctx.reference_photo
    iou = None
    rating = None
    overlay = None
    differences: list[str] = []
    if photo and Path(photo).is_file() and stl:
        try:
            from furniture_cad.render_views import overlay_masks_png
            from furniture_cad.silhouette import _aligned_iou, _photo_mask, _stl_front_mask, rating_for_iou, silhouette_iou

            m = silhouette_iou(photo, stl)
            iou = m["iou"]
            rating = rating_for_iou(float(iou))
            ref = _photo_mask(Path(photo), tuple(m["size"]))
            model = _stl_front_mask(Path(stl), tuple(m["size"]))
            # Re-align model like silhouette_iou for a fair overlay
            _, align = _aligned_iou(ref, model)
            from furniture_cad.silhouette import _resize_mask, _shift

            model_a = _shift(_resize_mask(model, float(align["scale"]), tuple(m["size"])), int(align["dx"]), int(align["dy"]))
            overlay_path = ctx.work_dir / "renders" / "compare_overlay.png"
            overlay_masks_png(ref, model_a, overlay_path)
            overlay = str(overlay_path)
            if float(iou) < 0.4:
                differences.append("silhouette mismatch is large (Wrong) — check proportions, foot shape, shelf count")
            elif float(iou) < 0.55:
                differences.append("silhouette is Close but not Close+ — refine outline vs photo")
            else:
                differences.append("silhouette within Close+/Match band on this view")
            differences.append(f"align scale={align.get('scale')} dx={align.get('dx')} dy={align.get('dy')}")
        except Exception as e:
            notes.append(f"IoU/overlay failed: {type(e).__name__}: {e}")
    else:
        notes.append("need reference photo + STL for silhouette compare")

    image_paths = [overlay] if overlay else []
    result = {
        "has_photo": bool(photo),
        "photo": str(photo) if photo else None,
        "views": args.get("views"),
        "qty_matches": matches,
        "qty_ok": all(m["ok"] for m in matches.values()) if matches else None,
        "iou": iou,
        "iou_rating": rating,
        "overlay": overlay,
        "image_paths": image_paths,
        "differences": differences,
        "notes": notes,
        "stl": str(stl) if stl else None,
    }
    ctx.last_compare = result
    return _ok(result)


def tool_ask_user(ctx: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    q = str(args.get("question") or "").strip()
    if not q:
        return _err("question required")
    return {
        "ok": True,
        "needs_user": True,
        "question": q,
        "choices": args.get("choices") or [],
        "hint": "Job pauses (status=needs_user). Resume via POST /jobs/:id/resume {answer}",
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
