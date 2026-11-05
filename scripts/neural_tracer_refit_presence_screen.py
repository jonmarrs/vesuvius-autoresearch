"""After finding 104 (reports/neural_tracer_refit_retry.md), an exploratory screen, not registered: could presence tell
the trace villa's refit retry adds on the reference from what it adds off it? If it could, a presence-gated retry would
be a candidate rule; if not, presence alone cannot make the retry precise.

On each held-out cube, the added trace is every voxel the refit run labels and the baseline run does not (finding 104's
runs, rasterised as they were scored). A voxel is on the reference when it lies within 2 voxels of a hand-traced fiber,
exactly as ScrollGT's precision counts it; the script checks that it reproduces each baseline row's predicted length
and precision. Presence is finding 91's fiber_hz_vt level, which the tracer read, at its half resolution.

Reports by cube and pooled: the AUC of presence between on- and off-reference added voxels (and, for comparison,
baseline voxels), and the share of each kept by a presence threshold. Development data: findings 91-104 used these
cubes. It decides nothing. Writes reports/evidence/neural_tracer_refit_presence_screen_2026-11-03.json once.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import neural_tracer_refit_retry as rr  # noqa: E402

cc, sh, f91 = rr.cc, rr.sh, rr.f91
RESULT = Path("reports/neural_tracer_refit_retry.json")
PRESENCE = cc.T / "presence"
TOL = 2.0
THRESHOLDS = (32, 64, 96, 128, 160, 192, 224, 240)


def gt_near(skel, shape, tol: float = TOL, step: float = 0.5) -> np.ndarray:
    """Voxels within tol of a ground-truth fiber, as scrollgt.fibers.eval_trace.score_tracing's precision builds them."""
    from scipy import ndimage
    from scrollgt.fibers.eval_trace import _resample_fiber

    mask = np.zeros(shape, bool)
    for fiber in skel.fibers:
        for p, _ in _resample_fiber(fiber.coords, fiber.edges, step=step):
            if p is None:
                continue
            idx = tuple(int(round(v)) for v in p)
            if all(0 <= idx[a] < shape[a] for a in range(3)):
                mask[idx] = True
    return ndimage.distance_transform_edt(~mask) <= tol


def auc_counts(pos: np.ndarray, neg: np.ndarray) -> float | None:
    """P(a uint8 value from pos exceeds one from neg), ties counted half: exact, from the two histograms."""
    hp = np.bincount(pos, minlength=256).astype(np.float64)
    hn = np.bincount(neg, minlength=256).astype(np.float64)
    if hp.sum() == 0 or hn.sum() == 0:
        return None
    below = np.concatenate([[0.0], np.cumsum(hn)[:-1]])
    return float((hp * (below + 0.5 * hn)).sum() / (hp.sum() * hn.sum()))


def pooled(per_cube: dict) -> dict:
    """The held-out cubes together, from each cube's histograms of added on- and off-reference presence."""
    on = sum(np.asarray(r["hist_added_on"], np.int64) for r in per_cube.values())
    off = sum(np.asarray(r["hist_added_off"], np.int64) for r in per_cube.values())
    n_on, n_off = int(on.sum()), int(off.sum())
    keep = {}
    for t in THRESHOLDS:
        k_on, k_off = int(on[t:].sum()), int(off[t:].sum())
        keep[t] = {
            "on": k_on / n_on,
            "off": k_off / n_off,
            "on_share": k_on / (k_on + k_off),
        }
    base_on = sum(r["base_on"] for r in per_cube.values())
    base = sum(r["base_vox"] for r in per_cube.values())
    return {
        "added": n_on + n_off,
        "added_on": n_on,
        "added_on_share": n_on / (n_on + n_off),
        "base_precision": base_on / base,
        "kept_at": keep,
    }


def screen_cube(
    cube: str, base_row: dict, work: Path = cc.T / "refit_retry_run"
) -> dict:
    import zarr
    from scrollgt.fibers.target import load_fiber_target

    n = sh.size_of(cube)
    skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{cube}")
    near = gt_near(skel, (n,) * 3)
    base = (
        cc.labels_in_cube(
            rr.BASE_RUNS[n] / "neural" / cube / "fibers.afv", rr.MARGIN, n
        )
        > 0
    )
    refit = cc.labels_in_cube(work / "refit" / cube / "fibers.afv", rr.MARGIN, n) > 0
    level = zarr.open(str(PRESENCE / f"{cube}_presence.zarr" / "1"), mode="r")[...]
    p = np.repeat(np.repeat(np.repeat(level, 2, 0), 2, 1), 2, 2)[:n, :n, :n]
    added = refit & ~base
    a_on, a_off = p[added & near], p[added & ~near]
    b_on, b_off = p[base & near], p[base & ~near]
    rec = {
        "added": int(added.sum()),
        "added_on": int(a_on.size),
        "base_vox": int(base.sum()),
        "base_on": int(b_on.size),
        "auc_added": auc_counts(a_on, a_off),
        "auc_base": auc_counts(b_on, b_off),
        "median_presence": {k: float(np.median(v)) for k, v in
                            (("added_on", a_on), ("added_off", a_off), ("base_on", b_on), ("base_off", b_off))},
        "hist_added_on": np.bincount(a_on, minlength=256).tolist(),
        "hist_added_off": np.bincount(a_off, minlength=256).tolist(),
    }  # fmt: skip
    # The on-reference test is ScrollGT's: it must give the baseline row's predicted length and precision.
    rec["reproduces_baseline_row"] = bool(
        rec["base_vox"] == round(base_row["pred_length"])
        and round(rec["base_on"] / rec["base_vox"], 4) == base_row["precision"]
    )
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", type=Path, default=cc.T / "refit_retry_run")
    ap.add_argument("--out", type=Path, default=Path("reports/evidence/neural_tracer_refit_presence_screen_2026-11-03.json"))  # fmt: skip
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: the screen writes its record once")
    sys.path.insert(0, str(f91.SG / "src"))
    base_rows = json.loads(RESULT.read_text())["baseline_rows_tol2"]
    per_cube = {}
    for c in rr.HELD:
        per_cube[c] = screen_cube(c, base_rows[c], a.work)
        r = per_cube[c]
        print(c, r["reproduces_baseline_row"], r["added"], r["added_on"], round(r["auc_added"], 3), round(r["auc_base"], 3), flush=True)  # fmt: skip
    out = {
        "after": "reports/neural_tracer_refit_retry.md (finding 104); not registered, decides nothing",
        "tolerance": TOL,
        "per_cube": per_cube,
        "pooled": pooled(per_cube),
    }
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print("wrote", a.out)
    return 0 if all(r["reproduces_baseline_row"] for r in per_cube.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
