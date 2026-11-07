"""Phase 3: pause on ask_user and resume with an answer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from furniture_cad.jobs.store import Job, JobStore
from furniture_cad.tools.handlers import ToolContext, dispatch
from furniture_cad.tools.loop import DEFAULT_MODEL, resolve_limits, run_messages_loop


def pending_question(job: Job) -> dict[str, Any] | None:
    if job.status != "needs_user":
        return None
    for entry in reversed(job.log or []):
        if entry.get("tool") == "ask_user" and entry.get("needs_user"):
            return entry
    # fall back to result payload
    res = job.result or {}
    if res.get("stop_reason") == "needs_user":
        return {"question": res.get("question") or "Answer required"}
    return {"question": "Answer required to resume"}


def resume_job(store: JobStore, job_id: str, answer: str) -> dict[str, Any]:
    job = store.get(job_id)
    if not job:
        return {"ok": False, "error": "not found"}
    if job.status != "needs_user":
        return {"ok": False, "error": f"job status is {job.status}, expected needs_user"}

    work = Path(job.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    answers_path = work / "user_answers.jsonl"
    with answers_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"answer": answer, "question": pending_question(job)}) + "\n")

    ctx = ToolContext(work_dir=work)
    if job.photo:
        ctx.reference_photo = Path(job.photo)
    # Restore parts if present
    parts_files = sorted(work.glob("*.parts.json"))
    if parts_files:
        from furniture_cad.parts import load_parts

        ctx.parts = load_parts(parts_files[-1])

    follow = (
        f"The user answered: {answer!r}. Continue the furniture job. "
        f"Original prompt: {job.prompt}"
    )
    lim = resolve_limits()
    summary = run_messages_loop(ctx, prompt=follow, limits=lim, model=job.model or DEFAULT_MODEL)
    job.log = list(job.log or []) + list(ctx.log)
    job.rounds = int(job.rounds or 0) + int(summary.get("rounds") or 0)
    job.spend_usd_approx = float(job.spend_usd_approx or 0) + float(summary.get("spent_usd_approx") or 0)
    job.result = summary
    if summary.get("stop_reason") == "needs_user":
        job.status = "needs_user"
    elif summary.get("ok"):
        job.status = "succeeded"
    else:
        job.status = "failed"
        job.error = str(summary.get("stop_reason") or "failed")
    store.save(job)
    return {"ok": True, "job": job.to_dict()}


def simulate_ask_pause(ctx: ToolContext, question: str, choices: list[str] | None = None) -> dict[str, Any]:
    """Offline helper for tests — dispatch ask_user and return needs_user payload."""
    return dispatch(ctx, "ask_user", {"question": question, "choices": choices or []})
