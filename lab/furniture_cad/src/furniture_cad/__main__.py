"""CLI entry: python -m furniture_cad <export|compile|fail|lists> ..."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: python -m furniture_cad {export,compile,fail,lists} ...\n"
            "  export --demo box [--out DIR]\n"
            "  compile --template NAME --params FILE [--out DIR]\n"
            "  fail --kind missing_block --need bent_panel --photo-id ...\n"
            "  lists --parts FILE [--out plan.json]\n"
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
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
