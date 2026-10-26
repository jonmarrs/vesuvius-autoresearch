"""What would a promotion rule over replicates have done on the loop's cycles since the 2026-10-17 promotion?

The loop promotes a cycle only when its val_f1 beats the stored incumbent by F1_NOISE_TOLERANCE (0.01). Since
2026-10-17 no cycle has, though `aug_mode_batchgeneratorsv2` beat the other tweaks on every cycle it ran
(reports/loop_tweak_replication_2026-10-25.md). This replays a rule over replicates on that record's 546 cycles, in the
order they ran, and asks two things: how often it promotes when no tweak differs, and what it promotes on the real
sequence.

THE RULE. At the end of cycle j, of tweak T: each of T's cycles so far, i, gets d_i = x_i - the mean of the other
tweaks' cycles so far that started in i's code epoch (kept only if that epoch has at least --min-others of them). With
n kept, t = mean(d) / (sd(d) / sqrt(n)). The rule promotes cycle j's candidate when n >= --min-cycles and t > c for every
measure (val_f1 and ROC AUC, or val_f1 alone). It uses only cycles that have already ended, as a live loop would.

THE NULL. Shuffle the tweak labels among the cycles of each code epoch, keeping every cycle's scores and start, and
replay the rule. A window in which it promotes anything is a false promotion. The shuffle keeps each epoch's mix of
tweaks, but it also spreads the real effects (batchgeneratorsv2's higher cycles) over other labels. So a second null
first takes each tweak's measured effect out of its cycles: each cycle minus its tweak's mean difference from the other
tweaks in the same epoch, over the whole record. Its shuffles then hold cycle-to-cycle noise and no tweak effect.

The rule fires at c exactly when the window's largest score max_j min_measures t exceeds c, so one replay per
permutation gives the false-promotion rate at every c.

Exploratory. The record is the one batchgeneratorsv2 was found in, so when the rule would have taken it is in-sample.
The false-promotion rate is not: it comes from the shuffled labels. Only cycles before the registered confirmation's
window (2026-10-25T16:00) are read.

    python3 scripts/loop_replicate_rule.py --record reports/loop_tweak_replication_2026-10-25.json --out reports/X.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

WINDOW_START = (
    "2026-10-25T16:00:00"  # the registered confirmation's window; never read here
)
MEASURES = {"val_f1_and_roc_auc": ("val_f1", "roc_auc"), "val_f1_only": ("val_f1",)}
THRESHOLDS = (3.0, 3.5, 4.0, 4.5, 5.0, 6.0)
MIN_CYCLES = (6, 8)
MIN_OTHERS = 10
TARGET = 0.01  # the largest false-promotion rate per window this accepts
PERMUTATIONS = 1000
SEED = 20261026


def scores(rows, labels, measures, min_cycles, min_others=MIN_OTHERS):
    """Each cycle's rule score: the smallest t over the measures for its tweak at its end (-inf below min_cycles)."""
    S = {m: defaultdict(float) for m in measures}
    ST = {m: defaultdict(float) for m in measures}
    C = defaultdict(int)
    CT = defaultdict(int)
    seen = defaultdict(list)
    out = np.full(len(rows), -math.inf)
    for j, row in enumerate(rows):
        T, e = labels[j], row["epoch"]
        C[e] += 1
        CT[e, T] += 1
        for m in measures:
            S[m][e] += row[m]
            ST[m][e, T] += row[m]
        seen[T].append(j)
        if len(seen[T]) < min_cycles:
            continue
        ts = []
        for m in measures:
            d = []
            for i in seen[T]:
                k = rows[i]["epoch"]
                n_o = C[k] - CT[k, T]
                if n_o >= min_others:
                    d.append(rows[i][m] - (S[m][k] - ST[m][k, T]) / n_o)
            if len(d) < min_cycles:
                break
            sd = float(np.std(d, ddof=1))
            ts.append(
                math.inf if sd == 0 else float(np.mean(d)) / (sd / math.sqrt(len(d)))
            )
        else:
            out[j] = min(ts)
    return out


def shuffled(rows, rng):
    labels = [r["tweak"] for r in rows]
    by_epoch = defaultdict(list)
    for i, r in enumerate(rows):
        by_epoch[r["epoch"]].append(i)
    for e in sorted(by_epoch):
        pos = by_epoch[e]
        perm = rng.permutation(len(pos))
        old = [labels[i] for i in pos]
        for i, p in zip(pos, perm, strict=True):
            labels[i] = old[p]
    return labels


def centred(rows, measures):
    """Rows with each tweak's effect taken out: x_i - mean over the tweak's cycles of (x - other tweaks' epoch mean)."""
    by_epoch = defaultdict(list)
    for r in rows:
        by_epoch[r["epoch"]].append(r)
    effect = {}
    for m in measures:
        diffs = defaultdict(list)
        for r in rows:
            others = [o[m] for o in by_epoch[r["epoch"]] if o["tweak"] != r["tweak"]]
            if others:
                diffs[r["tweak"]].append(r[m] - sum(others) / len(others))
        effect[m] = {tw: sum(d) / len(d) for tw, d in diffs.items()}
    return [
        {**r, **{m: r[m] - effect[m].get(r["tweak"], 0.0) for m in measures}}
        for r in rows
    ]


def clopper_pearson(k, n, level=0.95):
    a = (1 - level) / 2
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a, k + 1, n - k))
    return [lo, hi]


def analyse(record, permutations=PERMUTATIONS, seed=SEED):
    rows = sorted(record["rows"], key=lambda r: r["start"])
    assert rows and max(r["start"] for r in rows) < WINDOW_START, (
        "reads only cycles before the confirmation window"
    )
    labels = [r["tweak"] for r in rows]
    rng = np.random.default_rng(seed)
    nulls = [shuffled(rows, rng) for _ in range(permutations)]
    grid = []
    maxima = {}
    for name, measures in MEASURES.items():
        for min_cycles in MIN_CYCLES:
            actual = scores(rows, labels, measures, min_cycles)
            null_max = [
                float(scores(rows, lab, measures, min_cycles).max()) for lab in nulls
            ]
            flat = centred(rows, measures)
            centred_max = [
                float(scores(flat, lab, measures, min_cycles).max()) for lab in nulls
            ]
            maxima[f"{name}/min_cycles_{min_cycles}"] = {
                "shuffled": null_max,
                "centred": centred_max,
            }
            best = defaultdict(lambda: -math.inf)
            for j, s in enumerate(actual):
                best[labels[j]] = max(best[labels[j]], float(s))
            for c in THRESHOLDS:
                k = sum(m > c for m in null_max)
                kc = sum(m > c for m in centred_max)
                fired = [j for j, s in enumerate(actual) if s > c]
                first = None
                if fired:
                    r = rows[fired[0]]
                    first = {
                        "cycle": fired[0] + 1,
                        "start": r["start"],
                        "tweak": r["tweak"],
                        "val_f1": r["val_f1"],
                        "roc_auc": r["roc_auc"],
                        "tweak_cycles_so_far": labels[: fired[0] + 1].count(r["tweak"]),
                    }
                grid.append(
                    {
                        "measures": name,
                        "min_cycles": min_cycles,
                        "c": c,
                        "false_promotions": k,
                        "rate": k / permutations,
                        "ci95": clopper_pearson(k, permutations),
                        "centred_false_promotions": kc,
                        "centred_rate": kc / permutations,
                        "centred_ci95": clopper_pearson(kc, permutations),
                        "first_promotion": first,
                        "tweaks_that_would_fire": sorted({labels[j] for j in fired}),
                    }
                )
            for row in grid:
                if row["measures"] == name and row["min_cycles"] == min_cycles:
                    row["largest_score_by_tweak"] = {
                        t: round(s, 3)
                        for t, s in sorted(best.items(), key=lambda kv: -kv[1])
                        if s > -math.inf
                    }
    chosen = {}
    for name in MEASURES:
        for min_cycles in MIN_CYCLES:
            ok = [
                g
                for g in grid
                if g["measures"] == name
                and g["min_cycles"] == min_cycles
                and max(g["rate"], g["centred_rate"]) <= TARGET
            ]
            chosen[f"{name}/min_cycles_{min_cycles}"] = (
                min(ok, key=lambda g: g["c"])["c"] if ok else None
            )
    return {
        "cycles": len(rows),
        "first_start": rows[0]["start"],
        "last_start": rows[-1]["start"],
        "tweaks": len(set(labels)),
        "epochs": len({r["epoch"] for r in rows}),
        "min_others": MIN_OTHERS,
        "permutations": permutations,
        "seed": seed,
        "target_rate": TARGET,
        "smallest_c_at_target": chosen,
        "grid": grid,
        "null_maxima": maxima,  # per permutation, in draw order: the window's largest rule score
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--record", required=True, help="loop_tweak_replication's JSON record"
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw = Path(args.record).read_bytes()
    out = {"source": {"record": args.record, "sha256": hashlib.sha256(raw).hexdigest()}}
    out.update(analyse(json.loads(raw)))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for name, c in out["smallest_c_at_target"].items():
        print(f"{name}: smallest c with false-promotion rate <= {TARGET}: {c}")


if __name__ == "__main__":
    main()
