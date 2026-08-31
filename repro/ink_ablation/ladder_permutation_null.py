"""Proper null distribution, because 5 hand-picked controls cannot supply one.

The previous control used 4 misalignments + 1 other-segment map. One of them
(flipLR) returned ladder rho +0.7714 against the true reference's +0.9429. With
n=6 members the sampling SD of Spearman rho is 1/sqrt(5) = 0.447, so those two
numbers are ~0.4 SD apart: the hand-picked controls cannot separate them.

So build the null properly. Roll the canon window on a torus by large random
offsets: texture statistics preserved exactly, correspondence destroyed. 400
draws gives an empirical distribution for BOTH statistics -- the ladder rho and
each member's AUC -- and turns 'the control looks clean' into a p-value.
"""

import json

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SEG, N = "20231012184424", 4096
M, MIN_SHIFT, NDRAW = N // 8, 40, 400
P = dict(np.load("preds_segB.npz"))
KS = ["it1", "it2", "it3", "it0", "it4", "it5"]
T = {"it1": 3396, "it2": 8970, "it3": 15286, "it0": 20075, "it4": 24773, "it5": 33061}
c = np.array(Image.open(f"canon_{SEG}.jpg").convert("L")).astype(np.float32) / 255.0
# window origin: level-0 centre of the segment used in ladder_second_segment.py
Y0, X0 = 50800 // 2, 75720 // 2
w = c[Y0 // 8 : Y0 // 8 + M, X0 // 8 : X0 // 8 + M]

pred_rank = {}
for k in KS:  # rank once; AUC is rank-based so this is exact
    v = P[k].ravel()
    r = np.empty(v.size, np.float64)
    r[np.argsort(v, kind="mergesort")] = np.arange(1, v.size + 1)
    pred_rank[k] = r
tiles_rank = np.argsort(np.argsort([T[k] for k in KS])).astype(float)


def auc_from_rank(r, y):
    n1 = int(y.sum())
    n0 = y.size - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def ladder_rho(sc):
    y = np.argsort(np.argsort([sc[k] for k in KS])).astype(float)
    return float(np.corrcoef(tiles_rank, y)[0, 1])


obs = {k: auc_from_rank(pred_rank[k], (w > 0.5).ravel()) for k in KS}
obs_rho = ladder_rho(obs)
print(
    f"observed   rho {obs_rho:+.4f}   " + "  ".join(f"{k} {obs[k]:.4f}" for k in KS),
    flush=True,
)

rng = np.random.default_rng(20260830)
rhos, aucs = [], {k: [] for k in KS}
while len(rhos) < NDRAW:
    dy, dx = rng.integers(-M // 2, M // 2, 2)
    if abs(dy) < MIN_SHIFT and abs(dx) < MIN_SHIFT:
        continue
    yb = (np.roll(w, (int(dy), int(dx)), (0, 1)) > 0.5).ravel()
    sc = {k: auc_from_rank(pred_rank[k], yb) for k in KS}
    rhos.append(ladder_rho(sc))
    for k in KS:
        aucs[k].append(sc[k])
rhos = np.array(rhos)

print(
    f"\nnull ladder rho over {NDRAW} rolls: mean {rhos.mean():+.4f}  sd {rhos.std():.4f}"
    f"  p95 {np.quantile(rhos, 0.95):+.4f}  max {rhos.max():+.4f}"
)
print(
    f"P(null rho >= observed {obs_rho:+.4f}) = {(rhos >= obs_rho).mean():.4f}   "
    f"P(null |rho| >= |observed|) = {(np.abs(rhos) >= abs(obs_rho)).mean():.4f}"
)
print(
    f"\nfor reference, the hand-picked controls: flipLR +0.7714 sits at "
    f"percentile {(rhos < 0.7714).mean() * 100:.1f} of this null\n"
)
print(
    f"{'member':<7}{'observed':>10}{'null mean':>11}{'null p95':>10}{'null max':>10}{'p':>8}"
)
res = {
    "observed_auc": obs,
    "observed_rho": obs_rho,
    "null_rho": rhos.tolist(),
    "per_member": {},
}
for k in KS:
    v = np.array(aucs[k])
    p = float((v >= obs[k]).mean())
    res["per_member"][k] = {
        "observed": obs[k],
        "null_mean": float(v.mean()),
        "null_p95": float(np.quantile(v, 0.95)),
        "null_max": float(v.max()),
        "p": p,
    }
    print(
        f"{k:<7}{obs[k]:>10.4f}{v.mean():>11.4f}{np.quantile(v, 0.95):>10.4f}{v.max():>10.4f}{p:>8.4f}"
    )
json.dump(res, open("ladder_permutation_null.json", "w"), indent=2)
