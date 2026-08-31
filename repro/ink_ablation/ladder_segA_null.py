"""Apply the SAME roll-null to segment A, the claim that is actually in the report.

reports/ink_ablation_transfer_result.md asserts "the ladder is monotone in
pseudo-label density" from segment A against registered human GT, hedged only in
prose. On segment B that same ordering statistic failed its null at p=0.0625. If
it fails here too, the report needs a correction rather than an addendum.

Same null: roll the GT on a torus by large offsets. Structure preserved,
correspondence destroyed, 400 draws.
"""

import json

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

P = dict(np.load("preds_L0.npz"))
gt = np.array(
    Image.open(
        "/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt/"
        "data/scroll1_20231210121321/gt_ink.png"
    ).convert("L")
)
print(
    f"preds {P['it5'].shape}   gt {gt.shape}   gt ink fraction {(gt > 127).mean():.4f}"
)
KS = ["it1", "it2", "it3", "it0", "it4", "it5"]
T = {"it1": 3396, "it2": 8970, "it3": 15286, "it0": 20075, "it4": 24773, "it5": 33061}
tiles_rank = np.argsort(np.argsort([T[k] for k in KS])).astype(float)


def auc_from_rank(r, y):
    n1 = int(y.sum())
    n0 = y.size - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def ranks(v):
    r = np.empty(v.size, np.float64)
    r[np.argsort(v, kind="mergesort")] = np.arange(1, v.size + 1)
    return r


def ladder_rho(sc):
    return float(
        np.corrcoef(
            tiles_rank, np.argsort(np.argsort([sc[k] for k in KS])).astype(float)
        )[0, 1]
    )


# which crop reproduces the reported table? the report says 2048^2, same frame, no shift
for tag, sl in [
    ("full 4096^2", (slice(None), slice(None))),
    ("centre 2048^2", (slice(1024, 3072), slice(1024, 3072))),
]:
    g = (gt[sl] > 127).ravel()
    sc = {k: auc_from_rank(ranks(P[k][sl].ravel()), g) for k in KS}
    print(
        f"  {tag:<15} "
        + "  ".join(f"{k} {sc[k]:.4f}" for k in KS)
        + f"   rho {ladder_rho(sc):+.4f}"
    )

SL = (slice(1024, 3072), slice(1024, 3072))
M = 2048
pred_rank = {k: ranks(P[k][SL].ravel()) for k in KS}
w = gt[SL]
obs = {k: auc_from_rank(pred_rank[k], (w > 127).ravel()) for k in KS}
obs_rho = ladder_rho(obs)
print(f"\nscoring centre 2048^2;  observed rho {obs_rho:+.4f}", flush=True)

rng = np.random.default_rng(20260830)
rhos, aucs = [], {k: [] for k in KS}
while len(rhos) < 400:
    dy, dx = rng.integers(-M // 2, M // 2, 2)
    if abs(dy) < 160 and abs(dx) < 160:
        continue
    yb = (np.roll(w, (int(dy), int(dx)), (0, 1)) > 127).ravel()
    sc = {k: auc_from_rank(pred_rank[k], yb) for k in KS}
    rhos.append(ladder_rho(sc))
    for k in KS:
        aucs[k].append(sc[k])
rhos = np.array(rhos)

print(
    f"\nnull ladder rho over 400 rolls: mean {rhos.mean():+.4f}  sd {rhos.std():.4f}  "
    f"p95 {np.quantile(rhos, 0.95):+.4f}  max {rhos.max():+.4f}"
)
print(f"P(null rho >= observed) = {(rhos >= obs_rho).mean():.4f}\n")
print(
    f"{'member':<7}{'tiles':>8}{'observed':>10}{'null mean':>11}{'null p95':>10}{'null max':>10}{'p':>8}"
)
res = {
    "observed": obs,
    "observed_rho": obs_rho,
    "p_rho": float((rhos >= obs_rho).mean()),
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
        f"{k:<7}{T[k]:>8}{obs[k]:>10.4f}{v.mean():>11.4f}{np.quantile(v, 0.95):>10.4f}{v.max():>10.4f}{p:>8.4f}"
    )
json.dump(res, open("ladder_segA_null.json", "w"), indent=2)
