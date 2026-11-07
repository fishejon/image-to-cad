"""Phase 4: edit named dimensions → rebuild saved script with no model call."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from furniture_cad.tools.handlers import ToolContext, dispatch


def apply_params(script: str, params: dict[str, float | int]) -> str:
    """Replace simple `name=number` assignments / dict entries for known params."""
    out = script
    for key, val in params.items():
        # name=123 or "name": 123 or name=123.0
        patterns = [
            rf"(\b{re.escape(key)}\s*=\s*)-?\d+(?:\.\d+)?",
            rf'("{re.escape(key)}"\s*:\s*)-?\d+(?:\.\d+)?',
            rf"('{re.escape(key)}'\s*:\s*)-?\d+(?:\.\d+)?",
        ]
        for pat in patterns:
            out, n = re.subn(pat, rf"\g<1>{val}", out)
            if n:
                break
    return out


def rebuild_from_project(project_dir: Path | str, params: dict[str, float | int]) -> dict[str, Any]:
    project_dir = Path(project_dir)
    script_path = project_dir / "build_script.py"
    meta_path = project_dir / "build_meta.json"
    if not script_path.is_file():
        # recover from last build name + sidecar written by save_project
        raise FileNotFoundError(f"missing {script_path}")
    script = script_path.read_text(encoding="utf-8")
    new_script = apply_params(script, params)
    t0 = time.perf_counter()
    ctx = ToolContext(work_dir=project_dir / "rebuild")
    result = dispatch(ctx, "build", {"name": "rebuild", "script": new_script})
    if result.get("ok"):
        dispatch(ctx, "lists", {})
    ms = (time.perf_counter() - t0) * 1000
    meta = {
        "params": params,
        "rebuild_ms": round(ms, 1),
        "ok": bool(result.get("ok")),
        "gate_under_5s": ms < 5000,
    }
    if meta_path.is_file():
        prev = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["source"] = prev
    (project_dir / "rebuild_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    script_path.write_text(new_script, encoding="utf-8")
    return {"ok": result.get("ok"), "rebuild_ms": meta["rebuild_ms"], "gate_under_5s": meta["gate_under_5s"], "result": result}


def save_project_script(project_dir: Path | str, script: str, *, name: str = "assembly") -> Path:
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / "build_script.py"
    path.write_text(script, encoding="utf-8")
    (project_dir / "build_meta.json").write_text(
        json.dumps({"name": name, "saved": True}, indent=2) + "\n", encoding="utf-8"
    )
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rebuild saved build script with new params (no model)")
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--set", nargs=2, metavar=("KEY", "VAL"), action="append", default=[])
    args = p.parse_args(argv)
    params = {k: float(v) for k, v in args.set}
    out = rebuild_from_project(args.project, params)
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
