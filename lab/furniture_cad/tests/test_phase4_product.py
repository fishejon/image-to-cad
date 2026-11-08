"""Phase 4: cohort, consent, pricing, capture guidance, export pack."""

from __future__ import annotations

from pathlib import Path

import pytest

from furniture_cad.construct import compile_ir
from furniture_cad.export_integrations import export_pack
from furniture_cad.product import (
    ConsentRecord,
    capture_checklist,
    may_use_for_dataset,
    quote_job,
)
from furniture_cad.product import cohort as cohort_mod
from furniture_cad.product import pricing as pricing_mod


CAD = Path(__file__).resolve().parents[1]
IR = CAD / "examples" / "ir" / "console_stub.ir.json"


def test_cohort_consent_pricing_capture() -> None:
    cohort = cohort_mod.TesterCohort(max_external=2)
    cohort.add(cohort_mod.Tester("u1", tier="alpha"))
    cohort.add(cohort_mod.Tester("u2", tier="external"))
    assert cohort.summary()["slots_left_external"] == 1
    with pytest.raises(ValueError):
        cohort.add(cohort_mod.Tester("u1", tier="alpha"))

    assert may_use_for_dataset(None) is False
    c = ConsentRecord("u1", "job1", allow_dataset=True)
    assert may_use_for_dataset(c) is True
    assert may_use_for_dataset({"allow_dataset": False}) is False

    q = quote_job(experiment_id="std_job", estimated_spend_usd=1.5)
    assert q["allowed"] is True
    assert quote_job(estimated_spend_usd=3.0)["allowed"] is False
    assert isinstance(pricing_mod.PricingExperiment("x", "X", 1.0), pricing_mod.PricingExperiment)

    guide = capture_checklist(piece_class="casegood.console")
    assert guide["require_known_dim"] is True
    assert any(v["role"] == "front" and v["required"] for v in guide["views"])


def test_export_pack(tmp_path: Path) -> None:
    result = compile_ir(IR)
    paths = export_pack(
        assembly=result["assembly"],
        ir=result["ir"],
        cut_list_v2=result["cut_list_v2"],
        out_dir=tmp_path,
        stem="console",
    )
    assert Path(paths["step"]).is_file()
    assert Path(paths["sketchup_json"]).is_file()
    assert "LWPOLYLINE" in Path(paths["cnc_dxf"]).read_text()
