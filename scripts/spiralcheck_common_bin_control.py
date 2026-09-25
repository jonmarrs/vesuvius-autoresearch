"""Post-hoc control: is anchor10cov's smaller outer pitch composition or spacing?

Not registered. Recomputes spiralcheck's per-(pair, z, theta) radial gaps for the
twelve fits' scored windings on SHARED z edges and only the cells valid in all
twelve, and the anchor gate's median-radius-step measure, for comparison. See
`reports/spiralcheck_is_not_discriminating_here.md`. Runs in spiralcheck's env:

    uv run --project ~/tools/spiralcheck python scripts/spiralcheck_common_bin_control.py \
        scripts reports/spiralcheck_validation/common_bins.json <collect --work dir>
"""

import json
import sys
from pathlib import Path

import numpy as np
from spiralcheck.intrinsic import resolve_umbilicus
from spiralcheck.io_tifxyz import load_run_windings

sys.path.insert(0, sys.argv[1])  # repo scripts dir
from analyse_spiralcheck_validation import ARMS, UMBILICUS  # noqa: E402

WORK = Path(sys.argv[3])  # the `collect --work` dir (holds <tag>/scored_in symlinks)
umb_json = json.loads(UMBILICUS.read_text())
ZB, TB, MINC = 10, 48, 3

fams = {t: load_run_windings(WORK / t / "scored_in") for t in ARMS}
allz = np.concatenate([s.valid_zyxs[:, 0] for f in fams.values() for s in f.values()])
z_edges = np.linspace(allz.min(), allz.max() + 1e-6, ZB + 1)
umb = resolve_umbilicus(umb_json, (z_edges[:-1] + z_edges[1:]) / 2)

gaps, gate = {}, {}
for t, fam in fams.items():
    wids = sorted(fam)
    sums = np.zeros((len(wids), ZB, TB))
    cnt = np.zeros((len(wids), ZB, TB), np.int64)
    xs, ys = [], []
    for wi, w in enumerate(wids):
        p = fam[w].valid_zyxs.astype(np.float64)
        zi = np.clip(np.searchsorted(z_edges, p[:, 0], side="right") - 1, 0, ZB - 1)
        yx = p[:, 1:] - umb[zi]
        r = np.linalg.norm(yx, axis=-1)
        ti = np.clip(
            ((np.arctan2(yx[:, 0], yx[:, 1]) + np.pi) / (2 * np.pi) * TB).astype(int),
            0,
            TB - 1,
        )
        np.add.at(sums, (wi, zi, ti), r)
        np.add.at(cnt, (wi, zi, ti), 1)
        ys.append(p[:, 1])
        xs.append(p[:, 2])
    mr = np.where(cnt >= MINC, sums / np.maximum(cnt, 1), np.nan)
    gaps[t] = np.diff(mr, axis=0)  # (9, ZB, TB)
    # the anchor gate's measure: step of per-winding median radius about the strip centroid
    cx, cy = np.median(np.concatenate(xs)), np.median(np.concatenate(ys))
    meds = [np.median(np.hypot(x - cx, y - cy)) for x, y in zip(xs, ys, strict=False)]
    gate[t] = float(np.median(np.diff(meds)))

common = np.all([np.isfinite(g) for g in gaps.values()], axis=0)
print("common (pair, z, theta) cells:", int(common.sum()), "of", common.size)
rows = {}
for t in sorted(ARMS):
    g = gaps[t][common]
    per_pair = [
        float(np.nanmedian(np.where(common[k], gaps[t][k], np.nan))) for k in range(9)
    ]
    rows[t] = {
        "config": ARMS[t][0],
        "median_gap_common": float(np.median(g)),
        "mean_gap_common": float(np.mean(g)),
        "frac_gap_gt_2.5x13": float((g > 2.5 * 13.0).mean()),
        "per_pair_median": [round(v, 2) for v in per_pair],
        "gate_median_radius_step": gate[t],
    }
    r = rows[t]
    print(
        f"{t:18s} {r['config']:12s} med {r['median_gap_common']:6.2f} mean {r['mean_gap_common']:6.2f} "
        f"infl {r['frac_gap_gt_2.5x13']:.4f} gate {r['gate_median_radius_step']:6.2f} pairs {r['per_pair_median']}"
    )
Path(sys.argv[2]).write_text(
    json.dumps({"n_common": int(common.sum()), "rows": rows}, indent=2) + "\n"
)
