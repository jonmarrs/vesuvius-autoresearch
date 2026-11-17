#!/usr/bin/env python3
"""Browse reviewed command/runtime boundaries without importing ML or running work.

Command prefixes need the arguments in their linked guides. This catalogue does
not inspect dependencies, data, checkpoints, GPU availability or readiness.
"""

import argparse
import json
import shlex
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from vesuvius_autoresearch.core.command_inventory import (
    STACKS,
    read_inventory,
    select_commands,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--command", help="show one exact command ID")
    parser.add_argument("--stack", choices=STACKS)
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit full metadata and captured inventory identity",
    )
    parser.add_argument(
        "--inventory", type=Path, default=ROOT / "configs/command_inventory.json"
    )
    args = parser.parse_args(argv)
    try:
        inventory, source = read_inventory(args.inventory)
        selected = select_commands(inventory, command=args.command, stack=args.stack)
        if args.json:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "scope": inventory["scope"],
                        "inventory_source": source,
                        "readiness": "not_checked",
                        "stacks": inventory["stacks"],
                        "commands": selected,
                    },
                    indent=2,
                    allow_nan=False,
                )
            )
        elif args.command:
            row = selected[0]
            print(f"{row['id']}: {row['summary']}")
            print(f"Command prefix: {shlex.join(row['argv'])}")
            print(
                f"Stack: {row['stack']}; layout: {row['layout']}; Villa: {row['villa']}; effects: {row['effects']}"
            )
            print(f"Needs: {row['needs']}")
            print(f"Guide: {row['guide']}")
            print("Readiness: not checked. Nothing was executed.")
        else:
            print("Reviewed command families (metadata only; readiness is not checked)")
            for row in selected:
                print(
                    f"{row['id']:<21} {row['stack']:<11} {row['layout']:<18} {row['summary']}"
                )
            print(
                "Use --command ID for requirements and the guide; no command is executed."
            )
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"command inventory: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
