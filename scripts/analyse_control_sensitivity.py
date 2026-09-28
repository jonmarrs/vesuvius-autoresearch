"""How much do the two current-tier ablation verdicts depend on which baseline seeds they use?

Written 2026-09-27 after the second inkdelta validation (`reports/inkdelta_registered_intervals.md`)
exposed that the survey (`scripts/survey_manipulation_effects.py`) swapped the anchor study's control
to `curbase_s4-s9` as "tree-matched" but left the same-winding study on `curbase_s1-s3`, although both
treated arms were rendered on the same code. Post-hoc: nothing here was registered, and it is
reported as sensitivity, not as a verdict.

The nine `curbase_s*` are one configuration differing only by seed. All nine were FITTED from one
unchanged copy of villa `d8c5f488a` (`villa-spiral-current`). They were RENDERED on two codes:
s1-s3 before the 2026-09-11 submodule bump, s4-s9 after it, as were every treated arm below.
`reports/rerender_test_verdict.md` measured that render change as inert (+1.44%, inside a 3.04%
same-code render noise).
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
from inkdelta.compare import compare  # noqa: E402
from inkdelta.runs import load_run  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
CONTROLS = {
    "registered s1-s3 (old render)": [f"curbase_s{i}" for i in (1, 2, 3)],
    "render-matched s4-s9": [f"curbase_s{i}" for i in range(4, 10)],
    "all nine s1-s9": [f"curbase_s{i}" for i in range(1, 10)],
}
TREATED = {
    "same-winding ablation (current)": ["nosamecur_s1", "nosamecur_s2", "nosamecur_s3"],
    "anchor ablation 59->10": ["anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"],
}


def runs(tags):
    return [load_run(SO / f"outer_{t}", None) for t in tags]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="reports/control_sensitivity.json")
    a = ap.parse_args()
    out = {"control_cv": {}, "effects": {}}
    for name, tags in CONTROLS.items():
        fg = [r.total_fg_pixels for r in runs(tags)]
        out["control_cv"][name] = st.stdev(fg) / st.mean(fg)
        print(f"{name:32} n={len(fg)} CV {out['control_cv'][name]:.4f}")
    print()
    for study, t_tags in TREATED.items():
        out["effects"][study] = {}
        for cname, c_tags in CONTROLS.items():
            r = compare(runs(c_tags), runs(t_tags), build_a="edge", build_b="edge")
            iv = r.interval
            out["effects"][study][cname] = {"verdict": r.verdict, **{k: iv[k] for k in ("rel", "lo", "hi", "df")}}
            print(f"{study:34}{cname:32}{iv['rel']:+7.2%} [{iv['lo']:+.2%}, {iv['hi']:+.2%}] "
                  f"df={iv['df']:.2f}  {r.verdict}")  # fmt: skip
    Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
