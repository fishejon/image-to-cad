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
    if cmd == "rebuild":

        from furniture_cad.rebuild import main as rebuild_main

        return rebuild_main(rest)
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
