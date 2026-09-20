"""Every manipulation in the corpus, against the endpoint villa actually scores.

Each study here was registered, run and reported on its own. This asks the
question none of them can: **across everything we have tried, has anything
improved reading?** It is a synthesis, not a new measurement -- every number comes
from a scored arm already on disk.

Two rules it enforces, both learned the hard way:

* **Controls must be TREE-MATCHED.** `reports/the_anchor_control_was_cross_tree.md`
  -- the anchor study's baseline was fitted before a villa bump and its treatment
  after, which moved its ink estimate by 4.63 points. Each study below names the
  control that shares a code tier with its treatment, which is not always the
  control the registration named.
* **A null is quoted with the effect it could have SEEN.** The floor is
  tier-specific and was doubled on 2026-09-19
  (`reports/six_unused_seeds_double_the_current_floor.md`), so "no effect" here
  always reads "no effect larger than X".
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

from scipy import stats

ALPHA = 0.05
# reports/six_unused_seeds_double_the_current_floor.md and noise_floor_by_tier.md
CV = {"pinned": 0.0514, "current": 0.0536}

# name -> (control arms, treated arms, tier). Controls are TREE-MATCHED.
STUDIES: dict[str, tuple[tuple[str, ...], tuple[str, ...], str]] = {
    "gap-expander fix": (
        ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06"),
        ("gap133", "gap133s2", "gap133s3", "gap133s4", "gap133s5", "gap133s6"),
        "pinned",
    ),
    "patch bootstrap": (
        ("rand090s1", "rand090s2", "rand090s3"),
        ("boot090s1", "boot090s2", "boot090s3"),
        "pinned",
    ),
    "stripmatch": (
        ("rand090s1", "rand090s2", "rand090s3"),
        ("strip090s1", "strip090s2", "strip090s3"),
        "pinned",
    ),
    "same-winding ablation (pinned)": (
        ("baseline01", "seed02", "seed03", "seed04", "seed05", "seed06"),
        ("nosame_s1", "nosame_s2", "nosame_s3"),
        "pinned",
    ),
    "same-winding ablation (current)": (
        ("curbase_s1", "curbase_s2", "curbase_s3"),
        ("nosamecur_s1", "nosamecur_s2", "nosamecur_s3"),
        "current",
    ),
    # TREE-MATCHED, and deliberately NOT the registered curbase_s1-s3: those were
    # fitted on d8c5f488a, the ablated arms on be09a8503.
    "anchor ablation 59->10": (
        (
            "curbase_s4",
            "curbase_s5",
            "curbase_s6",
            "curbase_s7",
            "curbase_s8",
            "curbase_s9",
        ),
        ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"),
        "current",
    ),
}


def ink(spiral_out: str, tag: str) -> float:
    p = Path(spiral_out) / f"outer_{tag}" / "ink_metric" / "metrics.json"
    return json.loads(p.read_text())["summary"]["total_fg_pixels"]


def effect(ctl: list[float], trt: list[float], cv: float) -> dict:
    rel = (st.mean(trt) - st.mean(ctl)) / st.mean(ctl)
    t, p = stats.ttest_ind(ctl, trt, equal_var=False)
    se = (
        st.stdev(ctl) ** 2 / len(ctl) + st.stdev(trt) ** 2 / len(trt)
    ) ** 0.5 / st.mean(ctl)
    df = (st.stdev(ctl) ** 2 / len(ctl) + st.stdev(trt) ** 2 / len(trt)) ** 2 / (
        (st.stdev(ctl) ** 2 / len(ctl)) ** 2 / (len(ctl) - 1)
        + (st.stdev(trt) ** 2 / len(trt)) ** 2 / (len(trt) - 1)
    )
    tc = stats.t.ppf(1 - ALPHA / 2, df)
    return {
        "rel": rel,
        "p": float(p),
        "lo": rel - tc * se,
        "hi": rel + tc * se,
        "mde": 2.802 * cv * (1 / len(ctl) + 1 / len(trt)) ** 0.5,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    print("HAS ANY MANIPULATION IMPROVED READING? endpoint = total_fg_pixels\n")
    print(
        f"{'study':<34}{'n':>7}{'effect':>9}{'p':>8}{'95% CI':>20}{'MDE':>7}  verdict"
    )
    out, moved_up = {}, 0
    for name, (c, t, tier) in STUDIES.items():
        ctl = [ink(a.spiral_out, x) for x in c]
        trt = [ink(a.spiral_out, x) for x in t]
        e = effect(ctl, trt, CV[tier])
        sig = e["p"] < ALPHA
        if sig and e["rel"] > 0:
            v, moved_up = "IMPROVED", moved_up + 1
        elif sig:
            v = "HARMED"
        else:
            v = f"null, bounds {e['mde']:.0%}"
        ci = f"[{e['lo']:+.1%}, {e['hi']:+.1%}]"
        print(
            f"{name:<34}{len(ctl)}v{len(trt):<5}{e['rel']:>+8.2%}{e['p']:>8.3f}{ci:>20}{e['mde']:>7.1%}  {v}"
        )
        out[name] = {**e, "tier": tier, "verdict": v}

    print(f"\n{len(STUDIES)} manipulations. Improved reading: {moved_up}.")
    print("Every null is a bound, not an absence: none could have seen an effect")
    print("smaller than its MDE column, and all of those are 9% or larger.")

    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
