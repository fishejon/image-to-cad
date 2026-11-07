"""Minimal job HTTP API for local worker / Vercel relay.

POST /jobs                 {prompt, photo?, photo_b64?, model?, mode?, domain?, run?, async?}
GET  /jobs
GET  /jobs/:id
GET  /jobs/:id/artifacts
GET  /jobs/:id/artifacts/:name
POST /jobs/:id/run         {mode?, async?}  — default async for browser polling
POST /jobs/:id/resume      {answer}

Vercel should only create jobs + poll; this process (or Docker worker) runs them.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from furniture_cad.jobs.resume import pending_question, resume_job
from furniture_cad.jobs.store import JobStore
from furniture_cad.tools.freeze_set import FREEZE_PIECES, freeze_tool_calls
from furniture_cad.tools.handlers import ToolContext
from furniture_cad.tools.loop import resolve_limits, run_messages_loop, run_tool_script

DEFAULT_ROOT = Path("out/jobs")
_ARTIFACT_SAFE = re.compile(r"^[A-Za-z0-9._\-]+$")
_RUN_LOCKS: dict[str, threading.Lock] = {}
_RUN_LOCKS_GUARD = threading.Lock()


def _expected_token() -> str:
    return (os.environ.get("WORKER_JOBS_TOKEN") or os.environ.get("JOBS_TOKEN") or "").strip()


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    """If WORKER_JOBS_TOKEN is set, require Authorization: Bearer <token> (or x-jobs-token)."""
    expected = _expected_token()
    if not expected:
        return True
    auth = (handler.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer ") and auth[7:].strip() == expected:
        return True
    if (handler.headers.get("x-jobs-token") or "").strip() == expected:
        return True
    return False


def _json(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    data = json.dumps(body).encode("utf-8")
    handler.send_response(status)
    handler.send_header("content-type", "application/json")
    handler.send_header("content-length", str(len(data)))
    handler.send_header("access-control-allow-origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _bytes(handler: BaseHTTPRequestHandler, status: int, data: bytes, content_type: str, *, filename: str | None = None) -> None:
    handler.send_response(status)
    handler.send_header("content-type", content_type)
    handler.send_header("content-length", str(len(data)))
    handler.send_header("access-control-allow-origin", "*")
    if filename:
        handler.send_header("content-disposition", f'attachment; filename="{filename}"')
    handler.end_headers()
    handler.wfile.write(data)


def _job_public(job) -> dict[str, Any]:
    d = job.to_dict()
    pq = pending_question(job)
    if pq:
        inp = pq.get("input") if isinstance(pq.get("input"), dict) else {}
        d["pending_question"] = {
            "question": inp.get("question") or pq.get("question") or "Answer required",
            "choices": list(inp.get("choices") or []),
        }
    work = Path(job.work_dir)
    arts = []
    if work.is_dir():
        for p in sorted(work.rglob("*")):
            if p.is_file() and p.suffix.lower() in {".stl", ".step", ".stp", ".json", ".py", ".jpg", ".jpeg", ".png"}:
                rel = str(p.relative_to(work)).replace("\\", "/")
                if "/" not in rel:  # top-level only for listing
                    arts.append({"name": rel, "bytes": p.stat().st_size})
    d["artifacts"] = arts
    return d


def _decode_photo_b64(raw: str) -> bytes:
    s = (raw or "").strip()
    if "," in s and s.lower().startswith("data:"):
        s = s.split(",", 1)[1]
    return base64.b64decode(s)


def _save_photo(work: Path, body: dict[str, Any]) -> str | None:
    work.mkdir(parents=True, exist_ok=True)
    b64 = body.get("photo_b64") or body.get("photo_data_url")
    if b64:
        data = _decode_photo_b64(str(b64))
        # Cap ~8 MB decoded
        if len(data) > 8_000_000:
            raise ValueError("photo too large (max ~8MB)")
        path = work / "reference.jpg"
        path.write_bytes(data)
        return str(path)
    photo = body.get("photo")
    return str(photo) if photo else None


def _lock_for(job_id: str) -> threading.Lock:
    with _RUN_LOCKS_GUARD:
        if job_id not in _RUN_LOCKS:
            _RUN_LOCKS[job_id] = threading.Lock()
        return _RUN_LOCKS[job_id]


def run_job(store: JobStore, job_id: str, *, mode: str | None = None) -> dict[str, Any]:
    lock = _lock_for(job_id)
    if not lock.acquire(blocking=False):
        job = store.get(job_id)
        return {"ok": True, "async": True, "job": _job_public(job) if job else None, "note": "already running"}
    try:
        job = store.get(job_id)
        if not job:
            return {"ok": False, "error": "not found"}
        if job.status in ("succeeded", "failed"):
            return {"ok": True, "job": _job_public(job)}
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
                    "ok": all(r["result"].get("ok") for r in results)
                    and bool(ctx.last_build and ctx.last_build.get("exported")),
                }
            else:
                lim = resolve_limits()
                from furniture_cad.tools.loop import DEFAULT_MODEL

                # Prefer cheaper model for repair-ish prompts when configured
                model = job.model
                if not model:
                    repair = __import__("os").environ.get("FURNITURE_CAD_REPAIR_MODEL")
                    model = repair or DEFAULT_MODEL
                summary = run_messages_loop(ctx, prompt=job.prompt, limits=lim, model=model)

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
            return {"ok": True, "job": _job_public(job)}
        except Exception as e:
            job.status = "failed"
            job.error = f"{type(e).__name__}: {e}"
            store.save(job)
            return {"ok": False, "error": job.error, "job": _job_public(job)}
    finally:
        lock.release()


def start_job_async(store: JobStore, job_id: str, *, mode: str | None = None) -> dict[str, Any]:
    job = store.get(job_id)
    if not job:
        return {"ok": False, "error": "not found"}
    if job.status == "queued":
        job.status = "running"
        store.save(job)

    def _target() -> None:
        run_job(store, job_id, mode=mode)

    threading.Thread(target=_target, daemon=True, name=f"job-{job_id}").start()
    # Give the worker a tick to flip status
    time.sleep(0.05)
    job2 = store.get(job_id)
    return {"ok": True, "async": True, "job": _job_public(job2) if job2 else None}


def make_handler(store: JobStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            sys.stderr.write("jobs: " + (fmt % args) + "\n")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("access-control-allow-origin", "*")
            self.send_header("access-control-allow-methods", "GET,POST,OPTIONS")
            self.send_header("access-control-allow-headers", "content-type, authorization, x-jobs-token")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path == "/health":
                return _json(self, 200, {"ok": True, "service": "furniture_cad.jobs", "auth": bool(_expected_token())})
            if not _authorized(self):
                return _json(self, 401, {"error": "unauthorized"})
            if path == "/jobs":
                return _json(self, 200, {"jobs": [_job_public(j) for j in store.list()]})

            # /jobs/:id/artifacts/:name
            m_file = re.match(r"^/jobs/([^/]+)/artifacts/(.+)$", path)
            if m_file:
                job = store.get(m_file.group(1))
                if not job:
                    return _json(self, 404, {"error": "not found"})
                name = unquote(m_file.group(2))
                if "/" in name or ".." in name or not _ARTIFACT_SAFE.match(name):
                    return _json(self, 400, {"error": "invalid artifact name"})
                fpath = Path(job.work_dir) / name
                if not fpath.is_file():
                    return _json(self, 404, {"error": "artifact not found"})
                ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
                return _bytes(self, 200, fpath.read_bytes(), ctype, filename=name)

            # /jobs/:id/artifacts
            m_list = re.match(r"^/jobs/([^/]+)/artifacts$", path)
            if m_list:
                job = store.get(m_list.group(1))
                if not job:
                    return _json(self, 404, {"error": "not found"})
                return _json(self, 200, {"job_id": job.id, "artifacts": _job_public(job).get("artifacts") or []})

            if path.startswith("/jobs/"):
                job = store.get(path.split("/")[2])
                if not job:
                    return _json(self, 404, {"error": "not found"})
                return _json(self, 200, _job_public(job))
            return _json(self, 404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if not _authorized(self):
                return _json(self, 401, {"error": "unauthorized"})
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
                work = Path(
                    body.get("work_dir")
                    or (store.root / "work" / ("w_" + str(int(time.time() * 1000))))
                )
                try:
                    photo = _save_photo(work, body)
                except Exception as e:
                    return _json(self, 400, {"error": f"photo: {e}"})
                domain = body.get("domain")
                if domain:
                    (work / "domain.txt").write_text(str(domain), encoding="utf-8")
                job = store.create(
                    prompt=prompt,
                    work_dir=work,
                    photo=photo,
                    model=body.get("model"),
                )
                want_run = bool(body.get("run"))
                async_run = body.get("async", True)
                if want_run:
                    if async_run:
                        return _json(self, 201, start_job_async(store, job.id, mode=body.get("mode")))
                    return _json(self, 200, run_job(store, job.id, mode=body.get("mode")))
                return _json(self, 201, _job_public(job))

            if path.startswith("/jobs/") and path.endswith("/run"):
                job_id = path.split("/")[2]
                async_run = body.get("async", True)
                if async_run:
                    return _json(self, 200, start_job_async(store, job_id, mode=body.get("mode")))
                return _json(self, 200, run_job(store, job_id, mode=body.get("mode")))

            if path.startswith("/jobs/") and path.endswith("/resume"):
                job_id = path.split("/")[2]
                answer = str(body.get("answer") or "").strip()
                if not answer:
                    return _json(self, 400, {"error": "answer required"})
                # Resume runs sync by default (may take a while); allow async
                if body.get("async"):
                    def _res() -> None:
                        resume_job(store, job_id, answer)

                    job = store.get(job_id)
                    if job and job.status == "needs_user":
                        job.status = "running"
                        store.save(job)
                    threading.Thread(target=_res, daemon=True).start()
                    time.sleep(0.05)
                    job2 = store.get(job_id)
                    return _json(self, 200, {"ok": True, "async": True, "job": _job_public(job2) if job2 else None})
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
