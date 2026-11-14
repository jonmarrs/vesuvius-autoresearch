"""Finding 113, step 1: which windings of a scored fit are read for ink, and which are snapped with them.

Of the windings whose excess is at least MINIMUM, in index order, cut into GROUPS consecutive groups of equal
size (the last may be smaller): the highest excess in each. Both index neighbours of each are snapped too, for
the stacked check.

usage: choose_windings.py QUALITY.json CHOSEN.txt SNAP_LIST.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MINIMUM = 0.07
GROUPS = 4


def index(name: str) -> int:
    return int(name[1:])


def choose(windings: dict[str, dict | None]) -> list[str]:
    good = sorted(
        (
            name
            for name, w in windings.items()
            if w is not None and w["excess"] >= MINIMUM
        ),
        key=index,
    )
    if not good:
        return []
    size = -(-len(good) // GROUPS)
    return [
        max(
            good[start : start + size],
            key=lambda name: (windings[name]["excess"], -index(name)),
        )
        for start in range(0, len(good), size)
    ]


def with_neighbours(chosen: list[str], windings: dict[str, dict | None]) -> list[str]:
    """The chosen windings and the windings one index either side of each, where the fit wrote them."""
    names = set()
    for name in chosen:
        for step in (-1, 0, 1):
            other = f"w{index(name) + step:03d}"
            if other in windings:
                names.add(other)
    return sorted(names, key=index)


def main(argv: list[str] | None = None) -> int:
    quality, chosen_out, snap_out = (
        Path(p) for p in (argv if argv is not None else sys.argv[1:])
    )
    for out in (chosen_out, snap_out):
        if out.exists():
            print(f"{out} exists: the choice is made once", file=sys.stderr)
            return 2
    windings = json.loads(quality.read_text())["windings"]
    chosen = choose(windings)
    if not chosen:
        print("no winding reaches the minimum excess", file=sys.stderr)
        return 1
    chosen_out.write_text("\n".join(chosen) + "\n")
    snap_out.write_text("\n".join(with_neighbours(chosen, windings)) + "\n")
    print(f"chosen {len(chosen)}, to snap {len(with_neighbours(chosen, windings))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
