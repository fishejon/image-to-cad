"""Tester cohort registry (Phase 4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tester:
    user_id: str
    email: str | None = None
    tier: str = "alpha"  # alpha | beta | external
    seats: int = 1
    notes: str = ""


@dataclass
class TesterCohort:
    name: str = "phase4-alpha"
    max_external: int = 20
    testers: list[Tester] = field(default_factory=list)

    def add(self, tester: Tester) -> None:
        external = sum(1 for t in self.testers if t.tier == "external")
        if tester.tier == "external" and external >= self.max_external:
            raise ValueError(f"external cohort full ({self.max_external})")
        if any(t.user_id == tester.user_id for t in self.testers):
            raise ValueError(f"duplicate user_id {tester.user_id}")
        self.testers.append(tester)

    def summary(self) -> dict[str, Any]:
        by_tier: dict[str, int] = {}
        for t in self.testers:
            by_tier[t.tier] = by_tier.get(t.tier, 0) + 1
        return {
            "name": self.name,
            "count": len(self.testers),
            "by_tier": by_tier,
            "max_external": self.max_external,
            "slots_left_external": max(0, self.max_external - by_tier.get("external", 0)),
        }
