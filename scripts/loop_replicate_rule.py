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

THE REGISTERED WINDOW TEST (docs/preregistration/2026-10-26_loop_replicate_rule_window.md). The rule at the c chosen
above (REGISTERED), frozen, on the confirmation window's cycles: --window reads the output of the confirmation's
registered command, keeps the cycles its verdict reads (to the standing tweak's 8th), and replays the rule from the
window's start. Its first promotion, set against the confirmation's reading, is the result. --power estimates, from
the cycles before the window only, how often that happens when the standing tweak's effect is the exploratory one,
half of it, or none.

    python3 scripts/loop_replicate_rule.py --record reports/loop_tweak_replication_2026-10-25.json --power --out X.json
    python3 scripts/loop_replicate_rule.py --window reports/<the confirmation's output>.json --out reports/Y.json
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


def tweak_effects(rows, measures):
    """Per measure and tweak: the mean over the tweak's cycles of (x - the other tweaks' mean in its epoch)."""
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
    return effect


def centred(rows, measures):
    """Rows with each tweak's effect taken out: x_i - mean over the tweak's cycles of (x - other tweaks' epoch mean)."""
    effect = tweak_effects(rows, measures)
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


# docs/preregistration/2026-10-26_loop_replicate_rule_window.md: the rule at the c the replay above chose, frozen.
REGISTERED = {
    "since": WINDOW_START,
    "standing": "aug_mode_batchgeneratorsv2",
    "measures": "val_f1_and_roc_auc",
    "min_cycles": 6,
    "min_others": MIN_OTHERS,
    "c": 4.5,
}
# The confirmation's own window (loop_tweak_replication.REGISTERED): its cut, and when it gives no reading.
CONFIRMATION = {"cut_at": 8, "min_standing": 6, "min_others": 60}
# The standing tweak's exploratory effect, half of it, none.
POWER_SCALES = (1.0, 0.5, 0.0)
POWER_SIMULATIONS = 2000
DEADLINE_HOURS = 96  # 2026-10-25 16:00 to the confirmation's deadline, 2026-10-29 16:00
# Reported, not registered: the same simulation run on to the standing tweak's 20th cycle, with no deadline.
HORIZON = {"cut_at": 20, "simulations": 1000}


def _finite(x):
    return None if not math.isfinite(x) else round(float(x), 4)


def cap_cycles(rows):
    """The cycles the window holds by its deadline, at the pace of the cycles before it."""
    starts = sorted(np.datetime64(r["start"]) for r in rows)
    hours = (starts[-1] - starts[0]) / np.timedelta64(1, "h")
    return round(len(rows) / hours * DEADLINE_HOURS)


def power(record, scales=POWER_SCALES, simulations=POWER_SIMULATIONS, seed=SEED, reg=REGISTERED, cut_at=CONFIRMATION["cut_at"], deadline=True):  # fmt: skip
    """How often the frozen rule's first promotion in a window like the confirmation's is the standing tweak.

    The noise is the record's cycles (all before the window) with every tweak's effect taken out (centred) and each
    epoch's mean removed: cycle-to-cycle noise in one code epoch. Each simulated cycle is the standing tweak at the
    record's rate, its noise the next of the standing tweak's own cycles (shuffled, so none repeats) plus `scale`
    times its measured effect. Otherwise its noise is the next of the other cycles (shuffled; reshuffled when used
    up), and its tweak is drawn from the other cycles' tweaks apart from that noise, so no tweak re-draws its own
    few cycles. A window ends at the standing tweak's `cut_at`-th cycle or (with `deadline`) at the deadline's
    cycle count, and gives no reading with fewer than 6 standing cycles or 60 others.
    """
    rows = sorted(record["rows"], key=lambda r: r["start"])
    assert rows and max(r["start"] for r in rows) < WINDOW_START, (
        "reads only cycles before the confirmation window"
    )
    measures = MEASURES[reg["measures"]]
    effect = tweak_effects(rows, measures)
    flat = centred(rows, measures)
    means = {}
    for e in {r["epoch"] for r in flat}:
        members = [r for r in flat if r["epoch"] == e]
        means[e] = {m: sum(r[m] for r in members) / len(members) for m in measures}
    noise = [{m: r[m] - means[r["epoch"]][m] for m in measures} for r in flat]
    labels = [r["tweak"] for r in rows]
    mine = [noise[i] for i, t in enumerate(labels) if t == reg["standing"]]
    rest = [noise[i] for i, t in enumerate(labels) if t != reg["standing"]]
    rest_tweaks = [t for t in labels if t != reg["standing"]]
    if cut_at > len(mine):
        raise ValueError(
            f"the standing tweak has {len(mine)} cycles, fewer than {cut_at}"
        )
    rate = len(mine) / len(rows)
    cap = cap_cycles(rows) if deadline else math.inf
    out = []
    for index, scale in enumerate(scales):
        rng = np.random.default_rng([seed, index])
        lift = {m: scale * effect[m][reg["standing"]] for m in measures}
        trace = []
        for _ in range(simulations):
            sim, tweaks = [], []
            own = iter(rng.permutation(len(mine)))
            other = iter(())
            n_standing = 0
            while len(sim) < cap and n_standing < cut_at:
                if rng.random() < rate:
                    x = mine[int(next(own))]
                    sim.append({"epoch": "w", **{m: x[m] + lift[m] for m in measures}})  # fmt: skip
                    tweaks.append(reg["standing"])
                    n_standing += 1
                    continue
                k = next(other, None)
                if k is None:
                    other = iter(rng.permutation(len(rest)))
                    k = next(other)
                sim.append({"epoch": "w", **rest[int(k)]})
                tweaks.append(rest_tweaks[int(rng.integers(len(rest_tweaks)))])
            if (
                n_standing < CONFIRMATION["min_standing"]
                or len(tweaks) - n_standing < CONFIRMATION["min_others"]
            ):
                trace.append("incomplete")
                continue
            s = scores(sim, tweaks, measures, reg["min_cycles"], reg["min_others"])
            fired = [j for j, x in enumerate(s) if x > reg["c"]]
            if not fired:
                trace.append("none")
            elif tweaks[fired[0]] == reg["standing"]:
                trace.append(f"standing@{tweaks[: fired[0] + 1].count(reg['standing'])}")  # fmt: skip
            else:
                trace.append("other")
        outcomes = {k: 0 for k in ("standing", "other", "none", "incomplete")}
        at = defaultdict(int)
        for t in trace:
            outcomes[t.split("@")[0]] += 1
            if t.startswith("standing@"):
                at[t.split("@")[1]] += 1
        out.append(
            {
                "scale": scale,
                "lift": lift,
                "outcomes": outcomes,
                "fired_at_standing_cycle": dict(
                    sorted(at.items(), key=lambda kv: int(kv[0]))
                ),
                "trace": trace,
            }
        )
    return {
        "registered": reg,
        "confirmation": CONFIRMATION,
        "cycles": len(rows),
        "cut_at": cut_at,
        "cap_cycles": cap if deadline else None,
        "simulations": simulations,
        "seed": seed,
        "standing_effect": {m: effect[m][reg["standing"]] for m in measures},
        "scales": out,
    }


READINGS = {
    ("standing", True): "TAKES_CONFIRMED_GAIN",
    ("standing", False): "PROMOTES_UNCONFIRMED",
    ("other", True): "PROMOTES_ANOTHER_TWEAK",
    ("other", False): "PROMOTES_ANOTHER_TWEAK",
    ("none", True): "MISSES_CONFIRMED_GAIN",
    ("none", False): "ABSTAINS",
}


def window_test(confirmation, permutations=PERMUTATIONS, seed=SEED, reg=REGISTERED):
    """The registered test: the frozen rule's first promotion on the confirmation window's cycles, and its reading."""
    theirs = confirmation.get("registered") or {}
    wanted = {"since": reg["since"], "standing": reg["standing"], **CONFIRMATION}
    if {k: theirs.get(k) for k in wanted} != wanted:
        raise SystemExit(
            "not the output of the registered confirmation (its registered window differs)"
        )
    verdict = confirmation["verdict"]
    base = {
        "registered": reg,
        "confirmation": {
            "status": verdict["status"],
            "reading": verdict.get("reading"),
        },
    }
    rows = sorted(confirmation["rows"], key=lambda r: r["start"])
    if rows and rows[0]["start"] < reg["since"]:
        raise SystemExit(f"a cycle starts before the window ({rows[0]['start']})")
    if verdict["status"] != "OK":
        return dict(base, status=verdict["status"], reading=None)
    standing = [j for j, r in enumerate(rows) if r["tweak"] == reg["standing"]]
    if len(standing) > CONFIRMATION["cut_at"]:
        rows = rows[: standing[CONFIRMATION["cut_at"] - 1] + 1]
    labels = [r["tweak"] for r in rows]
    measures = MEASURES[reg["measures"]]
    args = (reg["min_cycles"], reg["min_others"])
    s = scores(rows, labels, measures, *args)
    each = {m: scores(rows, labels, (m,), *args) for m in measures}
    fired = [j for j, x in enumerate(s) if x > reg["c"]]
    first = None
    outcome = "none"
    if fired:
        j = fired[0]
        outcome = "standing" if labels[j] == reg["standing"] else "other"
        first = {
            "cycle": j + 1,
            "start": rows[j]["start"],
            "tweak": labels[j],
            "tweak_cycles_so_far": labels[: j + 1].count(labels[j]),
            "score": _finite(s[j]),
        }
    best = defaultdict(lambda: -math.inf)
    for j, x in enumerate(s):
        best[labels[j]] = max(best[labels[j]], float(x))
    rng = np.random.default_rng(seed)
    nulls = [shuffled(rows, rng) for _ in range(permutations)]
    flat = centred(rows, measures)
    plain = [float(scores(rows, n, measures, *args).max()) for n in nulls]
    flat_max = [float(scores(flat, n, measures, *args).max()) for n in nulls]
    return dict(
        base,
        status="OK",
        cycles=len(rows),
        first_start=rows[0]["start"],
        last_start=rows[-1]["start"],
        outcome=outcome,
        first_promotion=first,
        reading=READINGS[outcome, verdict.get("reading") == "CONFIRMED"],
        standing_cycles=[
            {
                "start": rows[j]["start"],
                "tweak_cycles_so_far": k + 1,
                "score": _finite(s[j]),
                **{f"t_{m}": _finite(each[m][j]) for m in measures},
            }
            for k, j in enumerate(
                i for i, t in enumerate(labels) if t == reg["standing"]
            )
        ],
        largest_score_by_tweak={
            t: round(x, 3)
            for t, x in sorted(best.items(), key=lambda kv: -kv[1])
            if x > -math.inf
        },
        null={
            "permutations": permutations,
            "seed": seed,
            "false_promotions": sum(m > reg["c"] for m in plain),
            "centred_false_promotions": sum(m > reg["c"] for m in flat_max),
            "shuffled": plain,
            "centred": flat_max,
        },
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--record", help="loop_tweak_replication's JSON record")
    src.add_argument(
        "--window",
        help="the registered confirmation's output (loop_tweak_replication.py --registered)",
    )
    ap.add_argument(
        "--power",
        action="store_true",
        help="with --record: the registered window test's power",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.power and not args.record:
        ap.error("--power takes --record")
    path = args.record or args.window
    raw = Path(path).read_bytes()
    key = "record" if args.record else "confirmation"
    out = {"source": {key: path, "sha256": hashlib.sha256(raw).hexdigest()}}
    if args.window:
        out.update(window_test(json.loads(raw)))
        Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps({k: out.get(k) for k in ("status", "confirmation", "outcome", "first_promotion", "reading")}, indent=1))  # fmt: skip
        return
    if args.power:
        record = json.loads(raw)
        out.update(power(record))
        out["horizon"] = power(record, simulations=HORIZON["simulations"], cut_at=HORIZON["cut_at"], deadline=False)  # fmt: skip
        Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
        for scale in out["scales"]:
            print(scale["scale"], scale["outcomes"], scale["fired_at_standing_cycle"])
        return
    out.update(analyse(json.loads(raw)))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for name, c in out["smallest_c_at_target"].items():
        print(f"{name}: smallest c with false-promotion rate <= {TARGET}: {c}")


if __name__ == "__main__":
    main()
