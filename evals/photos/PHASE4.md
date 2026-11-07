# Phase 4 — Editable parts / no-model rebuild

**Status: GATE PASSED.** Saved `build_script.py` rebuilds with `--set KEY VAL` in &lt; 5 s (no model).

## Commands

```bash
python -m furniture_cad run --freeze-set case_01 --work out/proj
python -m furniture_cad rebuild --project out/proj/case_01 --set W 750 --set H 1500
```
