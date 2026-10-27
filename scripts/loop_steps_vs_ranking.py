"""Within one tweak, do the loop's cycles that train fewer steps score differently? Exploratory, on the cycles before
the batchgeneratorsv2 window (reports/loop_tweak_replication_2026-10-25.json), and fixed before that window's readout.

Every 15-minute cycle fine-tunes the same incumbent for the same wall time. How many steps it trains depends on its
recipe and on the host's load. Within one tweak and one code epoch the recipe is fixed, so a cycle's steps differ from
its group's mean by load alone. Each measure's deviation from its group's mean, regressed on the steps' deviation
through the origin (fixed effects for tweak x epoch), gives what training fewer steps does at a fixed recipe. The
standing tweak is left out of the slope it is compared with.

`aug_mode_batchgeneratorsv2` keeps the model, loss, batch size and learning rate, and trains about 300 fewer steps
because its augmentation runs inside each training step, sample by sample, so each step takes longer, as load makes it
(not in the loader: scripts/loop_host_load.py). UAMT off (about 4,150 cheaper steps) and batch 16 (about 630 steps of
twice the size) change what a step is, so the step gap is measured against the other tweaks.

    python3 scripts/loop_steps_vs_ranking.py --record reports/loop_tweak_replication_2026-10-25.json --out reports/X.json

`window_adjustment` gives the same comparison on the registered confirmation's output, with the slope fixed here:
reported beside the confirmation's effects, it changes no reading.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop_tweak_replication as ltr  # noqa: E402

STANDING = ltr.REGISTERED["standing"]
MEASURES = ("val_f1", "roc_auc", "ap_lift")
OTHER_STEP_COSTS = ("use_uamt_False", "batch_size_16")
PERMUTATIONS = 10_000
BOOTSTRAPS = 2_000
SEED = 0
BINS = (-1000, -150, -50, 50, 150, 1000)
EPOCH = dt.datetime(1970, 1, 1)


def deviations(rows: list[dict], leave_out=(STANDING,)) -> list[dict]:
    """Each cycle's steps, hours and measures minus its tweak x epoch group's means. Groups of one are dropped."""
    groups = defaultdict(list)
    for r in rows:
        if r["tweak"] not in leave_out:
            groups[r["tweak"], r["epoch"]].append(r)
    out = []
    for (tweak, epoch), members in groups.items():
        if len(members) < 2:
            continue
        # The starts are the loop's own clock, read the same on every machine. .timestamp() read them in the
        # runner's zone, so a runner whose clocks changed inside the record (Europe/London on 10-25) got another
        # with_hours.
        hours = [
            (dt.datetime.fromisoformat(r["start"]) - EPOCH).total_seconds() / 3600
            for r in members
        ]
        keys = ("steps", *MEASURES)
        mean = {k: np.mean([r[k] for r in members]) for k in keys}
        for r, h in zip(members, hours, strict=True):
            d = {k: r[k] - mean[k] for k in keys}
            out.append(
                dict(
                    d,
                    tweak=tweak,
                    epoch=epoch,
                    day=r["start"][:10],
                    hours=h - np.mean(hours),
                )
            )
    return out


def _xy(dev, measure):
    x = np.array([d["steps"] for d in dev]) / 100
    return x, np.array([d[measure] for d in dev])


def slope(dev: list[dict], measure: str) -> dict:
    """Per 100 steps, with its t interval (df: cycles - groups - 1)."""
    x, y = _xy(dev, measure)
    b = float(x @ y / (x @ x))
    df = len(dev) - len({(d["tweak"], d["epoch"]) for d in dev}) - 1
    se = float(np.sqrt(((y - b * x) @ (y - b * x)) / df / (x @ x)))
    q = float(stats.t.ppf(0.975, df))
    return {"per_100_steps": b, "se": se, "ci95": [b - q * se, b + q * se], "df": df}


def permutation_p(dev: list[dict], measure: str, n: int, rng) -> float:
    """Two-sided: the steps' deviations shuffled within each group."""
    x, y = _xy(dev, measure)
    groups = defaultdict(list)
    for i, d in enumerate(dev):
        groups[d["tweak"], d["epoch"]].append(i)
    index = [np.array(v) for v in groups.values()]
    observed = abs(x @ y / (x @ x))
    hits = 0
    for _ in range(n):
        xp = x.copy()
        for idx in index:
            xp[idx] = rng.permutation(x[idx])
        hits += abs(xp @ y / (xp @ xp)) >= observed
    return hits / n


def day_bootstrap(dev: list[dict], measure: str, n: int, rng) -> list[float]:
    """95% interval of the slope with whole days resampled (few days: a rough check on clustering)."""
    x, y = _xy(dev, measure)
    day = np.array([d["day"] for d in dev])
    days = np.unique(day)
    rows_of = {k: np.where(day == k)[0] for k in days}
    draws = []
    for _ in range(n):
        idx = np.concatenate([rows_of[k] for k in rng.choice(days, len(days))])
        draws.append(x[idx] @ y[idx] / (x[idx] @ x[idx]))
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def with_hours(dev: list[dict], measure: str) -> float:
    """The steps slope with time within the group as a second regressor."""
    x, y = _xy(dev, measure)
    coef, *_ = np.linalg.lstsq(
        np.column_stack([x, [d["hours"] for d in dev]]), y, rcond=None
    )
    return float(coef[0])


def leave_one_tweak_out(dev: list[dict], measure: str) -> list[float]:
    got = []
    for tweak in sorted({d["tweak"] for d in dev}):
        x, y = _xy([d for d in dev if d["tweak"] != tweak], measure)
        got.append(float(x @ y / (x @ x)))
    return [min(got), max(got)]


def by_bin(dev: list[dict]) -> list[dict]:
    out = []
    for lo, hi in pairwise(BINS):
        members = [d for d in dev if lo <= d["steps"] < hi]
        out.append(
            {"steps_from": lo, "steps_to": hi, "n": len(members), "steps": float(np.mean([d["steps"] for d in members])),
             **{m: float(np.mean([d[m] for d in members])) for m in MEASURES}}
        )  # fmt: skip
    return out


def step_gap(
    rows: list[dict], standing: str = STANDING, leave_out=OTHER_STEP_COSTS
) -> float:
    """The standing tweak's steps minus the mean of its epoch's other cycles, averaged, as its effects are."""
    by_epoch = defaultdict(list)
    for r in rows:
        if r["tweak"] not in (standing, *leave_out):
            by_epoch[r["epoch"]].append(r["steps"])
    gaps = [
        r["steps"] - np.mean(by_epoch[r["epoch"]])
        for r in rows
        if r["tweak"] == standing
    ]
    return float(np.mean(gaps))


def analyse(
    record: dict, permutations=PERMUTATIONS, bootstraps=BOOTSTRAPS, seed=SEED
) -> dict:
    rows = record["rows"]
    if max(r["start"] for r in rows) >= ltr.REGISTERED["since"]:
        raise SystemExit("the record reaches into the confirmation's window")
    dev = deviations(rows)
    rng = np.random.default_rng(seed)
    measures = {}
    for m in MEASURES:
        s = slope(dev, m)
        per_tweak = []
        for tweak in sorted({d["tweak"] for d in dev}):
            mine = [d for d in dev if d["tweak"] == tweak]
            if len(mine) >= 8:
                per_tweak.append(slope(mine, m)["per_100_steps"])
        measures[m] = dict(
            s,
            permutation_p=permutation_p(dev, m, permutations, rng),
            day_bootstrap95=day_bootstrap(dev, m, bootstraps, rng),
            with_hours=with_hours(dev, m),
            leave_one_tweak_out=leave_one_tweak_out(dev, m),
            tweaks_with_negative_slope=[sum(b < 0 for b in per_tweak), len(per_tweak)],
        )
    gap = step_gap(rows)
    own = deviations([r for r in rows if r["tweak"] == STANDING], leave_out=())
    standing = {
        "tweak": STANDING,
        "cycles": sum(r["tweak"] == STANDING for r in rows),
        "step_gap": gap,
        "step_gap_against_every_tweak": step_gap(rows, leave_out=()),
        "effects": {m: ltr.effects(rows, m)[STANDING]["mean_diff"] for m in MEASURES},
        "its_own_slope": {m: slope(own, m)["per_100_steps"] for m in MEASURES},
        "from_its_steps": {
            m: {
                "predicted": measures[m]["per_100_steps"] * gap / 100,
                "ci95": sorted(b * gap / 100 for b in measures[m]["ci95"]),
            }
            for m in MEASURES
        },
    }
    return {
        "cycles": len(rows),
        "last_start": max(r["start"] for r in rows),
        "deviations": len(dev),
        "groups": len({(d["tweak"], d["epoch"]) for d in dev}),
        "permutations": permutations,
        "bootstraps": bootstraps,
        "seed": seed,
        "measures": measures,
        "bins": by_bin(dev),
        "standing": standing,
    }


def window_adjustment(confirmation: dict, analysis: dict) -> dict:
    """The confirmation's standing effects beside what its step gap in the window predicts, with the slopes fixed
    before the window. Cut at the 8th standing cycle, as the confirmation's verdict is."""
    reg = ltr.REGISTERED
    rows = sorted(confirmation["rows"], key=lambda r: r["start"])
    standing = [j for j, r in enumerate(rows) if r["tweak"] == reg["standing"]]
    if len(standing) > reg["cut_at"]:
        rows = rows[: standing[reg["cut_at"] - 1] + 1]
    gap = step_gap(rows, reg["standing"])
    out = {"step_gap": gap}
    for m in MEASURES:
        effect = ltr.effects(rows, m)[reg["standing"]]["mean_diff"]
        predicted = analysis["measures"][m]["per_100_steps"] * gap / 100
        out[m] = {
            "effect": effect,
            "from_its_steps": predicted,
            "beyond_its_steps": effect - predicted,
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--record",
        required=True,
        help="loop_tweak_replication's JSON record, before the window",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw = Path(args.record).read_bytes()
    out = {"source": {"record": args.record, "sha256": hashlib.sha256(raw).hexdigest()}}
    out.update(analyse(json.loads(raw)))
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for m, s in out["measures"].items():
        print(
            f"{m}: {s['per_100_steps']:+.5f} per 100 steps, p {s['permutation_p']:.4f}"
        )


if __name__ == "__main__":
    main()
