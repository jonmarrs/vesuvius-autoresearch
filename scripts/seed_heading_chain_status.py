#!/usr/bin/env python3
"""Inspect seed-heading re-run completion without loading arrays or GPU code.

Completion is a successful latest attempt plus mechanically present outputs;
it does not establish input identity, numerical equivalence or scientific merit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CUBES = ("s5_13497_01497_02497_256", "s5_16997_03997_04497_256")
SIDES = ("before", "after")
EVENTS = {"TRACE", "DONE", "FAILED"}


def last_events(work: Path) -> dict[tuple[str, str], str]:
    """A later TRACE or FAILED invalidates an older DONE; SKIP_DONE is a notice."""
    path = work / "chain.log"
    try:
        contents = path.read_text()
    except FileNotFoundError:
        return {}
    events = {}
    for number, line in enumerate(contents.splitlines(), 1):
        fields = line.split()
        if not fields or fields[0] not in EVENTS:
            continue
        if len(fields) < 3 or fields[1] not in SIDES or fields[2] not in CUBES:
            raise ValueError(f"malformed run event in {path}:{number}")
        events[fields[1], fields[2]] = fields[0]
    return events


def output_problems(run: Path, *, require_afv: bool = False) -> list[str]:
    """Check closed output presence only; the comparison validates file contents."""
    problems = []
    for name in ("run.json", "tiles.jsonl", *(("fibers.afv",) if require_afv else ())):
        path = run / name
        if not path.is_file() or path.stat().st_size == 0:
            problems.append(f"missing or empty {name}")
    tiles = run / "tiles"
    paths = sorted(tiles.glob("*.npz"))
    partials = [path for path in paths if path.name.endswith(".partial.npz")]
    finished = [path for path in paths if path not in partials]
    if partials:
        problems.append("interrupted .partial.npz tiles remain")
    if not finished:
        problems.append("no finished tile files")
    elif any(not path.is_file() or path.stat().st_size == 0 for path in finished):
        problems.append("finished tile path is not a nonempty regular file")
    return problems


def inspect_run(work: Path, side: str, cube: str, *, require_afv=False) -> dict:
    if side not in SIDES or cube not in CUBES:
        raise ValueError("unknown seed-heading side or cube")
    event = last_events(work).get((side, cube))
    problems = output_problems(work / side / cube, require_afv=require_afv)
    complete = event == "DONE" and not problems
    return {
        "side": side,
        "cube": cube,
        "last_event": event,
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "output_problems": problems,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser(
        "status", help="Inspect the latest attempts and outputs"
    )
    status.add_argument("--work", type=Path, required=True)
    status.add_argument("--side", choices=SIDES)
    status.add_argument("--cube", choices=CUBES)
    status.add_argument("--require-afv", action="store_true")
    outputs = commands.add_parser(
        "outputs", help="Check output presence after a trace exits"
    )
    outputs.add_argument("--run", type=Path, required=True)
    outputs.add_argument("--require-afv", action="store_true")
    args = parser.parse_args(argv)
    report: dict
    try:
        if args.command == "outputs":
            problems = output_problems(args.run, require_afv=args.require_afv)
            report = {
                "status": "INCOMPLETE" if problems else "COMPLETE",
                "output_problems": problems,
            }
        else:
            if bool(args.side) != bool(args.cube):
                parser.error("--side and --cube must be supplied together")
            rows = [
                inspect_run(args.work, side, cube, require_afv=args.require_afv)
                for side in ((args.side,) if args.side else SIDES)
                for cube in ((args.cube,) if args.cube else CUBES)
            ]
            report = {
                "status": "COMPLETE"
                if all(row["status"] == "COMPLETE" for row in rows)
                else "INCOMPLETE",
                "runs": rows,
            }
        report["scope"] = (
            "latest attempt and output presence; contents and input identity unverified"
        )
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "COMPLETE" else 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "UNKNOWN", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
