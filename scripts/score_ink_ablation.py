"""Score the ablation series against registered ground truth, under frozen rules.

Implements `docs/preregistration/2026-08-30_ink_absence_vs_unrecovered.md` and its
two addenda. Written before the predictions existed, so the analysis cannot be
shaped by them.

THE QUESTION. Among pixels the models call negative, does DISAGREEMENT across a
series that differs only in pseudo-label density separate "no ink" from "no ink
recovered yet"? That is villa's own open problem, and without an answer there is
no way to know when a scroll is finished as opposed to unread.

WHAT THE RULES FORCE, and each costs something:

  * rule 2: AUC of p_std discriminating false from true negatives, verdict at
    0.65 / 0.55;
  * rule 3: p_std must beat p_mean. **If it does not, the ablation series adds
    nothing over a single model, and that is the headline whatever the absolute
    AUC is.** Floors are p_mean, p_max, and permuted p_std over 5 seeds;
  * rule 1: fewer than 1,000 pixels in either group is UNPOWERED, reported as
    counts rather than as a ratio;
  * addendum 1: three alignments. Primary is the target's recorded peak shift
    [31,-8] level-2 px; secondary unshifted; and a WRONG-DIRECTION control
    [-31,8]. If primary and secondary disagree on the verdict there is NO
    verdict, and if primary does not beat the wrong-direction arm the study is
    void, because the signal then does not depend on the labels being in the
    right place;
  * addendum 2: p_std is reported over all six AND over it1..it5, the pure
    density ladder, because it0 differs in training DATA rather than density.
    slope is it1..it5 only.
"""

import argparse
import json

import numpy as np


def auc(score, y):
    y = y.astype(bool)
    n1 = int(y.sum())
    n0 = y.size - n1
    if n1 < 1 or n0 < 1:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    r = np.empty(score.size, np.float64)
    r[order] = np.arange(1, score.size + 1)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()

    from PIL import Image

    P = np.load(args.preds)
    members = sorted(P.files)
    stack = np.stack([P[k] for k in members])  # (6, N, N)
    ladder = np.stack([P[k] for k in members if k != "it0"])
    n = stack.shape[-1]
    gt_full = np.array(Image.open(args.gt)) > 0
    if gt_full.shape[0] != n:  # GT is level-2 px; preds match it natively
        f = gt_full.shape[0] // n
        gt_full = gt_full.reshape(n, f, n, f).mean(axis=(1, 3)) > 0.5

    p_mean, p_max = stack.mean(0), stack.max(0)
    p_std_all, p_std_ladder = stack.std(0), ladder.std(0)
    idx = np.arange(ladder.shape[0], dtype=np.float64)
    idx -= idx.mean()
    slope = (ladder * idx[:, None, None]).sum(0) / (idx**2).sum()

    # level-2 px shifts; predictions sit at the GT's own resolution
    arms = {
        "primary [31,-8]": (31, -8),
        "unshifted [0,0]": (0, 0),
        "wrong-dir [-31,8]": (-31, 8),
    }
    results = {}
    for name, (dy, dx) in arms.items():
        gt = np.roll(np.roll(gt_full, dy, axis=0), dx, axis=1)
        neg = p_mean.ravel() < 0.5  # threshold fixed in advance
        y_fn = gt.ravel() & neg  # GT ink, model says no: FALSE negative
        y_tn = ~gt.ravel() & neg  # GT no ink, model says no: TRUE negative
        n_fn, n_tn = int(y_fn.sum()), int(y_tn.sum())
        sel = y_fn | y_tn
        lab = y_fn[sel]
        row = {
            "n_false_neg": n_fn,
            "n_true_neg": n_tn,
            "powered": bool(n_fn >= 1000 and n_tn >= 1000),
        }
        if row["powered"]:
            row["auc_p_std_all"] = auc(p_std_all.ravel()[sel], lab)
            row["auc_p_std_ladder"] = auc(p_std_ladder.ravel()[sel], lab)
            row["floor_p_mean"] = auc(p_mean.ravel()[sel], lab)
            row["floor_p_max"] = auc(p_max.ravel()[sel], lab)
            row["slope_ladder"] = auc(np.abs(slope).ravel()[sel], lab)
            rng = np.random.default_rng(20260830)
            perm = [
                auc(rng.permutation(p_std_all.ravel()[sel]), lab)
                for _ in range(args.seeds)
            ]
            row["floor_permuted"] = float(np.mean(perm))
        results[name] = row

    for name, r in results.items():
        print(f"\n=== {name} ===")
        print(
            f"  false negatives {r['n_false_neg']}   true negatives {r['n_true_neg']}"
            f"   powered: {r['powered']}"
        )
        if not r["powered"]:
            print("  UNPOWERED by rule 1; no ratio reported.")
            continue
        print(f"  AUC p_std (all six)      {r['auc_p_std_all']:.4f}")
        print(f"  AUC p_std (ladder 1..5)  {r['auc_p_std_ladder']:.4f}")
        print(
            f"  floor p_mean             {r['floor_p_mean']:.4f}   <- rule 3: p_std must beat this"
        )
        print(f"  floor p_max              {r['floor_p_max']:.4f}")
        print(f"  floor permuted           {r['floor_permuted']:.4f}")
        print(f"  |slope| (reported only)  {r['slope_ladder']:.4f}")

    pri, sec, wrong = (
        results["primary [31,-8]"],
        results["unshifted [0,0]"],
        results["wrong-dir [-31,8]"],
    )
    print("\n=== VERDICT ===")
    if not pri.get("powered"):
        print("UNPOWERED. No verdict.")
    else:
        beats_floor = pri["auc_p_std_all"] > pri["floor_p_mean"]
        if wrong.get("powered") and pri["auc_p_std_all"] <= wrong["auc_p_std_all"]:
            print(
                "VOID: the primary alignment does not beat the WRONG-DIRECTION control, so the"
            )
            print("signal does not depend on the labels being in the right place.")
        elif not beats_floor:
            print(
                f"p_std {pri['auc_p_std_all']:.4f} does NOT beat p_mean {pri['floor_p_mean']:.4f}."
            )
            print(
                "By rule 3 the ablation series adds nothing over a single model. That is the"
            )
            print("headline regardless of the absolute AUC.")
        else:
            v = (
                "carries a usable signal"
                if pri["auc_p_std_all"] >= 0.65
                else "does not"
                if pri["auc_p_std_all"] <= 0.55
                else "is inconclusive"
            )
            agree = (pri["auc_p_std_all"] >= 0.65) == (
                sec.get("auc_p_std_all", 0) >= 0.65
            )
            print(
                f"p_std {pri['auc_p_std_all']:.4f} beats p_mean {pri['floor_p_mean']:.4f}; series {v}."
            )
            if not agree:
                print(
                    "Primary and secondary alignments DISAGREE on the verdict: no verdict (addendum 1)."
                )
    if args.out:
        json.dump(results, open(args.out, "w"), indent=2)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
