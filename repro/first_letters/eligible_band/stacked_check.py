"""Finding 113, step 3: is a chosen winding, after the snap, on the same sheet as an index neighbour?

A chosen winding is stacked on a neighbour if at least STACKED_SHARE of its nodes lie within WITHIN voxels of
the neighbour's snapped surface, along that surface's normal. A stacked winding is still read. If two chosen
windings are stacked on each other, the one with the lower excess is dropped.

usage: stacked_check.py OUT.json READ.txt SNAP_DIR CHOSEN.txt QUALITY.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pherc343" / "mesh_step"))

import mesh_step_analysis as analysis  # noqa: E402

STACKED_SHARE = 0.30
WITHIN = "2"  # voxels; a key of surface_distance's fraction_within


def is_stacked(share_within: float) -> bool:
    return share_within >= STACKED_SHARE


def keep(
    chosen: list[str], stacked_on: dict[str, list[str]], excess: dict[str, float]
) -> list[str]:
    """Chosen windings in order, without the lower-excess one of any pair stacked on each other."""
    dropped: set[str] = set()
    for name in chosen:
        for other in stacked_on.get(name, []):
            if other in chosen and name not in dropped and other not in dropped:
                dropped.add(min((name, other), key=lambda n: (excess[n], n)))
    return [name for name in chosen if name not in dropped]


def main(argv: list[str] | None = None) -> int:
    out, read_out, snap, chosen_file, quality = (
        Path(p) for p in (argv if argv is not None else sys.argv[1:])
    )
    for path in (out, read_out):
        if path.exists():
            print(f"{path} exists: this is measured once", file=sys.stderr)
            return 2
    chosen = chosen_file.read_text().split()
    scores = json.loads(quality.read_text())["windings"]
    surfaces = {
        folder.name: analysis.load_tifxyz(folder)
        for folder in sorted(snap.glob("w*"))
        if (folder / "x.tif").exists()
    }
    pairs: dict[str, dict] = {}
    stacked_on: dict[str, list[str]] = {}
    for name in chosen:
        number = int(name[1:])
        others = [f"w{number - 1:03d}", f"w{number + 1:03d}"] + [
            c for c in chosen if c != name
        ]
        for other in dict.fromkeys(others):
            if other not in surfaces:
                continue
            distance = analysis.surface_distance(*surfaces[name], *surfaces[other])
            share = distance["fraction_within"][WITHIN]
            pairs[f"{name}->{other}"] = {
                "share_within_2": share,
                "median": distance["median"],
                "covered": distance["covered_fraction"],
                "stacked": is_stacked(share),
            }
            if is_stacked(share):
                stacked_on.setdefault(name, []).append(other)
    kept = keep(chosen, stacked_on, {n: scores[n]["excess"] for n in chosen})
    result = {
        "chosen": len(chosen),
        "stacked_on_a_neighbour": sum(1 for name in chosen if stacked_on.get(name)),
        "dropped": len(chosen) - len(kept),
        "read": len(kept),
        "pairs": pairs,
    }
    out.write_text(json.dumps(result, indent=1) + "\n")
    read_out.write_text("\n".join(kept) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "pairs"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
