"""The record of a Studio band read (finding 125), assembled from its run directory after the read: numbers only.

It changes nothing in the run. It reads, under R (the band's run directory) and ARM:
- work/gate_ARM/: the gate of each stage (snap, orient, summarise) and of each winding's step (flatten, render,
  studio), as `run_studio_band.sh` wrote them;
- work/studio_ARM/orient.json: the render orientation decided before any ink;
- work/studio_ARM/summary/summary.json: Studio's ink numbers per winding;
- work/studio_ARM/summary/orientation.json: the reading-orientation turn of each image (`band_index.py`);
- work/studio_ARM/stacked.json: consecutive windings on one surface (`studio_band.py stacked`), if run;
- work/quality_ARM.json: the fit's excess per winding;
- logs/studio_ARM_gpu_mib.log: GPU memory in use, sampled while the read ran, if sampled.

usage: band_record.py R ARM OUT.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

STEPS = ("flatten", "render", "studio")


def _spread(values: list[float]) -> dict:
    a = np.asarray(values, dtype=np.float64)
    return {
        "median": round(float(np.median(a)), 4),
        "min": round(float(a.min()), 4),
        "max": round(float(a.max()), 4),
    }


def _gate(path: Path) -> dict:
    return json.loads(path.read_text())


def steps(gates: Path, windings: list[str]) -> dict:
    out: dict = {}
    for stage in ("snap", "orient", "summarise"):
        path = gates / f"studio_{stage}.json"
        out[stage] = _gate(path) if path.exists() else None
    for step in STEPS:
        done = {
            w: _gate(gates / f"studio_{step}_{w}.json")
            for w in windings
            if (gates / f"studio_{step}_{w}.json").exists()
        }
        seconds = [g["seconds"] for g in done.values()]
        out[step] = {
            "attempted": len(done),
            "exited_zero": sum(g["exit"] == 0 for g in done.values()),
            "failed": sorted(w for w, g in done.items() if g["exit"] != 0),
            "seconds_total": int(sum(seconds)),
            "seconds_median": int(np.median(seconds)) if seconds else None,
            "seconds_max": int(max(seconds)) if seconds else None,
        }
    return out


def gpu_peak(path: Path) -> int | None:
    if not path.exists():
        return None
    values = [
        int(line.split()[1])
        for line in path.read_text().splitlines()
        if line.split()[1:]
    ]
    return max(values) if values else None


def record(root: Path, arm: str) -> dict:
    work = root / "work"
    studio = work / f"studio_{arm}"
    windings = (work / f"windings_{arm}.txt").read_text().split()
    orient = json.loads((studio / "orient.json").read_text())["windings"]
    summary = json.loads((studio / "summary" / "summary.json").read_text())["windings"]
    turns = json.loads((studio / "summary" / "orientation.json").read_text())
    quality = json.loads((work / f"quality_{arm}.json").read_text())["windings"]
    stacked_path = studio / "stacked.json"
    stacked = json.loads(stacked_path.read_text()) if stacked_path.exists() else None

    inward = [o["share_of_normals_pointing_inward"] for o in orient.values()]
    read = sorted(summary)
    shares = [
        summary[w]["ink_share"] for w in read if summary[w]["ink_share"] is not None
    ]
    largest = [
        summary[w]["largest_tile_ink_share"]
        for w in read
        if summary[w]["largest_tile_ink_share"] is not None
    ]
    kinds = {"unturned": 0, "mirrored only": 0, "upside down only": 0, "both": 0}
    for w in read:
        lr, ud = turns[w]["flip_lr"], turns[w]["flip_ud"]
        kinds[
            "both"
            if lr and ud
            else "mirrored only"
            if lr
            else "upside down only"
            if ud
            else "unturned"
        ] += 1
    by_winding = {
        w: {
            "render": orient[w]["render"],
            "share_of_normals_pointing_inward": orient[w][
                "share_of_normals_pointing_inward"
            ],
            "excess": (quality.get(w) or {}).get("excess"),
            "read": w in summary,
            **(
                {
                    "ink_share": summary[w]["ink_share"],
                    "largest_tile_ink_share": summary[w]["largest_tile_ink_share"],
                    "tiles_scored": summary[w]["tiles_scored"],
                    "rendered_pixels": summary[w]["rendered_pixels"],
                    "flip_lr": turns[w]["flip_lr"],
                    "flip_ud": turns[w]["flip_ud"],
                }
                if w in summary
                else {}
            ),
        }
        for w in windings
    }
    ranked = sorted(
        (w for w in read if summary[w]["largest_tile_ink_share"] is not None),
        key=lambda w: (-summary[w]["largest_tile_ink_share"], w),
    )
    return {
        "finding": 125,
        "registration": "docs/preregistration/2026-11-20_first_letters_0826_studio_band.md",
        "registration_commit": "d6e5ca0f",
        "arm": arm,
        "windings": len(windings),
        "steps": steps(work / f"gate_{arm}", windings),
        "render_orientation": {
            "flip": sum(o["render"] == "flip" for o in orient.values()),
            "keep": sorted(w for w, o in orient.items() if o["render"] == "keep"),
            "share_of_normals_pointing_inward": _spread(inward),
        },
        "read": len(read),
        "reading_orientation": kinds,
        "ink_share": _spread(shares) if shares else None,
        "largest_tile_ink_share": _spread(largest) if largest else None,
        "tiles_scored": int(sum(summary[w]["tiles_scored"] for w in read)),
        "windings_with_no_tile_scored": sorted(
            w for w in read if summary[w]["tiles_scored"] == 0
        ),
        "rendered_pixels": int(sum(summary[w]["rendered_pixels"] for w in read)),
        "inspection_order_first_ten": ranked[:10],
        "stacked": stacked,
        "gpu_peak_mib_all_processes": gpu_peak(
            root / "logs" / f"studio_{arm}_gpu_mib.log"
        ),
        "by_winding": by_winding,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("arm")
    ap.add_argument("out", type=Path)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    result = record(args.root, args.arm)
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "by_winding"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
