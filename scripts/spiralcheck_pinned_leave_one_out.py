"""Descriptive (unregistered): leave-one-fit-out range of the pinned-tier Q3 r values.

Run from the repo root after the registered analysis. See
`reports/spiralcheck_null_replicates_on_pinned.md`.
"""

import json
import sys

sys.path.insert(0, "scripts")
from analyse_spiralcheck_pinned_replication import ARMS  # noqa: E402
from analyse_spiralcheck_validation import METRICS, within_config_r  # noqa: E402

rows = json.load(open("reports/spiralcheck_pinned/collected.json"))["fits"]
tags = sorted(rows)
out = {}
for m in METRICS:
    rs = []
    for drop in tags:
        t2 = [t for t in tags if t != drop]
        c = within_config_r(
            [rows[t]["scored"][m] for t in t2],
            [rows[t]["total_fg_pixels"] for t in t2],
            [ARMS[t] for t in t2],
        )
        rs.append((round(c["r"], 3), round(c["p"], 4), drop))
    lo, hi = min(rs), max(rs)
    out[m] = {"loo_r_min": lo, "loo_r_max": hi}
    print(m, "leave-one-fit-out r range", lo, hi)
json.dump(out, open("reports/spiralcheck_pinned/leave_one_out.json", "w"), indent=2)
