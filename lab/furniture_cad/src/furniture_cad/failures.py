"""Append-only failure log for missing blocks / bad fits (drives library growth)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "failure_log.jsonl"


def log_failure(
    *,
    kind: str,
    need: str | None = None,
    photo_id: str | None = None,
    template: str | None = None,
    notes: str = "",
    extra: dict[str, Any] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """
    Append one JSONL record.

    kind: missing_block | bad_fit | compile_error | other
    need: block id or capability that was missing (for missing_block)
    """
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "need": need,
        "photo_id": photo_id,
        "template": template,
        "notes": notes,
    }
    if extra:
        record["extra"] = extra
    log_path = path or DEFAULT_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def log_missing_block(
    photo_id: str,
    need: str,
    notes: str = "",
    *,
    template: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    return log_failure(
        kind="missing_block",
        need=need,
        photo_id=photo_id,
        template=template,
        notes=notes,
        path=path,
    )


def read_failures(path: Path | None = None) -> list[dict[str, Any]]:
    log_path = path or DEFAULT_LOG
    if not log_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Log furniture_cad failures")
    p.add_argument("--kind", default="missing_block", choices=["missing_block", "bad_fit", "compile_error", "other"])
    p.add_argument("--need", default=None, help="Missing block id / capability")
    p.add_argument("--photo-id", default=None)
    p.add_argument("--template", default=None)
    p.add_argument("--notes", default="")
    p.add_argument("--path", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rec = log_failure(
        kind=args.kind,
        need=args.need,
        photo_id=args.photo_id,
        template=args.template,
        notes=args.notes,
        path=args.path,
    )
    print(json.dumps(rec, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
