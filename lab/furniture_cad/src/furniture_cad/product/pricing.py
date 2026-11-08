"""Pricing experiment stubs (Phase 4) — not billing; quote shapes only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PricingExperiment:
    id: str
    name: str
    price_per_job_usd: float
    included_rounds: int = 4
    hard_spend_cap_usd: float = 2.0


EXPERIMENTS = {
    "alpha_free": PricingExperiment("alpha_free", "Alpha free", 0.0, hard_spend_cap_usd=2.0),
    "beta_credit": PricingExperiment("beta_credit", "Beta $1 credit", 1.0, hard_spend_cap_usd=2.0),
    "std_job": PricingExperiment("std_job", "Standard job", 2.0, hard_spend_cap_usd=2.0),
}


def quote_job(*, experiment_id: str = "alpha_free", estimated_spend_usd: float = 1.0) -> dict[str, Any]:
    exp = EXPERIMENTS.get(experiment_id) or EXPERIMENTS["alpha_free"]
    over = estimated_spend_usd > exp.hard_spend_cap_usd
    return {
        "schema": "price_quote.v1",
        "experiment": exp.id,
        "name": exp.name,
        "price_usd": exp.price_per_job_usd,
        "estimated_spend_usd": estimated_spend_usd,
        "hard_cap_usd": exp.hard_spend_cap_usd,
        "allowed": not over,
        "reason": "over_hard_cap" if over else "ok",
    }
