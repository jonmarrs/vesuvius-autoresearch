"""POST-HOC companions to the registered same-winding extension verdict. Written 2026-09-29 AFTER the
verdict (reports/samewinding_extension_verdict.json) was read. Nothing here changes it.

1. Sensitivity to the 09-28 gate amendment (+/-5% -> +/-10%): which arms the original gate would have
   failed, and the primary comparison without them.
2. Seed pairing: nosamecur_sK and curbase_sK share optimizer_random_seed. If the seed is a shared
   nuisance across the two datasets, a paired comparison is much tighter than the registered one.
   Noticed in the data, so it is a LEAD for a future registered design, not a result.
"""

import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
from inkdelta.stats import t_ppf, welch_relative  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")


def m(tag):
    return json.loads(
        (SO / f"outer_{tag}" / "ink_metric" / "metrics.json").read_text()
    )["summary"]


abl = {k: m(f"nosamecur_s{k}") for k in range(1, 7)}
ctl = {k: m(f"curbase_s{k}") for k in range(1, 10)}
ctl_area = st.mean(ctl[k]["total_pixels"] for k in range(4, 10))
out = {"gate_original_5pct": {}, "paired": {}}

for k in (4, 5, 6):
    dev = abl[k]["total_pixels"] / ctl_area - 1
    out["gate_original_5pct"][f"nosamecur_s{k}"] = {
        "area_dev": dev,
        "fails_5pct": abs(dev) > 0.05,
    }
kept = [
    k
    for k in range(1, 7)
    if not (k >= 4 and out["gate_original_5pct"][f"nosamecur_s{k}"]["fails_5pct"])
]
w = welch_relative(
    [ctl[k]["total_fg_pixels"] for k in range(4, 10)],
    [abl[k]["total_fg_pixels"] for k in kept],
)
out["primary_without_5pct_failures"] = {"ablated_seeds": kept, **w}

pairs = list(range(1, 7))
ca = [ctl[k]["total_fg_pixels"] for k in pairs]
aa = [abl[k]["total_fg_pixels"] for k in pairs]
d = [a / c - 1 for a, c in zip(aa, ca, strict=False)]
mean, sd = st.mean(d), st.stdev(d)
half = t_ppf(0.975, len(d) - 1) * sd / len(d) ** 0.5
r = st.correlation(ca, aa)
out["paired"] = {"seeds": pairs, "per_seed_rel": d, "mean": mean, "lo": mean - half, "hi": mean + half,
                 "df": len(d) - 1, "r_ink_across_datasets": r,
                 "note": "s1-s3 controls were rendered on d8c5f488a, the rest on be09a8503 (measured inert)"}  # fmt: skip

for k, v in out["gate_original_5pct"].items():
    print(
        f"{k}: strip area {v['area_dev']:+.2%} vs control mean -> original 5% gate {'FAIL' if v['fails_5pct'] else 'pass'}"
    )
p = out["primary_without_5pct_failures"]
print(
    f"primary without those arms (seeds {p['ablated_seeds']}): {p['rel']:+.2%} [{p['lo']:+.2%}, {p['hi']:+.2%}]"
)
q = out["paired"]
print(
    "paired per-seed:",
    ", ".join(f"s{k} {x:+.2%}" for k, x in zip(pairs, d, strict=False)),
)
print(
    f"paired mean {q['mean']:+.2%} [{q['lo']:+.2%}, {q['hi']:+.2%}] df {q['df']}; r(ink, same seed) = {r:.3f}"
)
Path("reports/samewinding_extension_posthoc.json").write_text(
    json.dumps(out, indent=1) + "\n"
)
