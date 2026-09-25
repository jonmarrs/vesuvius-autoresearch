"""Descriptive (unregistered) checks for the spiralcheck validation.

Q3 with the ink outlier `curbase_s6` dropped, per-metric seed CVs, and the scored-scope
separation with s6 dropped. Run from the repo root.
"""

import json
import sys

sys.path.insert(0, "scripts")
from analyse_spiralcheck_validation import (  # noqa: E402
    ARMS,
    METRICS,
    oneway,
    within_config_r,
)

c = json.load(open("reports/spiralcheck_validation/collected.json"))["fits"]
out = {}
for drop in (None, "curbase_s6"):
    tags = sorted(t for t in c if t != drop)
    g = [ARMS[t][0] for t in tags]
    ink = [c[t]["total_fg_pixels"] for t in tags]
    for m in METRICS:
        r = within_config_r([c[t]["scored"][m] for t in tags], ink, g)
        out[f"q3 drop={drop} {m}"] = (round(r["r"], 3), round(r["p"], 4), r["df"])
tags = sorted(c)
g = [ARMS[t][0] for t in tags]
for scope in ("all", "scored"):
    for m in METRICS:
        a = oneway([c[t][scope][m] for t in tags], g)
        out[f"cv {scope} {m}"] = round(a["pooled_within_sd"] / a["grand_mean"], 4)
# post-hoc: scored-scope separation with curbase_s6 dropped, and anchor vs rest only
for m in ("median_pitch", "inflated_bin_fraction"):
    t2 = [t for t in tags if t != "curbase_s6"]
    a = oneway([c[t]["scored"][m] for t in t2], [ARMS[t][0] for t in t2])
    out[f"q1s drop s6 {m}"] = (round(a["F"], 2), round(a["p"], 5))
    vals = [c[t]["scored"][m] for t in tags]
    out[f"per-fit scored {m}"] = {
        t: round(v, 4) for t, v in zip(tags, vals, strict=False)
    }
for k, v in out.items():
    print(k, v)
with open("reports/spiralcheck_validation/descriptive.json", "w") as fh:
    fh.write(json.dumps(out, indent=2) + "\n")
