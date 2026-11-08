"""Phase 4 productization — cohort, consent, pricing, capture guidance."""

from furniture_cad.product.capture_guidance import capture_checklist
from furniture_cad.product.cohort import TesterCohort
from furniture_cad.product.consent import ConsentRecord, may_use_for_dataset
from furniture_cad.product.pricing import PricingExperiment, quote_job

__all__ = [
    "TesterCohort",
    "ConsentRecord",
    "may_use_for_dataset",
    "PricingExperiment",
    "quote_job",
    "capture_checklist",
]
