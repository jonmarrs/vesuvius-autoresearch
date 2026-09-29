"""POST-HOC falsification test, 2026-09-29: is the fit seed a shared nuisance ACROSS configs?

Prompted by the same-winding extension (r = 0.916 between same-seed ink with and without the
constraints). Tested here on data that played no part in noticing it, using only arms whose
optimizer_random_seed is verified from their fit script:

* pinned tier (villa-spiral 6847063f): nosame / boot090 / rand090 / strip090 x seeds 1-3;
* current tier: curbase / nosamecur / anchor10cov x seeds 1-3 (includes the noticing data,
  reported separately).

Two-way layout on log(total_fg_pixels), config x seed, no replication: F_seed = MS_seed / MS_resid.
If the seed carries across configs, F_seed is large.
"""

import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, "/home/jon/openclaw-workspace/Neo-VM/projects/inkdelta/src")
from inkdelta.stats import betainc  # noqa: E402

SO = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
LAYOUTS = {
    "pinned (independent of the noticing data)": {
        "nosame": ["nosame_s1", "nosame_s2", "nosame_s3"],
        "boot090": ["boot090s1", "boot090s2", "boot090s3"],
        "rand090": ["rand090s1", "rand090s2", "rand090s3"],
        "strip090": ["strip090s1", "strip090s2", "strip090s3"],
    },
    "current, seeds 1-3 (anchor10cov is new to this question)": {
        "curbase": ["curbase_s1", "curbase_s2", "curbase_s3"],
        "nosamecur": ["nosamecur_s1", "nosamecur_s2", "nosamecur_s3"],
        "anchor10cov": ["anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"],
    },
}


def ink(tag):
    return json.loads(
        (SO / f"outer_{tag}" / "ink_metric" / "metrics.json").read_text()
    )["summary"]["total_fg_pixels"]


def f_sf(f, d1, d2):
    """P(F > f) for F(d1, d2)."""
    return betainc(d2 / 2, d1 / 2, d2 / (d2 + d1 * f))


out = {}
for name, lay in LAYOUTS.items():
    y = {c: [math.log(ink(t)) for t in tags] for c, tags in lay.items()}
    C, S = len(y), 3
    grand = st.mean(v for vs in y.values() for v in vs)
    cm = {c: st.mean(vs) for c, vs in y.items()}
    sm = [st.mean(y[c][s] for c in y) for s in range(S)]
    ss_seed = C * sum((m - grand) ** 2 for m in sm)
    ss_res = sum((y[c][s] - cm[c] - sm[s] + grand) ** 2 for c in y for s in range(S))
    df_s, df_r = S - 1, (C - 1) * (S - 1)
    F = (ss_seed / df_s) / (ss_res / df_r)
    p = f_sf(F, df_s, df_r)
    out[name] = {"F_seed": F, "df": [df_s, df_r], "p": p,
                 "seed_effects_pct": [100 * (m - grand) for m in sm]}  # fmt: skip
    print(f"{name}: F_seed({df_s},{df_r}) = {F:.2f}, p = {p:.3f}; seed effects "
          + ", ".join(f"s{s + 1} {100 * (m - grand):+.1f}%" for s, m in enumerate(sm)))  # fmt: skip
Path("reports/seed_as_shared_nuisance.json").write_text(
    json.dumps(out, indent=1) + "\n"
)
