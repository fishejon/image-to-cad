"""Phase 0/1: tool contract + offline runner (build/lists/measure)."""

from __future__ import annotations

import json
from pathlib import Path

from furniture_cad.tools.contract import anthropic_tools, load_contract, tool_names
from furniture_cad.tools.handlers import ToolContext, dispatch
from furniture_cad.tools.loop import resolve_limits, run_tool_script

ROOT = Path(__file__).resolve().parents[1]
OFFLINE = ROOT / "examples" / "tools" / "bookshelf_offline.json"


def test_contract_frozen_tools_and_limits() -> None:
    c = load_contract()
    assert c["schema"] == "furniture_cad.tools.v1"
    names = tool_names()
    assert names == ["build", "render", "measure", "check", "compare", "lists", "ask_user"]
    lim = c["limits"]
    assert lim["max_spend_usd_per_job"] == 2.0
    assert lim["max_spend_usd_per_day"] == 25.0
    assert lim["max_rounds"] == 8
    tools = anthropic_tools()
    assert all("input_schema" in t and "name" in t for t in tools)
    assert len(tools) == 7


def test_resolve_limits_env(monkeypatch) -> None:
    monkeypatch.setenv("FURNITURE_CAD_MAX_ROUNDS", "3")
    monkeypatch.setenv("FURNITURE_CAD_MAX_SPEND_USD_PER_JOB", "1.5")
    lim = resolve_limits()
    assert lim["max_rounds"] == 3
    assert lim["max_spend_usd_per_job"] == 1.5


def test_build_bad_script_returns_tool_error(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    result = dispatch(ctx, "build", {"script": "raise ValueError('boom')"})
    assert result["ok"] is False
    assert "ValueError" in result["error"]


def test_offline_bookshelf_build_lists_measure(tmp_path: Path) -> None:
    calls = json.loads(OFFLINE.read_text(encoding="utf-8"))
    ctx = ToolContext(work_dir=tmp_path)
    results = run_tool_script(ctx, calls)
    assert len(results) == 3
    assert all(r["result"]["ok"] for r in results)
    assert len(ctx.parts) == 10
    assert sum(p.qty for p in ctx.parts) == 20
    totals = results[1]["result"]["totals"]
    assert totals["piece_count"] == 20
    assert totals["part_types"] == 10
    m = results[2]["result"]
    assert m["id"] == "side_L"
    assert m["finished_mm"] == [18.0, 300.0, 1800.0]


def test_ask_user_flags_pause(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    result = dispatch(ctx, "ask_user", {"question": "Oak or walnut?", "choices": ["oak", "walnut"]})
    assert result["ok"] is True
    assert result["needs_user"] is True


def test_build_exports_seat_panel_solid(tmp_path: Path) -> None:
    calls = json.loads((ROOT / "examples" / "tools" / "seat_panel_solid.json").read_text(encoding="utf-8"))
    ctx = ToolContext(work_dir=tmp_path)
    results = run_tool_script(ctx, calls)
    assert results[0]["result"]["ok"] is True
    build = results[0]["result"]["build"]
    assert build["has_assembly"] is True
    assert build.get("exported") is True
    assert (tmp_path / "seat_panel_smoke.stl").is_file()
    assert (tmp_path / "seat_panel_smoke.step").is_file()
    assert results[1]["result"]["ok"] is True
    assert results[2]["result"]["finished_mm"] == [28.0, 460.0, 430.0]
