"""Exploratory, after finding 97: why villa's neural tracer still drops seed dots with the scan around the cube.

villa's volume tracer gives each seed dot a heading in `_seed_heading` (tracers/fibers/tracing/volume.py at ccb431818)
and drops the dot, counted as `no_heading`, when there is none. In the order villa tests them:

* `edge`: the CT window around the dot crosses the CT's edge (`frames/ct.py::_ct_context`);
* `no_normal`: the CT window shows no sheet normal (`ct_sheet_normal`);
* `ambiguous`: the sheet leaves H/V ambiguous (`sheet_heading`);
* `disagree`: the CT's axis for the dot's family lies more than 35 degrees from the dot's direction, which comes from
  the presence (the reference mask's model, fiber_hz_vt) by a Hessian (`tile_dots`).

Finding 96 showed the edge rule caused the cube-only protocol's drops. Findings 97 and 98 padded the CT by 128 voxels,
and in sample the drops fell to 0.002-0.012 of the dots; on the two held-out Scroll-5 256³ cubes they stayed at 0.266
and 0.353. This re-derives each run's seed dots with villa's own tile_dots (the count must equal the run's) and gives
every dot its reason, in villa's order (on the 512³ cubes, a fixed random sample of SAMPLE dots). Near the ground truth
(within NEAR voxels of a sample of a ScrollGT centreline) it also measures the angle of the dot's presence direction,
and of the CT's family axis, to the ground-truth tangent.

A run never offers an owned dot (one on a fiber already written), so its `no_heading` counts the dots it offered, which
depend on its tracing order. This classifies every dot instead, and checks it against the run two ways: villa's own
`_seed_heading` gives the same verdict on the first CHECK dots, and every seed the run wrote (on the 512³ cubes, a
sample of SEEDS) passes.

Expected, written before it was run (guesses, not registered predictions):
  E1 (moderate) on the two held-out 256³ cubes most of the dropped dots are `disagree`, and none is `edge`;
  E2 (low) on the `disagree` dots near the ground truth, the presence direction is further from the ground-truth
     tangent than the CT's family axis is, on most of them: the mask's model, not the CT, is what disagrees;
  E3 (moderate) on every other cube fewer than 0.10 of all dots are dropped.

CPU only. Runs in villa's tracer environment (repro/fibers/setup_neural_tracer_env.sh) with HF_HUB_OFFLINE=1.
Writes reports/neural_tracer_heading_residual.json.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_placement as pl  # noqa: E402

T = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer")
RUNS = {256: T / "ct_context_run" / "neural", 512: T / "ct_context_512_run" / "neural"}
HELD_256 = ["s5_13497_01497_02497_256", "s5_16997_03997_04497_256"]
MARGIN = 128  # CT voxels of scan around each cube in findings 97 and 98
REASONS = ("edge", "no_normal", "ambiguous", "disagree", "ok")
EDGE_MESSAGE = "CT seed context crosses the volume boundary"
AGREE_DEGREES = 35.0  # villa's _seed_heading: |axis . direction| >= cos(35 degrees)
NEAR = 4.0  # CT voxels from a ground-truth sample
SAMPLE, SEEDS, CHECK, RNG_SEED = 2000, 300, 50, 0


def angle(a, b) -> float:
    """The angle between two lines, in degrees, sign free (0-90)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    c = abs(float(a @ b)) / (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.degrees(np.arccos(min(1.0, c))))


def classify(vol, xyz, family, direction, ct, ct_structure):
    """(reason, the CT's family axis or None): villa's _seed_heading's tests, in its order, told apart. `ct` and
    `ct_structure` are villa's frames/ct.py and shared/ct_structure.py."""
    try:
        context = ct._ct_context(vol, xyz)
    except ct_structure.SeedHeadingError as error:
        if str(error) != EDGE_MESSAGE:
            raise
        return "edge", None
    try:
        normal = ct_structure.ct_sheet_normal(*context)
    except ct_structure.SeedHeadingError:
        return "no_normal", None
    try:
        axis = ct.sheet_heading(normal, family)
    except ct_structure.SeedHeadingError:
        return "ambiguous", None
    if abs(axis @ np.asarray(direction)) < np.cos(
        np.radians(AGREE_DEGREES)
    ):  # villa's test, verbatim
        return "disagree", axis
    return "ok", axis


def last_tile(run: Path) -> dict:
    """The run's one tile record (its last line, as a tile finished twice counts by its last line)."""
    last = {}
    for line in (run / "tiles.jsonl").read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            last[d["tile"]] = d
    if len(last) != 1:
        raise ValueError(f"{run.name}: {len(last)} tiles, not one")
    return next(iter(last.values()))


def to_cube_zyx(xyz_grid, input_scale: float, margin: int = MARGIN) -> np.ndarray:
    """A trace-grid xyz in the padded run to (z, y, x) CT voxels of the cube itself."""
    return np.asarray(xyz_grid, float)[::-1] * input_scale - margin


def written_seeds(run: Path) -> tuple[np.ndarray, np.ndarray]:
    """The seed (grid xyz) and family of every fiber the run wrote."""
    (npz,) = sorted((run / "tiles").glob("*.npz"))
    with np.load(npz, allow_pickle=False) as z:
        return z["seed"], z["family"]


def _median(values) -> float | None:
    return statistics.median(values) if values else None


def near_gt_summary(rows: list[dict]) -> dict:
    """Per reason: the dots near the ground truth, the median angles to its tangent, and how often the CT's axis is
    the closer of the two."""
    out = {}
    for reason in REASONS:
        near = [
            r
            for r in rows
            if r["reason"] == reason and r["gt_tangent_angle_presence"] is not None
        ]
        both = [r for r in near if r["gt_tangent_angle_ct_axis"] is not None]
        out[reason] = {
            "near": len(near),
            "median_presence_to_gt": _median(
                [r["gt_tangent_angle_presence"] for r in near]
            ),
            "median_ct_axis_to_gt": _median(
                [r["gt_tangent_angle_ct_axis"] for r in both]
            ),
            "ct_axis_closer_share": (
                sum(
                    r["gt_tangent_angle_ct_axis"] < r["gt_tangent_angle_presence"]
                    for r in both
                )
                / len(both)
                if both
                else None
            ),
        }
    return out


def cube_row(
    cube: str, run: Path, model_spec, ck, path, vm, ct, ct_structure, rng
) -> dict:
    """Classify one cube's dots (see the module docstring)."""
    import zarr
    from scipy.spatial import cKDTree
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.neural_tracing.tracers.fibers.tracing.runtime import configure_volume
    from vesuvius.neural_tracing.tracers.shared.crop_sampling.normalization import (
        prepare_normalization,
    )
    from vesuvius.neural_tracing.tracers.shared.crop_sampling.volume import CTVolume

    rec = json.loads((run / "run.json").read_text())
    tile = last_tile(run)
    model_cfg, spec = model_spec[0], copy.deepcopy(model_spec[1])
    configure_volume(argparse.Namespace(**rec), spec, model_cfg, path)
    with tempfile.TemporaryDirectory() as tmp:
        prepare_normalization(Path(tmp), [spec], known=ck["ct_normalization"])
    vol = CTVolume(spec, cache_bytes=2 << 30)
    lo, hi = np.array(rec["box"]["lo"]), np.array(rec["box"]["hi"])
    ns = argparse.Namespace(threshold=rec["threshold"], dot_radius=rec["dot_radius"],
                            plane_spacing=rec["plane_spacing"], fill_spacing=rec["fill_spacing"])  # fmt: skip
    dots = vm.tile_dots(zarr.open(rec["presence"], mode="r"), lo, hi, ns)
    n = len(dots["xyz"])
    if n != tile["dots"]:
        raise ValueError(
            f"{cube}: tile_dots gives {n} dots, the run recorded {tile['dots']}"
        )
    size = int(cube.rsplit("_", 1)[1])
    pick = (
        np.arange(n)
        if size == 256
        else np.sort(rng.choice(n, size=min(SAMPLE, n), replace=False))
    )

    target = pl.f91.SG / "data" / f"fibers_{cube}"
    skel, _, _ = load_fiber_target(target)
    P, _, _, D = pl.gt_samples(skel.fibers, size)
    ok_dir = np.isfinite(D).all(axis=1)
    P, D = P[ok_dir], D[ok_dir]
    tree = cKDTree(P)

    vm._WORKER_VOL = vol
    rows, mismatches = [], 0
    for j, i in enumerate(pick):
        xyz, family, direction = (
            dots["xyz"][i],
            str(dots["family"][i]),
            dots["direction"][i],
        )
        reason, axis = classify(vol, xyz, family, direction, ct, ct_structure)
        if j < CHECK and (reason == "ok") != (
            vm._seed_heading((xyz, family, direction)) is not None
        ):
            mismatches += 1
        d, k = tree.query(to_cube_zyx(xyz, vol.input_scale), distance_upper_bound=NEAR)
        g = D[k][::-1] if np.isfinite(d) else None  # zyx -> xyz
        rows.append({
            "reason": reason,
            "family": family,
            "plane": "fill" if str(dots["plane"][i]) == "fill" else "plane",
            "presence_to_ct_axis": None if axis is None else angle(axis, direction),
            "gt_tangent_angle_presence": None if g is None else angle(direction, g),
            "gt_tangent_angle_ct_axis": None if g is None or axis is None else angle(axis, g),
        })  # fmt: skip

    seeds, families = written_seeds(run)
    s_pick = (
        np.arange(len(seeds))
        if size == 256
        else np.sort(rng.choice(len(seeds), min(SEEDS, len(seeds)), replace=False))
    )
    key = {}
    for i in range(n):
        key.setdefault((tuple(dots["xyz"][i]), str(dots["family"][i])), []).append(i)
    seed_fail, seed_unmatched = 0, 0
    for i in s_pick:
        hits = key.get((tuple(seeds[i]), str(families[i])), [])
        if not hits:
            seed_unmatched += 1
            continue
        if not any(classify(vol, dots["xyz"][h], str(dots["family"][h]), dots["direction"][h], ct, ct_structure)[0] == "ok"
                   for h in hits):  # fmt: skip
            seed_fail += 1

    counts = {r: sum(x["reason"] == r for x in rows) for r in REASONS}
    by_family = {
        f: {
            r: sum(x["reason"] == r and x["family"] == f for x in rows) for r in REASONS
        }
        for f in ("H", "V")
    }
    return {
        "recorded": {
            k: tile[k] for k in ("dots", "owned_dots", "traced", "no_heading")
        },
        "dots": n,
        "classified": len(rows),
        "counts": counts,
        "dropped_share": 1 - counts["ok"] / len(rows),
        "by_family": by_family,
        "near_gt": near_gt_summary(rows),
        "villa_check": {"dots": min(CHECK, len(rows)), "mismatches": mismatches},
        "written_seeds": {
            "checked": int(len(s_pick)),
            "failing": seed_fail,
            "unmatched": seed_unmatched,
        },
        "skeleton_sha256": hashlib.sha256(
            (target / "skeleton.npz").read_bytes()
        ).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_heading_residual.json")
    )
    ap.add_argument("--cubes", nargs="*", help="a subset, for a smoke run")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(pl.f91.SG / "src"))
    from vesuvius.neural_tracing.tracers.fibers.frames import ct
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume as vm
    from vesuvius.neural_tracing.tracers.fibers.tracing.runtime import (
        resolve_checkpoint,
    )
    from vesuvius.neural_tracing.tracers.models.checkpoint import load_checkpoint
    from vesuvius.neural_tracing.tracers.shared import ct_structure

    runs = {
        c.name: c
        for size in (256, 512)
        for c in sorted(RUNS[size].iterdir())
        if (c / "run.json").exists()
    }
    if args.cubes:
        runs = {c: runs[c] for c in args.cubes}
    checkpoints = {
        json.loads((r / "run.json").read_text())["checkpoint"] for r in runs.values()
    }
    if len(checkpoints) != 1:
        raise ValueError(f"runs from {len(checkpoints)} checkpoints")
    path = resolve_checkpoint(checkpoints.pop())
    model, _, _, spec, ck = load_checkpoint(path, "cpu")
    rng = np.random.default_rng(RNG_SEED)
    cubes = {}
    for cube, run in runs.items():
        cubes[cube] = cube_row(
            cube, run, (model.cfg, spec), ck, path, vm, ct, ct_structure, rng
        )
        r = cubes[cube]
        print(cube, r["recorded"]["no_heading"], r["counts"], round(r["dropped_share"], 3), r["villa_check"],
              r["written_seeds"], flush=True)  # fmt: skip
    out = {
        "status": "exploratory, after finding 97 (expectations E1-E3 in the script, written before it was run)",
        "villa": "ccb431818",
        "runs": {str(k): "/".join(v.parts[-3:]) for k, v in RUNS.items()},
        "agree_degrees": AGREE_DEGREES,
        "near": NEAR,
        "sample_512": SAMPLE,
        "seeds_512": SEEDS,
        "check": CHECK,
        "rng_seed": RNG_SEED,
        "cubes": cubes,
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
