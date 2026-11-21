"""The record of a Studio band read (finding 125), assembled from its run directory after the read: numbers only.

It changes nothing in the run. It reads, under R (the band's run directory) and ARM:
- work/gate_ARM/: the gate of each stage (snap, orient, summarise) and of each winding's step (flatten, render,
  studio), as `run_studio_band.sh` wrote them;
- work/studio_ARM/orient.json: the render orientation decided before any ink;
- work/studio_ARM/summary/summary.json: Studio's ink numbers per winding;
- work/studio_ARM/summary/orientation.json: the reading-orientation turn of each image (`band_index.py`);
- work/studio_ARM/stacked.json: consecutive windings on one surface (`studio_band.py stacked`), if run;
- work/studio_ARM/geometry.json: `band_geometry.py`'s record (normals against the axis, the predicted sheet), if run;
- work/quality_ARM.json: the fit's excess per winding;
- logs/studio_ARM_gpu_mib.log: GPU memory in use, sampled while the read ran, if sampled (the peak, and how many
  samples it is over and when);
- work/gate_chain/: a chained read's step gates (`run_band_and_read.sh`), with the size of R/inputs and
  R/dataset/tracks, if chained;
- work/fit_verdict.json: finding 112's table applied to the fit (`band_fit_verdict.py`), if run;
- work/render_ARM/wNNN_N.zarr/0/.zarray: each render's canvas (rows by columns; N layers, 66 or a centred thinner
  render), and the apparent size of the
  renders and of Studio's maps (work/studio_ARM/maps/) on disk.

usage: band_record.py R ARM OUT.json [--finding N --registration PATH --registration-commit SHA]
                      [--quality-arm FIT_ARM]
(the defaults are finding 125's; a later band read names its own)
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


def _gpu_lines(path: Path) -> list[tuple[int, int]]:
    """The log's (epoch seconds, MiB) samples; a line without a value is skipped."""
    if not path.exists():
        return []
    return [
        (int(line.split()[0]), int(line.split()[1]))
        for line in path.read_text().splitlines()
        if line.split()[1:]
    ]


def gpu_peak(path: Path) -> int | None:
    values = [mib for _, mib in _gpu_lines(path)]
    return max(values) if values else None


def gpu_samples(path: Path) -> dict | None:
    """How many samples the peak is over, and when they were taken: a sampler started late covers part of the read."""
    lines = _gpu_lines(path)
    if not lines:
        return None
    return {"count": len(lines), "first_epoch": lines[0][0], "last_epoch": lines[-1][0]}


def chain(root: Path) -> dict | None:
    """A chained read's (`run_band_and_read.sh`) step gates and the size of its inputs and tracks; None without."""
    gates = root / "work" / "gate_chain"
    if not gates.exists():
        return None
    steps_ = {p.stem: _gate(p) for p in sorted(gates.glob("*.json"))}
    return {
        "steps": steps_,
        "seconds": int(sum(g["seconds"] for g in steps_.values())),
        "bytes_on_disk": {
            "inputs": apparent_bytes(root / "inputs"),
            "tracks": apparent_bytes(root / "dataset" / "tracks"),
        },
    }


FINDING_125 = (
    125,
    "docs/preregistration/2026-11-20_first_letters_0826_studio_band.md",
    "d6e5ca0f",
)


def canvas_megapixels(renders: Path, winding: str) -> float | None:
    """A winding's render canvas, rows times columns of its level 0, in millions of pixels; None if it has none.

    The render is wNNN_N.zarr for any layer count N; two renders of one winding are refused."""
    headers = sorted(renders.glob(f"{winding}_*.zarr/0/.zarray"))
    if len(headers) > 1:
        raise SystemExit(f"{winding} has {len(headers)} renders in {renders}")
    if not headers:
        return None
    _, rows, cols = json.loads(headers[0].read_text())["shape"]
    return round(rows * cols / 1e6, 4)


def apparent_bytes(folder: Path) -> int:
    return (
        sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
        if folder.exists()
        else 0
    )


def record(
    root: Path,
    arm: str,
    finding: int = FINDING_125[0],
    registration: str = FINDING_125[1],
    registration_commit: str = FINDING_125[2],
    quality_arm: str | None = None,
) -> dict:
    """quality_arm: the fit arm whose excess the read's windings carry, when the read arm is not a fit arm (the
    chain's `fulldense`, finding 126's selected windings of arm `full` subdivided, has quality_full.json)."""
    work = root / "work"
    canvases = {
        w: c
        for w in (work / f"windings_{arm}.txt").read_text().split()
        if (c := canvas_megapixels(work / f"render_{arm}", w)) is not None
    }
    studio = work / f"studio_{arm}"
    windings = (work / f"windings_{arm}.txt").read_text().split()
    orient = json.loads((studio / "orient.json").read_text())["windings"]
    summary = json.loads((studio / "summary" / "summary.json").read_text())["windings"]
    turns = json.loads((studio / "summary" / "orientation.json").read_text())
    quality = json.loads((work / f"quality_{quality_arm or arm}.json").read_text())[
        "windings"
    ]
    stacked_path = studio / "stacked.json"
    stacked = json.loads(stacked_path.read_text()) if stacked_path.exists() else None
    geometry_path = studio / "geometry.json"
    geometry = json.loads(geometry_path.read_text()) if geometry_path.exists() else None
    fit_path = work / "fit_verdict.json"
    fit = json.loads(fit_path.read_text()) if fit_path.exists() else None
    chained = chain(root)
    gpu_log = root / "logs" / f"studio_{arm}_gpu_mib.log"

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
            **(
                {}
                if geometry is None or w not in geometry["windings"]
                else {
                    "geometry": {
                        k: geometry["windings"][w][k]
                        for k in ("trusted", "other_side", "inward_against_axis")
                    }
                    | {
                        "final_within_2": geometry["windings"][w]["predicted_sheet"][
                            "final"
                        ]["within_2"]
                    }
                }
            ),
            "read": w in summary,
            **({"render_canvas_megapixels": canvases[w]} if w in canvases else {}),
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
        "finding": finding,
        "registration": registration,
        "registration_commit": registration_commit,
        "arm": arm,
        **({"quality_arm": quality_arm} if quality_arm else {}),
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
        "render_canvas_megapixels": _spread(list(canvases.values()))
        if canvases
        else None,
        "bytes_on_disk": {
            "renders": apparent_bytes(work / f"render_{arm}"),
            "studio_maps": apparent_bytes(studio / "maps"),
        },
        "inspection_order_first_ten": ranked[:10],
        "stacked": stacked,
        "geometry": None if geometry is None else geometry["summary"],
        "gpu_peak_mib_all_processes": gpu_peak(gpu_log),
        "gpu_samples": gpu_samples(gpu_log),
        **({"chain": chained} if chained else {}),
        **({"fit": fit} if fit else {}),
        "by_winding": by_winding,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root", type=Path)
    ap.add_argument("arm")
    ap.add_argument("out", type=Path)
    ap.add_argument("--finding", type=int, default=FINDING_125[0])
    ap.add_argument("--registration", default=FINDING_125[1])
    ap.add_argument("--registration-commit", default=FINDING_125[2])
    ap.add_argument(
        "--quality-arm", help="the fit arm whose quality_ARM.json holds the excess"
    )
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    result = record(args.root, args.arm, args.finding, args.registration, args.registration_commit,
                    args.quality_arm)  # fmt: skip
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "by_winding"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
