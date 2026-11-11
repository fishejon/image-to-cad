"""CLI entry: python -m furniture_cad <export|compile|fail|lists|run|jobs|ab|rebuild> ..."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: python -m furniture_cad {export,compile,fail,lists,run,jobs,ab,rebuild} ...\n"
            "  export --demo box [--out DIR]\n"
            "  compile --template NAME --params FILE [--out DIR]\n"
            "  fail --kind missing_block --need bent_panel --photo-id ...\n"
            "  lists --parts FILE [--out plan.json]\n"
            "  run --script FILE [--work DIR]   # offline tool-use dry-run\n"
            "  run --freeze-set [--work DIR]    # oracle solids+lists (hand scripts; not live A)\n"
            "  run --prompt TEXT [--work DIR]  # Messages API tool-use loop\n"
            "  run --contract                  # print tools.v1.json summary\n"
            "  jobs --port 8787 [--root DIR]   # job HTTP service\n"
            "  ab [--ids …] [--out FILE]       # B/O/A scorecard (oracle ≠ product gate)\n"
            "  blind [--ids …]                 # R4 blind scorecard + decision JSON\n"
            "  score-console [--ceiling|--ir-stub]  # console_01 vs Fusion GT + hand list\n"
            "  calibrate-console                   # P0/D8 camera-fit calibration table\n"
            "  pipeline --photo PATH --known-mm W D H [--vision]  # staged IR pipeline\n"
            "  perceive --photo PATH [--features FILE] [--known-mm W D H]  # P3 vision score\n"
            "  p4-a0 [--vision|--no-vision] [--runs 3]  # P4 console A0 ×N\n"
            "  rebuild --project DIR --set KEY VAL  # no-model rebuild\n"
            "This lab is offline and NOT deployed to prod."
        )
        return 0
    cmd, rest = argv[0], argv[1:]

    if cmd == "export":
        from furniture_cad.export import main as export_main

        return export_main(rest)
    if cmd == "compile":
        from furniture_cad.compile import main as compile_main

        return compile_main(rest)
    if cmd in ("fail", "failures"):
        from furniture_cad.failures import main as fail_main

        return fail_main(rest)
    if cmd == "lists":
        from furniture_cad.lists import main as lists_main

        return lists_main(rest)
    if cmd == "run":
        from furniture_cad.tools.loop import main as run_main

        return run_main(rest)
    if cmd == "jobs":
        from furniture_cad.jobs.server import main as jobs_main

        return jobs_main(rest)
    if cmd in ("ab", "ab-score"):
        from furniture_cad.jobs.ab_score import main as ab_main

        return ab_main(rest)
    if cmd in ("blind", "blind-eval"):
        from furniture_cad.jobs.blind_eval import main as blind_main

        return blind_main(rest)
    if cmd in ("score-console", "console-gt"):
        from furniture_cad.eval.console_gt import main as console_gt_main

        return console_gt_main(rest)
    if cmd in ("calibrate-console", "calibrate"):
        from furniture_cad.eval.calibrate_cli import main as calibrate_main

        return calibrate_main(rest)
    if cmd == "pipeline":
        import argparse
        import json
        from pathlib import Path

        from furniture_cad.pipeline import run_pipeline

        p = argparse.ArgumentParser(description="Run staged IR pipeline")
        p.add_argument("--photo", type=Path, default=None)
        p.add_argument("--known-mm", nargs=3, type=float, metavar=("W", "D", "H"), required=True)
        p.add_argument("--work", type=Path, default=Path("out/pipeline"))
        p.add_argument("--ir", type=Path, default=None)
        p.add_argument("--vision", action="store_true", help="P3 Anthropic Perceive")
        args = p.parse_args(rest)
        summary = run_pipeline(
            work_dir=args.work,
            photo=args.photo,
            known_mm={"w": args.known_mm[0], "d": args.known_mm[1], "h": args.known_mm[2]},
            seed_ir=args.ir,
            use_vision=True if args.vision else None,
        )
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("ok") else 1
    if cmd == "perceive":
        import argparse
        import json
        from pathlib import Path

        from furniture_cad.eval.scorer import feature_recall
        from furniture_cad.perceive import feature_counts_from_observation, perceive_vision

        p = argparse.ArgumentParser(description="P3 vision Perceive + optional feature recall")
        p.add_argument("--photo", type=Path, required=True)
        p.add_argument("--features", type=Path, default=None, help="features.json with counts")
        p.add_argument("--known-mm", nargs=3, type=float, metavar=("W", "D", "H"), default=None)
        p.add_argument("--out", type=Path, default=None)
        args = p.parse_args(rest)
        known = None
        if args.known_mm:
            known = {"w": args.known_mm[0], "d": args.known_mm[1], "h": args.known_mm[2]}
        intake = {
            "schema": "intake.v1",
            "path": str(args.photo),
            "segmentation": {"score": 0.5, "quality": "cli"},
            "rectify": {"rectified": False},
            "scale": None,
        }
        obs = perceive_vision(intake, known_mm=known, photo=args.photo)
        pred = feature_counts_from_observation(obs)
        out: dict = {"observation": obs, "counts": pred}
        if args.features and args.features.is_file():
            truth = json.loads(args.features.read_text(encoding="utf-8")).get("counts") or {}
            out["feature_recall"] = feature_recall(pred, truth)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=2))
        fr = out.get("feature_recall") or {}
        if fr and float(fr.get("recall") or 0) < 0.9:
            return 1
        return 0 if (obs.get("meta") or {}).get("perceive") == "vision_v1" else 2
    if cmd in ("p4-a0", "p4_a0"):
        from furniture_cad.eval.p4_a0 import main as p4_main

        return p4_main(rest)
    if cmd == "rebuild":



        from furniture_cad.rebuild import main as rebuild_main

        return rebuild_main(rest)
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
