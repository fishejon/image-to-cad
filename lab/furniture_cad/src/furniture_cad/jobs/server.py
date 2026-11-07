"""Minimal job HTTP API for local worker / Vercel relay.

POST /jobs          {prompt, photo?, model?, mode?}
GET  /jobs/:id
GET  /jobs
POST /jobs/:id/run  — process queued job (offline freeze piece or live prompt)

Vercel should only create jobs + poll; this process (or Docker worker) runs them.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from furniture_cad.jobs.resume import resume_job
from furniture_cad.jobs.store import JobStore
from furniture_cad.tools.freeze_set import FREEZE_PIECES, freeze_tool_calls
from furniture_cad.tools.handlers import ToolContext
from furniture_cad.tools.loop import resolve_limits, run_messages_loop, run_tool_script

DEFAULT_ROOT = Path("out/jobs")


def _json(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    data = json.dumps(body).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(data)))
    handler.send_header("access-control-allow-origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def run_job(store: JobStore, job_id: str, *, mode: str | None = None) -> dict[str, Any]:
    job = store.get(job_id)
    if not job:
        return {"ok": False, "error": "not found"}
    job.status = "running"
    store.save(job)
    work = Path(job.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    ctx = ToolContext(work_dir=work)
    if job.photo:
        ctx.reference_photo = Path(job.photo)

    try:
        piece = None
        for pid in FREEZE_PIECES:
            if pid in (job.prompt or "") or (mode == "freeze" and job.prompt.strip() == pid):
                piece = pid
                break
        if mode == "freeze" or (job.prompt.strip() in FREEZE_PIECES):
            piece = job.prompt.strip() if job.prompt.strip() in FREEZE_PIECES else piece
        if piece:
            results = run_tool_script(ctx, freeze_tool_calls(piece))
            summary = {
                "mode": "freeze",
                "piece": piece,
                "results": results,
                "parts_count": len(ctx.parts),
                "last_build": ctx.last_build,
                "last_plan_totals": (ctx.last_plan or {}).get("totals"),
                "ok": all(r["result"].get("ok") for r in results) and bool(ctx.last_build and ctx.last_build.get("exported")),
            }
        else:
            lim = resolve_limits()
            from furniture_cad.tools.loop import DEFAULT_MODEL

            summary = run_messages_loop(
                ctx, prompt=job.prompt, limits=lim, model=job.model or DEFAULT_MODEL
            )

        job.log = list(ctx.log)
        job.rounds = int(summary.get("rounds") or len(ctx.log))
        job.spend_usd_approx = float(summary.get("spent_usd_approx") or 0)
        job.result = summary
        if summary.get("stop_reason") == "needs_user" or summary.get("needs_user"):
            job.status = "needs_user"
        elif summary.get("ok"):
            job.status = "succeeded"
        else:
            job.status = "failed"
            job.error = str(summary.get("stop_reason") or summary.get("error") or "failed")
        store.save(job)
        return {"ok": True, "job": job.to_dict()}
    except Exception as e:
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"
        store.save(job)
        return {"ok": False, "error": job.error, "job": job.to_dict()}


def make_handler(store: JobStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("jobs: " + (fmt % args) + "\n")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("access-control-allow-origin", "*")
            self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
            self.send_header("access-control-allow-headers", "content-type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path == "/health":
                return _json(self, 200, {"ok": True, "service": "furniture_cad.jobs"})
            if path == "/jobs":
                return _json(self, 200, {"jobs": [j.to_dict() for j in store.list()]})
            if path.startswith("/jobs/"):
                job = store.get(path.split("/")[2])
                if not job:
                    return _json(self, 404, {"error": "not found"})
                return _json(self, 200, job.to_dict())
            return _json(self, 404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/") or "/"
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return _json(self, 400, {"error": "invalid JSON"})

            if path == "/jobs":
                prompt = str(body.get("prompt") or "").strip()
                if not prompt:
                    return _json(self, 400, {"error": "prompt required"})
                work = Path(body.get("work_dir") or (store.root / "work" / ("w_" + str(int(__import__('time').time())))))
                job = store.create(
                    prompt=prompt,
                    work_dir=work,
                    photo=body.get("photo"),
                    model=body.get("model"),
                )
                if body.get("run"):
                    return _json(self, 200, run_job(store, job.id, mode=body.get("mode")))
                return _json(self, 201, job.to_dict())

            if path.startswith("/jobs/") and path.endswith("/run"):
                job_id = path.split("/")[2]
                return _json(self, 200, run_job(store, job_id, mode=body.get("mode")))

            if path.startswith("/jobs/") and path.endswith("/resume"):
                job_id = path.split("/")[2]
                answer = str(body.get("answer") or "").strip()
                if not answer:
                    return _json(self, 400, {"error": "answer required"})
                return _json(self, 200, resume_job(store, job_id, answer))

            return _json(self, 404, {"error": "not found"})

    return Handler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="furniture_cad job service")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = p.parse_args(argv)
    store = JobStore(args.root)
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(json.dumps({"listening": f"http://{args.host}:{args.port}", "root": str(args.root)}))
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
