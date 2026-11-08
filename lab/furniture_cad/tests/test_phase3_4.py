"""Phase 3 ask_user pause + Phase 4 no-model rebuild."""

from __future__ import annotations

from pathlib import Path

from furniture_cad.jobs.resume import simulate_ask_pause
from furniture_cad.jobs.store import JobStore
from furniture_cad.rebuild import apply_params, rebuild_from_project, save_project_script
from furniture_cad.tools.oracle_set import SCRIPT_CASE_01, oracle_tool_calls as freeze_tool_calls
from furniture_cad.tools.handlers import ToolContext
from furniture_cad.tools.loop import run_tool_script


def test_ask_user_sets_needs_user(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path)
    r = simulate_ask_pause(ctx, "Overall height in mm?", ["1600", "1800"])
    assert r["ok"] is True
    assert r["needs_user"] is True
    assert "height" in r["question"].lower()


def test_job_needs_user_status(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    job = store.create(prompt="ask scale", work_dir=tmp_path / "j")
    job.status = "needs_user"
    job.log = [{"tool": "ask_user", "needs_user": True, "input": {"question": "Oak or walnut?"}}]
    store.save(job)
    got = store.get(job.id)
    assert got and got.status == "needs_user"


def test_rebuild_params_under_5s(tmp_path: Path) -> None:
    ctx = ToolContext(work_dir=tmp_path / "proj")
    results = run_tool_script(ctx, freeze_tool_calls("case_01"))
    assert results[0]["result"]["ok"]
    assert (tmp_path / "proj" / "build_script.py").is_file()
    out = rebuild_from_project(tmp_path / "proj", {"W": 750, "H": 1500})
    assert out["ok"] is True
    assert out["gate_under_5s"] is True
    assert out["rebuild_ms"] < 5000


def test_apply_params_replaces_assignments() -> None:
    s = "W = 900.0\nH = 1800.0\nseat_w=457\n"
    out = apply_params(s, {"W": 800, "seat_w": 400})
    assert "W = 800" in out
    assert "seat_w=400" in out
