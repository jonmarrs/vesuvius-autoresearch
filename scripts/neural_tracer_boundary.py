"""Finding 96 (exploratory, after the fact; not pre-registered): villa's neural fiber tracer cannot seed within its CT
seed context of the CT's edge, and ScrollGT's protocol gives it the cube alone.

villa's tracer reads a (2 x CT_CONTEXT_RADIUS + 1)³ window of CT around each seed dot to set its heading
(tracers/fibers/frames/ct.py `_ct_context`). If the window crosses the CT's edge it raises SeedHeadingError, and the
dot is dropped and counted as `no_heading`. Finding 91 ran it as ScrollGT's entrant on each cube's CT alone (finding
85's arrays), so every face of the cube is an edge of the CT. This measures, from finding 91's saved runs and
ScrollGT's ground truth, what that costs on each of the 21 cubes:

* the closest traced seed to a face (the rule, observed);
* the share of the seed dots dropped as `no_heading` (tiles.jsonl);
* the share of the cube where a seed's window fits (from the radius alone);
* the share of ground-truth length on fibers with a node where a seed's window fits. No trace can reach a fiber
  without a seed on it, so this caps the share of each fiber the tracer can follow from its own seed. It is a node
  test: nodes sit 1-2 voxels apart;
* finding 91's published row at tolerance 2: coverage and predicted over ground-truth length; and our tracer's
  coverage (ScrollGT's rows, findings 80 and 83), which has no such rule: on FACE_CUBE, the share of its labelled
  voxels within RADIUS of a face, beside that shell's share of the volume.

CPU only. Writes reports/neural_tracer_boundary.json.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_analysis as f91  # noqa: E402
import tolerance4_rescore as t4  # noqa: E402

RUN = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/run")
VILLA = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer/villa")
CT_STRUCTURE = "vesuvius/src/vesuvius/neural_tracing/tracers/shared/ct_structure.py"
RADIUS = 38  # CT voxels; checked against villa's source by villa_radius()
GRID_SCALE = 2  # finding 91: --ct-grid-scale 1 --grid-scale 2, so a trace-grid voxel is 2 CT voxels
FACE_CUBE = "s5_07997_02997_05497_256"


def villa_radius(villa: Path = VILLA) -> int:
    text = (villa / CT_STRUCTURE).read_text()
    m = re.search(r"^CT_CONTEXT_RADIUS = (\d+)", text, re.M)
    if m is None:
        raise ValueError("CT_CONTEXT_RADIUS not found")
    return int(m.group(1))


def seedable_grid(
    n: int, radius: int = RADIUS, scale: int = GRID_SCALE
) -> tuple[int, int]:
    """The trace-grid coordinates g (0 <= g < n / scale) whose seed window fits in an n-voxel CT axis.

    villa's window starts at floor(scale * g) - radius and spans 2 * radius + 1 voxels, so it needs
    radius <= scale * g <= n - radius - 1."""
    lo = -(-radius // scale)
    hi = (n - radius - 1) // scale
    return lo, hi


def seedable_share(n: int, radius: int = RADIUS, scale: int = GRID_SCALE) -> float:
    lo, hi = seedable_grid(n, radius, scale)
    return ((hi - lo + 1) / (n // scale)) ** 3


def reachable_share(fibers, n: int, radius: int = RADIUS) -> float:
    """Share of in-cube ground-truth length on fibers with a node whose seed window would fit.

    `fibers`: objects with `coords` (N, 3) in cube voxels and `edges` (E, 2). Length counts edges with both ends in
    the cube, as ScrollGT's loader keeps them."""
    total = reach = 0.0
    for f in fibers:
        c = np.asarray(f.coords, float)
        inside = np.all((c >= 0) & (c <= n - 1), axis=1)
        edges = np.asarray(f.edges).reshape(-1, 2)
        both = inside[edges[:, 0]] & inside[edges[:, 1]]
        length = float(
            np.linalg.norm(c[edges[both, 0]] - c[edges[both, 1]], axis=1).sum()
        )
        fl = np.floor(c)
        core = bool(np.any(np.all((fl >= radius) & (fl <= n - radius - 1), axis=1)))
        total += length
        reach += length * core
    return reach / total if total else float("nan")


def run_counts(cube: str, run: Path = RUN) -> dict:
    tiles = [
        json.loads(line)
        for line in (run / cube / "tiles.jsonl").read_text().splitlines()
        if line.strip()
    ]
    keys = (
        "dots",
        "owned_dots",
        "no_heading",
        "traced",
        "fibers",
        "traced_vox",
        "kept_vox",
    )
    out = {k: int(sum(t.get(k, 0) for t in tiles)) for k in keys}
    seeds = np.concatenate(
        [np.load(p)["seed"].reshape(-1, 3) for p in sorted((run / cube / "tiles").glob("*.npz")) if not p.name.endswith(".partial.npz")]
    )  # fmt: skip
    g = int(cube.split("_")[-1]) // GRID_SCALE
    out["seeds"] = int(len(seeds))
    out["min_seed_face_distance_grid"] = float(np.minimum(seeds, g - seeds).min())
    return out


def face_share(labels: np.ndarray, radius: int = RADIUS) -> tuple[float, float]:
    """(share of labelled voxels within `radius` of a face, share of the cube's voxels there)."""
    n = labels.shape[0]
    z, y, x = np.nonzero(labels)
    d = np.minimum.reduce([z, y, x, n - 1 - z, n - 1 - y, n - 1 - x])
    return float(np.mean(d < radius)), 1 - ((n - 2 * radius) / n) ** 3


def _range(values) -> list[float]:
    v = [float(x) for x in values]
    return [min(v), statistics.median(v), max(v)]


def summarize(rows: dict) -> dict:
    """Per size class: [min, median, max] of each measure, and whether the two classes separate."""
    out: dict = {}
    for key in ("no_heading_share", "seedable_share", "reachable_share", "neural_coverage", "neural_pred_over_gt",
                "tracer_coverage"):  # fmt: skip
        by = {
            n: _range(r[key] for r in rows.values() if r["size"] == n)
            for n in (256, 512)
        }
        out[key] = {
            "256": by[256],
            "512": by[512],
            "separate": by[256][2] < by[512][0] or by[512][2] < by[256][0],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--f91", type=Path, default=Path("reports/neural_tracer_entrant.json")
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_boundary.json")
    )
    args = ap.parse_args()
    if (r := villa_radius()) != RADIUS:
        raise SystemExit(f"villa's CT_CONTEXT_RADIUS is {r}, not {RADIUS}")
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.target import load_fiber_target

    rep = json.loads(args.f91.read_text())
    rows = {}
    for cube in f91.ALL:
        n = int(cube.split("_")[-1])
        skel, _, meta = load_fiber_target(f91.SG / "data" / f"fibers_{cube}")
        counts = run_counts(cube)
        neural = rep["neural_rows"][cube]
        rows[cube] = {
            "size": n,
            "split": meta["split"],
            **counts,
            "no_heading_share": counts["no_heading"] / counts["dots"],
            "seedable_share": seedable_share(n),
            "reachable_share": reachable_share(skel.fibers, n),
            "neural_coverage": neural["coverage"],
            "neural_pred_over_gt": neural["pred_length"] / neural["gt_length"],
            "tracer_coverage": rep["comparators"][cube]["tracer"]["coverage"],
        }
    out = {
        "status": "OK",
        "exploratory": True,
        "radius_ct_voxels": RADIUS,
        "grid_scale": GRID_SCALE,
        "seedable_grid": {str(n): list(seedable_grid(n)) for n in (256, 512)},
        "rows": rows,
        "by_size": summarize(rows),
        "tracer_face_share": dict(
            zip(
                ("labelled", "volume"),
                face_share(np.load(t4.tracer_labelling(FACE_CUBE))),
                strict=False,
            ),
            cube=FACE_CUBE,
        ),  # fmt: skip
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["by_size"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
