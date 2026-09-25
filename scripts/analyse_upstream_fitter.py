"""Does villa's updated fitter change the ink our region yields?

Implements `docs/preregistration/2026-09-24_upstream_fitter.md`. **Written, with its
tests, before any upstream arm was fitted.**

Three fits on villa `75c79ac5f` (the fitter after the 09-14 series and #1871
"Spiral simplification"), each flattened, rendered and scored on EXACTLY the
pinned path the six `curbase_s4..s9` baselines used: villa `be09a8503`, the same
render image, `FLATTEN_DETERMINISTIC=1`. Only the fitter differs, so any change in
`total_fg_pixels` is the fitter's.

Gates, checked before any statistic:

* all nine arms scored (partial samples are refused);
* every arm's render tree is `be09a8503` and every arm used the same render image
  with `flatten_deterministic=1`;
* every upstream arm records `FIT_TREE` = `75c79ac5f`.

A failed gate yields INVALID and no verdict.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_anchor_ablation import relative_ci  # noqa: E402

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
RENDER_TREE = "be09a85035059fd83471b1632b5898c62f2c65b1"
UPSTREAM_TREE = "75c79ac5f"
BASELINE = (
    "detfit_s4",
    "detfit_s5",
    "detfit_s6",
    "detfit_s7",
    "detfit_s8",
    "detfit_s9",
)
UPSTREAM = ("detfit_up1", "detfit_up2", "detfit_up3")
# the fit run each upstream work dir was built from (satisfaction lives there)
UPSTREAM_FIT_TAG = {
    "detfit_up1": "upfit_s1",
    "detfit_up2": "upfit_s2",
    "detfit_up3": "upfit_s3",
}
INK = "total_fg_pixels"


def read_arm(work: Path) -> dict:
    """Everything the rule needs from one work dir; missing files raise."""
    ink = json.loads((work / "ink_metric" / "metrics.json").read_text())["summary"][INK]
    img = dict(
        line.split("=", 1)
        for line in (work / "RENDER_IMAGE").read_text().split()
        if "=" in line
    )
    fit_tree = work / "FIT_TREE"
    return {
        "ink": float(ink),
        "villa_sha": (work / "VILLA_SHA").read_text().strip(),
        "image_id": img.get("image_id"),
        "flatten_deterministic": img.get("flatten_deterministic"),
        "fit_tree": fit_tree.read_text().strip() if fit_tree.exists() else None,
    }


def gates(arms: dict[str, dict]) -> list[str]:
    """Return the list of failed gates (empty = valid)."""
    fails = []
    missing = [a for a in BASELINE + UPSTREAM if a not in arms]
    if missing:
        raise ValueError(f"partial sample refused: missing {missing}")
    for a, r in arms.items():
        if r["villa_sha"] != RENDER_TREE:
            fails.append(f"{a}: render tree {r['villa_sha']} != {RENDER_TREE}")
        if r["flatten_deterministic"] != "1":
            fails.append(f"{a}: flatten not deterministic")
    ids = {r["image_id"] for r in arms.values()}
    if len(ids) != 1:
        fails.append(f"render images differ across arms: {sorted(map(str, ids))}")
    for a in UPSTREAM:
        if not (arms[a]["fit_tree"] or "").startswith(UPSTREAM_TREE):
            fails.append(f"{a}: FIT_TREE {arms[a]['fit_tree']} is not {UPSTREAM_TREE}")
    return fails


def verdict(base: list[float], up: list[float]) -> tuple[str, dict]:
    ci = relative_ci(base, up)
    if ci is None:
        return "INVALID", {"reason": "no variance; no interval can be formed"}
    if ci["lo"] > 0:
        return "FITTER CHANGED READING (+)", ci
    if ci["hi"] < 0:
        return "FITTER CHANGED READING (-)", ci
    return "NO DETECTED CHANGE", ci


def cv(xs: list[float]) -> float:
    return st.stdev(xs) / st.mean(xs)


def decide(arms: dict[str, dict]) -> dict:
    fails = gates(arms)
    if fails:
        return {"verdict": "INVALID", "failed_gates": fails}
    base = [arms[a]["ink"] for a in BASELINE]
    up = [arms[a]["ink"] for a in UPSTREAM]
    head, ci = verdict(base, up)
    return {
        "verdict": head,
        "relative_ci": ci,
        "baseline_mean": st.mean(base),
        "upstream_mean": st.mean(up),
        "baseline_cv": cv(base),
        "upstream_cv_df2": cv(up),  # descriptive only: df 2 cannot carry a claim
        "per_arm": {a: arms[a]["ink"] for a in BASELINE + UPSTREAM},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spiral-out", type=Path, default=SPIRAL_OUT)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    arms = {a: read_arm(args.spiral_out / a) for a in BASELINE + UPSTREAM}
    res = decide(arms)
    # descriptive: villa's own geometry score for the upstream fits
    sat = {}
    for a, tag in UPSTREAM_FIT_TAG.items():
        hits = sorted(
            args.spiral_out.glob(f"*-patch_{tag}/satisfaction_metrics_fitted.json")
        )
        if hits:
            sat[a] = json.loads(hits[-1].read_text())["summary"][
                "satisfied_area_fraction"
            ]
    res["upstream_satisfied_area_fraction"] = sat
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(res["verdict"])
    if "relative_ci" in res:
        c = res["relative_ci"]
        print(
            f"  {c['rel']:+.2%}  95% CI [{c['lo']:+.2%}, {c['hi']:+.2%}]  Welch df {c['df']:.1f}"
        )
    for f in res.get("failed_gates", []):
        print("  GATE FAILED:", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
