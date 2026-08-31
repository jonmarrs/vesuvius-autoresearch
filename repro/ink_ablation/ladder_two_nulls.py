"""Two nulls, two different questions. I conflated them.

Q1 "is each member's AUC a real reading?"  -> ROLL null (misalign the reference).
   This is the right null for reading. Already run: it3/it0/it4/it5 p<0.0025.

Q2 "does reading ability track training-tile count?" -> LABEL-PERMUTATION null
   (hold the six observed AUCs fixed, permute which member has which tile count).
   All 720 permutations, exact.

The roll null is the WRONG null for Q2: it collapses every member to ~0.50, so it
asks whether an ordering appears among six noise values -- and with six mutually
correlated maps it does, 6-13% of the time. That is a real warning about rank-only
statistics, but it is not evidence the observed ordering is artefactual, because
under the roll the AUC spread is ~0.03 against an observed ~0.26.
"""

import json
from itertools import permutations

import numpy as np

KS = ["it1", "it2", "it3", "it0", "it4", "it5"]
T = np.array([3396, 8970, 15286, 20075, 24773, 33061], float)
RUNS = {
    "seg A 20231210121321 vs human GT, full 4096^2": [
        0.5064,
        0.5317,
        0.6865,
        0.7184,
        0.7265,
        0.7276,
    ],
    "seg A 20231210121321 vs human GT, centre 2048^2": [
        0.5082,
        0.5510,
        0.7165,
        0.7486,
        0.7704,
        0.7689,
    ],
    "seg B 20231012184424 vs canon, 4096^2": [
        0.4609,
        0.4589,
        0.5971,
        0.6473,
        0.6524,
        0.7141,
    ],
}
lt = np.log10(T)
tr = np.argsort(np.argsort(T)).astype(float)
PERMS = list(permutations(range(6)))

for name, vals in RUNS.items():
    a = np.asarray(vals, dtype=float)
    rho = np.corrcoef(tr, np.argsort(np.argsort(a)).astype(float))[0, 1]
    slope = np.polyfit(lt, a, 1)[0]
    # exact: permute the tile labels across members, AUCs fixed
    rr = np.array(
        [
            np.corrcoef(tr, np.argsort(np.argsort(a[list(p)])).astype(float))[0, 1]
            for p in PERMS
        ]
    )
    ss = np.array([np.polyfit(lt, a[list(p)], 1)[0] for p in PERMS])
    print(f"\n{name}")
    print(f"  spread max-min      {a.max() - a.min():.4f}")
    print(
        f"  ladder rho          {rho:+.4f}   exact label-perm p = {(rr >= rho - 1e-12).mean():.4f}  ({int((rr >= rho - 1e-12).sum())}/720)"
    )
    print(
        f"  slope per decade    {slope:+.4f}   exact label-perm p = {(ss >= slope - 1e-12).mean():.4f}  ({int((ss >= slope - 1e-12).sum())}/720)"
    )

print("""
Reading the two together:
  the ROLL null says each of it3/it0/it4/it5 reads held-out ink, on both segments;
  the LABEL-PERMUTATION null says the ordering tracks tile count;
  the roll null applied to the ORDERING says a rank-only statistic on n=6
  correlated models is weak evidence on its own (p 0.06-0.13).
So the dose-response stands on the MAGNITUDES, not on the rank pattern, and the
between-segment rank agreement I led with (rho 0.943) is the weakest of the three.""")
