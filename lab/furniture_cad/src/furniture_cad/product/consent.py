"""Consent for dataset feedback loop (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ConsentRecord:
    user_id: str
    job_id: str
    allow_dataset: bool
    allow_model_training: bool = False
    captured_at: str = ""

    def __post_init__(self) -> None:
        if not self.captured_at:
            self.captured_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "job_id": self.job_id,
            "allow_dataset": self.allow_dataset,
            "allow_model_training": self.allow_model_training,
            "captured_at": self.captured_at,
        }


def may_use_for_dataset(consent: ConsentRecord | dict[str, Any] | None) -> bool:
    """Fail closed — no consent → no dataset use."""
    if consent is None:
        return False
    if isinstance(consent, ConsentRecord):
        return bool(consent.allow_dataset)
    return bool(consent.get("allow_dataset"))
