"""Build a reduced-anchor dataset as a symlink farm, reproducibly.

`data/spiral_s1_anchor10` was built by hand on 2026-09-06 and no script records
how. Inspecting it before running the study found two things the registration
had wrong, neither visible without looking at the coordinates:

1. **Nine of the 59 anchors sit outside the fit's z-ROI**, so the manipulation is
   50 -> 10, not 59 -> 10.
2. **48 of the 50 in-ROI anchors are already on one z-plane** (15694); the other
   two planes hold exactly one anchor each. Taking "the first 10" keeps only the
   crowded plane and drops both lone anchors, removing 100% of the longitudinal
   spread while cutting 80% of the count. Any effect would confound the two.

So this offers two strategies and makes the difference explicit:

* ``coverage`` -- keep every z-plane that has any anchor, then fill the remainder
  from the most populated planes. Isolates COUNT at matched spatial coverage,
  which is villa's actual question ("how many do you need?").
* ``crowded`` -- take the first N from the largest collection, reproducing the
  hand-built dataset so the old artifact stays explainable.

The source dataset is never modified: every entry except `abs_winding.json` is
symlinked, and that one file is rewritten.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ABS = "abs_winding.json"


def load_anchors(path: Path) -> list[dict]:
    """Flatten every anchor to {collection, point_id, xyz}, order preserved."""
    j = json.loads(path.read_text())
    out = []
    for cid, coll in j["collections"].items():
        for pid, rec in (coll.get("points") or {}).items():
            loc = rec.get("p") or rec.get("position") or rec.get("point")
            if loc:
                out.append(
                    {
                        "collection": cid,
                        "point_id": pid,
                        "xyz": [float(v) for v in loc[:3]],
                    }
                )
    return out


def in_roi(anchors: list[dict], z0: float, z1: float) -> list[dict]:
    return [a for a in anchors if z0 <= a["xyz"][2] <= z1]


def select(anchors: list[dict], keep: int, strategy: str) -> list[dict]:
    """Pick `keep` anchors. Deterministic: no RNG, ties broken by input order."""
    if keep >= len(anchors):
        return list(anchors)
    planes: dict[int, list[dict]] = defaultdict(list)
    for a in anchors:
        planes[round(a["xyz"][2])].append(a)

    if strategy == "crowded":
        biggest = max(planes.values(), key=len)
        return biggest[:keep]

    if strategy != "coverage":
        raise ValueError(f"unknown strategy {strategy!r}")

    # One from every plane first, so spatial coverage survives the cut...
    chosen = [v[0] for v in planes.values()]
    if len(chosen) > keep:
        raise ValueError(
            f"{len(planes)} z-planes carry anchors but only {keep} may be kept; "
            "coverage cannot be preserved at this count"
        )
    # ...then fill from the most populated planes, which is where the count is.
    rest = [a for v in sorted(planes.values(), key=len, reverse=True) for a in v[1:]]
    return chosen + rest[: keep - len(chosen)]


def write_subset(src: Path, dst: Path, wanted: list[dict]) -> None:
    keep = {(a["collection"], a["point_id"]) for a in wanted}
    j = json.loads((src / ABS).read_text())
    for cid, coll in j["collections"].items():
        pts = coll.get("points") or {}
        coll["points"] = {p: r for p, r in pts.items() if (cid, p) in keep}
    dst.mkdir(parents=True, exist_ok=True)
    for entry in os.listdir(src):
        target, link = src / entry, dst / entry
        if link.is_symlink() or link.exists():
            continue
        if entry == ABS:
            continue
        link.symlink_to(target)
    (dst / ABS).write_text(json.dumps(j, indent=1) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--keep", type=int, required=True)
    ap.add_argument("--strategy", choices=("coverage", "crowded"), default="coverage")
    ap.add_argument(
        "--z-roi",
        nargs=2,
        type=float,
        default=None,
        help="report and select within this z range (the fit's ROI)",
    )
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    anchors = load_anchors(src / ABS)
    print(f"source: {len(anchors)} anchors in {src / ABS}")

    pool = anchors
    if args.z_roi:
        z0, z1 = args.z_roi
        pool = in_roi(anchors, z0, z1)
        print(
            f"  inside z-ROI [{z0:.0f}, {z1:.0f}]: {len(pool)} "
            f"({len(anchors) - len(pool)} outside are never used by the fit)"
        )

    planes = defaultdict(int)
    for a in pool:
        planes[round(a["xyz"][2])] += 1
    print(f"  z-planes in pool: {dict(sorted(planes.items()))}")

    wanted = select(pool, args.keep, args.strategy)
    kept_planes = defaultdict(int)
    for a in wanted:
        kept_planes[round(a["xyz"][2])] += 1
    print(f"\nkeeping {len(wanted)} by strategy '{args.strategy}'")
    print(f"  z-planes kept: {dict(sorted(kept_planes.items()))}")
    if set(kept_planes) == set(planes):
        print("  spatial coverage PRESERVED: every populated z-plane is represented")
    else:
        lost = sorted(set(planes) - set(kept_planes))
        print(f"  spatial coverage REDUCED: z-planes dropped entirely: {lost}")
        print("  -> count and coverage are confounded in this dataset")

    write_subset(src, dst, wanted)
    got = load_anchors(dst / ABS)
    if len(got) != len(wanted):
        raise SystemExit(f"wrote {len(got)} anchors, expected {len(wanted)}")
    missing = [e for e in os.listdir(src) if not (dst / e).exists()]
    if missing:
        raise SystemExit(f"farm incomplete, missing: {missing}")
    print(
        f"\nwrote {dst} -- {len(got)} anchors, {len(os.listdir(dst))} entries, verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
