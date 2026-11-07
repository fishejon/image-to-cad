"""Photo upload, artifacts, and async run hooks for the job HTTP API."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from furniture_cad.jobs.server import _job_public, _save_photo, run_job
from furniture_cad.jobs.store import JobStore


def test_save_photo_b64(tmp_path: Path) -> None:
    raw = b"\xff\xd8\xfffakejpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    path = _save_photo(tmp_path / "w", {"photo_b64": b64})
    assert path
    assert Path(path).read_bytes() == raw


def test_save_photo_data_url(tmp_path: Path) -> None:
    raw = b"hello-photo"
    data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    path = _save_photo(tmp_path / "w2", {"photo_data_url": data_url})
    assert Path(path).read_bytes() == raw


def test_job_public_lists_artifacts(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (work / "lists.json").write_text('{"ok":true}\n', encoding="utf-8")
    (work / "demo.step").write_bytes(b"ISO-10303")
    store = JobStore(tmp_path)
    job = store.create(prompt="case_01", work_dir=work)
    out = run_job(store, job.id, mode="freeze")
    assert out["ok"] is True
    pub = _job_public(store.get(job.id))
    names = {a["name"] for a in pub["artifacts"]}
    assert "lists.json" in names
    assert any(n.endswith(".stl") for n in names)
    assert any(n.endswith(".step") for n in names)
