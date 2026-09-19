"""The five placement-mechanism analyses, as committed code rather than heredocs.

Findings 38-43 were computed inline and written up from terminal output. The
numbers were right -- this script reproduces them -- but nothing in the repository
could re-derive them, and `audit_report_claims.py` silently skipped every one of
those reports because it pairs a report to an artifact and there was none.

That is the failure mode this project has already recorded once: "properties
measured once and never re-checked". This closes it for that line of work.

Each sub-analysis writes `reports/<name>.json`, which the claims auditor then binds
the prose to.

    ./.venv/bin/python scripts/analyse_placement_mechanism.py --all
    ./.venv/bin/python scripts/analyse_placement_mechanism.py --test normal_separation

All five use the same frame as the studies they reproduce: render-clean arms only
(s4-s9, all on be09a8503), three disjoint pairs, (z, theta) volume binning, and an
axis DERIVED from the sampled points -- never hardcoded, which halved an effect once.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_ink_in_volume import ink_per_cell  # noqa: E402

SPIRAL_OUT = "/home/jon/openclaw-workspace/Neo-VM/spiral_out"
NZ, NTHETA, ZRANGE, SCALE = 96, 256, (13056, 18432), 10
PAIRS = (
    ("curbase_s4", "curbase_s7"),
    ("curbase_s5", "curbase_s8"),
    ("curbase_s6", "curbase_s9"),
)
REPORTS = Path(__file__).resolve().parents[1] / "reports"


def _binned(tag, axis, root):
    """(mean radius, ink, layer centroid, sample count) per (z, theta) bin."""
    d = f"{root}/outer_{tag}/meshes/concat/w120-129_flat"
    x, y, z = (tifffile.imread(f"{d}/{c}.tif").astype(np.float64) for c in "xyz")
    ink = ink_per_cell(f"{root}/outer_{tag}", x.shape)

    tot = np.zeros(x.shape)
    cen = np.zeros(x.shape)
    for k, f in enumerate(sorted(glob.glob(f"{d}/ink/*.tif"))):
        a = tifffile.imread(f).astype(np.float64)
        H, W = x.shape
        a = a[: H * SCALE, : W * SCALE].reshape(H, SCALE, W, SCALE).mean(axis=(1, 3))
        tot += a
        cen += k * a

    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if axis is None:
        axis = (float(x[m].mean()), float(y[m].mean()))
    cx, cy = axis
    th = np.arctan2(y[m] - cy, x[m] - cx)
    r = np.hypot(x[m] - cx, y[m] - cy)
    rng = [[ZRANGE[0], ZRANGE[1]], [-np.pi, np.pi]]
    bins = [NZ, NTHETA]

    n, _, _ = np.histogram2d(z[m], th, bins=bins, range=rng)
    hr, _, _ = np.histogram2d(z[m], th, bins=bins, range=rng, weights=r)
    hi, _, _ = np.histogram2d(
        z[m], th, bins=bins, range=rng, weights=ink[m].astype(float)
    )
    ht, _, _ = np.histogram2d(z[m], th, bins=bins, range=rng, weights=tot[m])
    hc, _, _ = np.histogram2d(z[m], th, bins=bins, range=rng, weights=cen[m])
    with np.errstate(invalid="ignore", divide="ignore"):
        rad = np.where(n > 0, hr / np.maximum(n, 1), np.nan)
        lay = np.where(ht > 0, hc / np.maximum(ht, 1e-9), np.nan)
    return rad, hi, lay, n, axis


def _load(root):
    axis, cache = None, {}
    for a, b in PAIRS:
        for t in (a, b):
            if t not in cache:
                *vals, axis = _binned(t, axis, root)
                cache[t] = vals
    return cache, axis


def normal_separation(cache, axis, rng):
    """Finding 38: does normal separation predict ink disagreement?"""
    rows = []
    for a, b in PAIRS:
        ra, ia, _, _ = cache[a]
        rb, ib, _, _ = cache[b]
        ok = np.isfinite(ra) & np.isfinite(rb) & (ia > 0) & (ib > 0)
        one = int(((ia > 0) ^ (ib > 0)).sum())
        sep = np.abs(ra - rb)[ok]
        agree = np.minimum(ia, ib)[ok] / np.maximum(np.maximum(ia, ib)[ok], 1e-9)
        rho, p = spearmanr(sep, agree)
        ink_one = float(
            (ia[(ia > 0) ^ (ib > 0)].sum() + ib[(ia > 0) ^ (ib > 0)].sum())
            / (ia.sum() + ib.sum())
        )
        rows.append(
            {
                "pair": f"{a[-2:]}-{b[-2:]}",
                "bins": int(ok.sum()),
                "one_armed_bins": one,
                "one_armed_ink_fraction": round(ink_one, 4),
                "median_separation_vx": round(float(np.median(sep)), 3),
                "rho": round(float(rho), 4),
                "p": float(p),
            }
        )
    return {
        "rows": rows,
        "median_rho": round(float(np.median([r["rho"] for r in rows])), 4),
    }


def counting_noise(cache, axis, rng):
    """Finding 40: does per-bin scatter scale as sqrt(mean) or proportionally?"""
    rows = []
    for a, b in PAIRS:
        _, ia, _, _ = cache[a]
        _, ib, _, _ = cache[b]
        both = (ia > 0) & (ib > 0)
        m = (ia[both] + ib[both]) / 2.0
        d = np.abs(ia[both] - ib[both])
        keep = (m > 0) & (d > 0)
        bexp = float(np.polyfit(np.log(m[keep]), np.log(d[keep]), 1)[0])
        sh = []
        for _ in range(50):
            perm = rng.permutation(ib[both])
            ms, ds = (ia[both] + perm) / 2.0, np.abs(ia[both] - perm)
            k = (ms > 0) & (ds > 0)
            sh.append(float(np.polyfit(np.log(ms[k]), np.log(ds[k]), 1)[0]))
        rows.append(
            {
                "pair": f"{a[-2:]}-{b[-2:]}",
                "bins": int(keep.sum()),
                "ties_dropped": int((~keep & (m > 0)).sum()),
                "b": round(bexp, 4),
                "shuffled_b_95": [
                    round(float(v), 4) for v in np.percentile(sh, [2.5, 97.5])
                ],
            }
        )
    return {
        "rows": rows,
        "median_b": round(float(np.median([r["b"] for r in rows])), 4),
    }


def layer_route(cache, axis, rng):
    """Finding 41: does normal separation move the sampled depth layer?"""
    rows = []
    for a, b in PAIRS:
        ra, _, ca, ta = cache[a]
        rb, _, cb, tb = cache[b]
        ok = (
            np.isfinite(ra)
            & np.isfinite(rb)
            & np.isfinite(ca)
            & np.isfinite(cb)
            & (ta > 0)
            & (tb > 0)
        )
        sep, dc, sg = np.abs(ra - rb)[ok], np.abs(ca - cb)[ok], (ca - cb)[ok]
        rho, _ = spearmanr(sep, dc)
        rows.append(
            {
                "pair": f"{a[-2:]}-{b[-2:]}",
                "bins": int(ok.sum()),
                "median_abs_dcentroid_layers": round(float(np.median(dc)), 4),
                "signed_mean": round(float(sg.mean()), 5),
                "rho": round(float(rho), 4),
            }
        )
    return {
        "rows": rows,
        "median_rho": round(float(np.median([r["rho"] for r in rows])), 4),
    }


def sampling_density(cache, axis, rng):
    """Finding 42: does the ink ratio track the sample-count ratio?"""
    rows = []
    for a, b in PAIRS:
        _, ia, _, na = cache[a]
        _, ib, _, nb = cache[b]
        ok = (na > 0) & (nb > 0) & (ia > 0) & (ib > 0)
        dn, di = np.log(na[ok] / nb[ok]), np.log(ia[ok] / ib[ok])
        s = float(np.polyfit(dn, di, 1)[0])
        sh = [float(np.polyfit(rng.permutation(dn), di, 1)[0]) for _ in range(100)]
        rows.append(
            {
                "pair": f"{a[-2:]}-{b[-2:]}",
                "bins": int(ok.sum()),
                "s": round(s, 4),
                "log_density_ratio_p5_p95": [
                    round(float(v), 4) for v in np.percentile(dn, [5, 95])
                ],
                "shuffled_s_95": [
                    round(float(v), 4) for v in np.percentile(sh, [2.5, 97.5])
                ],
            }
        )
    return {
        "rows": rows,
        "median_s": round(float(np.median([r["s"] for r in rows])), 4),
    }


def coverage_or_density(cache, axis, rng):
    """Finding 43: does that association survive where both arms cover fully?"""
    rows = []
    for a, b in PAIRS:
        _, ia, _, na = cache[a]
        _, ib, _, nb = cache[b]
        ok = (na > 0) & (nb > 0) & (ia > 0) & (ib > 0)
        dn, di = np.log(na[ok] / nb[ok]), np.log(ia[ok] / ib[ok])
        c = np.minimum(na[ok], nb[ok])
        edges = np.percentile(c, [0, 25, 50, 75, 100])
        quarts: list[dict[str, object]] = []
        for k in range(4):
            sel = (c >= edges[k]) & (c <= edges[k + 1] if k == 3 else c < edges[k + 1])
            if sel.sum() < 30:
                quarts.append({"q": k + 1, "n": int(sel.sum()), "s": None})
                continue
            s = float(np.polyfit(dn[sel], di[sel], 1)[0])
            sh = [
                float(np.polyfit(rng.permutation(dn[sel]), di[sel], 1)[0])
                for _ in range(80)
            ]
            lo, hi = np.percentile(sh, [2.5, 97.5])
            quarts.append(
                {
                    "q": k + 1,
                    "n": int(sel.sum()),
                    "s": round(s, 4),
                    "significant": bool(not (lo <= s <= hi)),
                }
            )
        rows.append({"pair": f"{a[-2:]}-{b[-2:]}", "quartiles": quarts})
    q4 = [r["quartiles"][3]["s"] for r in rows if r["quartiles"][3]["s"] is not None]
    return {"rows": rows, "q4_median_s": round(float(np.median(q4)), 4)}


TESTS = {
    "normal_separation": (
        normal_separation,
        "normal_separation_contributes_but_does_not_explain",
    ),
    "counting_noise": (counting_noise, "the_disagreement_is_part_counting_noise"),
    "layer_route": (layer_route, "the_layer_route_is_refuted"),
    "sampling_density": (
        sampling_density,
        "sampling_density_tracks_ink_but_not_proportionally",
    ),
    "coverage_or_density": (
        coverage_or_density,
        "coverage_refuted_density_still_unexplained",
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spiral-out", default=SPIRAL_OUT)
    ap.add_argument("--test", choices=sorted(TESTS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    if not args.test and not args.all:
        raise SystemExit("choose --test <name> or --all")

    cache, axis = _load(args.spiral_out)
    print(f"axis derived from the sampled points: cx={axis[0]:.0f} cy={axis[1]:.0f}\n")
    for name in sorted(TESTS) if args.all else [args.test]:
        fn, stem = TESTS[name]
        out = fn(cache, axis, np.random.default_rng(args.seed))
        out["axis"] = [round(v, 1) for v in axis]
        out["pairs"] = [f"{a}-{b}" for a, b in PAIRS]
        path = REPORTS / f"{stem}.json"
        path.write_text(json.dumps(out, indent=1) + "\n")
        summary = {k: v for k, v in out.items() if k.startswith(("median", "q4"))}
        print(f"{name:<22} {summary}  -> reports/{stem}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
