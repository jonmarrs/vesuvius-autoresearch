"""Does the community `spiralcheck intrinsic` evaluator see what our fits differ by?

Implements `docs/preregistration/2026-09-24_spiralcheck_validation.md`. **Written, with
its tests, before spiralcheck was run on any of the twelve study fits.**

spiralcheck (github.com/Nicodol/spiralcheck, v0.4.0, commit d1b50e29) checks a fitted winding family
without ground truth: along rays from the umbilicus, in 10 z x 48 theta bins, it
measures the radial gap between adjacent windings and counts gaps <= 0 (violations),
gaps < 0.2 x median pitch (collapsed) and gaps > 2.5 x median pitch (inflated). Its
own validation held the fit seed fixed. This study asks three things it could not:

* Q1  how much its numbers move between fit SEEDS of one config (pooled, df 9);
* Q2  whether they separate three configs (one-way ANOVA F(2, 9));
* Q3  whether, within a config, they track the ink the fit reads (df 8), measured
      on the ten windings that are actually rendered and scored (w120-w129).

`collect` runs spiralcheck (twice per input, to gate on determinism) and writes one
JSON; `analyse` applies the registered rule to it. The rule lives in pure
functions below so the tests can exercise every branch without spiralcheck.
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
UMBILICUS = Path("/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1/umbilicus.json")
SPIRALCHECK = Path.home() / "tools" / "spiralcheck"
SPIRALCHECK_COMMIT = "d1b50e2957409a870225fb9f5dcc5e25f7a0f9da"

# fit tag -> (config, the detfit work dir holding its deterministic ink score)
ARMS: dict[str, tuple[str, str]] = {
    "anchor10cov_pilot": ("anchor10cov", "detfit_an1"),
    "anchor10cov_s2": ("anchor10cov", "detfit_an2"),
    "anchor10cov_s3": ("anchor10cov", "detfit_an3"),
    "nosamecur_s1": ("nosamecur", "detfit_ns1"),
    "nosamecur_s2": ("nosamecur", "detfit_ns2"),
    "nosamecur_s3": ("nosamecur", "detfit_ns3"),
    "curbase_s4": ("curbase", "detfit_s4"),
    "curbase_s5": ("curbase", "detfit_s5"),
    "curbase_s6": ("curbase", "detfit_s6"),
    "curbase_s7": ("curbase", "detfit_s7"),
    "curbase_s8": ("curbase", "detfit_s8"),
    "curbase_s9": ("curbase", "detfit_s9"),
}
GROUP_SIZES = {"anchor10cov": 3, "nosamecur": 3, "curbase": 6}
SCORED_WINDINGS = range(120, 130)  # what the render + ink scorer read

METRICS = (
    "violated_bin_fraction",
    "collapsed_bin_fraction",
    "inflated_bin_fraction",
    "median_pitch",
)
ALPHA = 0.05 / len(METRICS)  # Bonferroni within each question: 0.0125


# ----------------------------------------------------------------- the rule


def check_complete(rows: dict[str, dict]) -> None:
    """Refuse partial samples: all twelve fits, groups 3/3/6, nothing extra."""
    if set(rows) != set(ARMS):
        missing = sorted(set(ARMS) - set(rows))
        extra = sorted(set(rows) - set(ARMS))
        raise ValueError(f"incomplete sample: missing {missing}, unexpected {extra}")
    sizes: dict[str, int] = {}
    for tag in rows:
        sizes[ARMS[tag][0]] = sizes.get(ARMS[tag][0], 0) + 1
    if sizes != GROUP_SIZES:
        raise ValueError(f"group sizes {sizes} != registered {GROUP_SIZES}")


def metric_row(intrinsic: dict) -> dict[str, float]:
    return {
        "violated_bin_fraction": float(intrinsic["violated_bin_fraction"]),
        "collapsed_bin_fraction": float(intrinsic["collapsed_bin_fraction"]),
        "inflated_bin_fraction": float(intrinsic["n_inflated"])
        / float(intrinsic["n_bins_checked"]),
        "median_pitch": float(intrinsic["median_pitch"]),
    }


def oneway(values: list[float], groups: list[str]) -> dict[str, Any]:
    """One-way ANOVA plus the pooled within-group sd (the seed noise, Q1)."""
    x = np.asarray(values, float)
    labels = sorted(set(groups))
    g = [x[[i for i, k in enumerate(groups) if k == lab]] for lab in labels]
    grand = x.mean()
    ss_b = float(sum(len(v) * (v.mean() - grand) ** 2 for v in g))
    ss_w = float(sum(((v - v.mean()) ** 2).sum() for v in g))
    df_b, df_w = len(g) - 1, len(x) - len(g)
    within_sd = math.sqrt(ss_w / df_w)
    if ss_w == 0.0:
        f, p = (math.inf, 0.0) if ss_b > 0 else (math.nan, math.nan)
    else:
        f = (ss_b / df_b) / (ss_w / df_w)
        p = float(stats.f.sf(f, df_b, df_w))
    return {
        "F": f,
        "p": p,
        "df_between": df_b,
        "df_within": df_w,
        "pooled_within_sd": within_sd,
        "grand_mean": float(grand),
        "group_means": {
            lab: float(v.mean()) for lab, v in zip(labels, g, strict=False)
        },
    }


def within_config_r(
    x: list[float], y: list[float], groups: list[str]
) -> dict[str, float]:
    """Pearson r after removing each config's mean from both x and y (df = n - k - 1)."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    xc, yc = xa.copy(), ya.copy()
    for lab in set(groups):
        idx = [i for i, k in enumerate(groups) if k == lab]
        xc[idx] -= xa[idx].mean()
        yc[idx] -= ya[idx].mean()
    df = len(xa) - len(set(groups)) - 1
    if not xc.any() or not yc.any():
        return {"r": math.nan, "p": math.nan, "df": df}
    r = float(np.dot(xc, yc) / math.sqrt(np.dot(xc, xc) * np.dot(yc, yc)))
    r = max(-1.0, min(1.0, r))
    if abs(r) == 1.0:
        return {"r": r, "p": 0.0, "df": df}
    t = r * math.sqrt(df / (1 - r * r))
    return {"r": r, "p": float(2 * stats.t.sf(abs(t), df)), "df": df}


def r_critical(df: int, alpha: float = ALPHA) -> float:
    t = float(stats.t.isf(alpha / 2, df))
    return t / math.sqrt(t * t + df)


def q2_verdict(values: list[float], groups: list[str]) -> tuple[str, dict]:
    if len(set(values)) == 1:
        return "UNINFORMATIVE", {"reason": "identical on all twelve fits"}
    a = oneway(values, groups)
    return ("SEPARATES CONFIGS" if a["p"] < ALPHA else "DOES NOT SEPARATE"), a


def q3_verdict(
    values: list[float], ink: list[float], groups: list[str]
) -> tuple[str, dict]:
    if len(set(values)) == 1:
        return "UNINFORMATIVE", {"reason": "identical on all twelve fits"}
    c = within_config_r(values, ink, groups)
    if math.isnan(c["r"]):
        return "UNINFORMATIVE", {"reason": "no within-config variation", **c}
    if c["p"] < ALPHA:
        return ("TRACKS INK (+)" if c["r"] > 0 else "TRACKS INK (-)"), c
    return "NO DETECTED RELATION", c


def decide(data: dict) -> dict:
    """The registered rule. `data` is what `collect` writes."""
    rows = data["fits"]
    check_complete(rows)
    nondet = sorted(t for t, r in rows.items() if not all(r["deterministic"].values()))
    if nondet:
        return {
            "verdict": "INSTRUMENT NONDETERMINISTIC",
            "detail": f"repeat runs differed on {nondet}; no Q1-Q3 verdict is issued",
        }
    tags = sorted(rows)
    groups = [ARMS[t][0] for t in tags]
    ink = [float(rows[t]["total_fg_pixels"]) for t in tags]
    sat = [float(rows[t]["satisfied_area_fraction"]) for t in tags]

    q2 = {m: q2_verdict([rows[t]["all"][m] for t in tags], groups) for m in METRICS}
    q3 = {
        m: q3_verdict([rows[t]["scored"][m] for t in tags], ink, groups)
        for m in METRICS
    }
    # descriptive only: agreement with villa's own geometry score, and seed noise
    # of the scored-region metrics
    q4 = {
        m: within_config_r([rows[t]["all"][m] for t in tags], sat, groups)
        for m in METRICS
    }
    q1_scored = {
        m: oneway([rows[t]["scored"][m] for t in tags], groups) for m in METRICS
    }

    if any(v[0].startswith("TRACKS INK") for v in q3.values()):
        head = "READING-RELEVANT"
        text = "Within a config, at least one spiralcheck metric tracks the ink the fit reads."
    elif any(v[0] == "SEPARATES CONFIGS" for v in q2.values()):
        head = "GEOMETRY-ONLY"
        text = (
            "spiralcheck separates configs but none of its metrics tracks ink within a config "
            f"(any |r| below {r_critical(8):.2f} is not excluded)."
        )
    else:
        head = "NOT DISCRIMINATING HERE"
        text = "spiralcheck neither separates these three configs nor tracks ink within them."
    return {
        "verdict": head,
        "detail": text,
        "alpha": ALPHA,
        "r_critical_df8": r_critical(8),
        "q2_all": {m: {"verdict": v[0], **v[1]} for m, v in q2.items()},
        "q3_scored": {m: {"verdict": v[0], **v[1]} for m, v in q3.items()},
        "q4_all_vs_satisfaction": q4,
        "q1_scored": q1_scored,
    }


# ------------------------------------------------------------------ collect


def _run_intrinsic(meshes: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv", "run", "--project", str(SPIRALCHECK), "spiralcheck", "intrinsic",
        "--meshes", str(meshes), "--out", str(out), "--umbilicus", str(UMBILICUS),
    ]  # fmt: skip
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads((out / "report.json").read_text())


def _scored_subset(fitted: Path, tag: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for w in SCORED_WINDINGS:
        src = fitted / f"w{w:03d}_spliced_{tag}"
        if not src.is_dir():
            raise FileNotFoundError(src)
        link = dest / src.name
        if not link.exists():
            link.symlink_to(src)
    return dest


def collect(out_dir: Path) -> dict:
    head = subprocess.run(
        ["git", "-C", str(SPIRALCHECK), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip
    if head != SPIRALCHECK_COMMIT:
        raise RuntimeError(f"spiralcheck at {head}, registered {SPIRALCHECK_COMMIT}")
    fits: dict[str, dict] = {}
    for tag, (_, det) in ARMS.items():
        run_dir = next(SPIRAL_OUT.glob(f"*-patch_{tag}"))
        fitted = run_dir / "meshes" / f"fitted_{tag}"
        inputs = {
            "all": fitted,
            "scored": _scored_subset(fitted, tag, out_dir / tag / "scored_in"),
        }
        row: dict = {"fit_dir": str(fitted), "deterministic": {}}
        for scope, meshes in inputs.items():
            a = _run_intrinsic(meshes, out_dir / tag / f"{scope}_run1")
            b = _run_intrinsic(meshes, out_dir / tag / f"{scope}_run2")
            row["deterministic"][scope] = a["intrinsic"] == b["intrinsic"]
            row[scope] = metric_row(a["intrinsic"])
            row[f"{scope}_n_windings"] = a["meta"]["n_windings"]
        ink = json.loads((SPIRAL_OUT / det / "ink_metric" / "metrics.json").read_text())
        row["total_fg_pixels"] = ink["summary"]["total_fg_pixels"]
        sat = json.loads((run_dir / "satisfaction_metrics_fitted.json").read_text())
        row["satisfied_area_fraction"] = sat["summary"]["satisfied_area_fraction"]
        fits[tag] = row
        print(tag, row["all"], row["scored"], flush=True)
    return {"spiralcheck_commit": head, "umbilicus": str(UMBILICUS), "fits": fits}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument(
        "--work", type=Path, required=True, help="spiralcheck outputs go here"
    )
    c.add_argument("--json", type=Path, required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--json", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "collect":
        args.json.write_text(json.dumps(collect(args.work), indent=2) + "\n")
        return 0
    res = decide(json.loads(args.json.read_text()))
    args.out.write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(res["verdict"], "-", res["detail"])
    for q in ("q2_all", "q3_scored"):
        for m, v in res.get(q, {}).items():
            print(f"  {q:10s} {m:24s} {v['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
