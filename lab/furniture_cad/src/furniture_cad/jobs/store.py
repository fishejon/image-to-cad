"""Job store — file-backed JSON (Postgres-ready shape for Phase 2)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Job:
    id: str
    status: str  # queued|running|needs_user|succeeded|failed
    prompt: str
    created_at: float
    updated_at: float
    work_dir: str
    photo: str | None = None
    model: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    log: list[dict[str, Any]] = field(default_factory=list)
    spend_usd_approx: float = 0.0
    rounds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Job:
        return cls(
            id=str(d["id"]),
            status=str(d["status"]),
            prompt=str(d.get("prompt") or ""),
            created_at=float(d["created_at"]),
            updated_at=float(d["updated_at"]),
            work_dir=str(d["work_dir"]),
            photo=d.get("photo"),
            model=d.get("model"),
            result=d.get("result"),
            error=d.get("error"),
            log=list(d.get("log") or []),
            spend_usd_approx=float(d.get("spend_usd_approx") or 0),
            rounds=int(d.get("rounds") or 0),
        )


class JobStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "jobs").mkdir(exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.root / "jobs" / f"{job_id}.json"

    def create(self, *, prompt: str, work_dir: Path | str, photo: str | None = None, model: str | None = None) -> Job:
        now = time.time()
        job = Job(
            id="job_" + uuid.uuid4().hex[:12],
            status="queued",
            prompt=prompt,
            created_at=now,
            updated_at=now,
            work_dir=str(work_dir),
            photo=photo,
            model=model,
        )
        self.save(job)
        return job

    def save(self, job: Job) -> None:
        job.updated_at = time.time()
        path = self._path(job.id)
        path.write_text(json.dumps(job.to_dict(), indent=2) + "\n", encoding="utf-8")

    def get(self, job_id: str) -> Job | None:
        path = self._path(job_id)
        if not path.is_file():
            return None
        return Job.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, *, limit: int = 50) -> list[Job]:
        rows = []
        for p in sorted((self.root / "jobs").glob("job_*.json"), reverse=True):
            try:
                rows.append(Job.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(rows) >= limit:
                break
        return rows
