"""Does any loop tweak beat the others reproducibly, on one incumbent? Every cycle since a promotion, by tweak.

The loop applies one tweak per cycle to the incumbent's config and fine-tunes best_model.pt for the cycle's budget; it
promotes only a val_f1 more than F1_NOISE_TOLERANCE (0.01) above the stored incumbent. Since the 2026-10-17 promotion
(batch_size_8, 0.265762) no cycle has promoted, but each tweak has recurred, so each has replicates. This takes every
scored 15-minute cycle that started in [--since, --until), from the sprint logs (tweak, start, budget, val_f1; parsed
by epoch_boundary_overhead.cycles), and joins each to its run in the loop's run logs by val_f1 (six decimals, as the run
log prints it) for the threshold-free measures the run also prints: ROC AUC, AP prevalence lift and mean AP.

The loop's code changed under it: each merge into the loop's checkout that touched what it runs starts an EPOCH, and a
cycle belongs to the epoch in force when it started. A tweak's effect is measured against its own epoch's other cycles:
each of its cycles minus the mean of the other tweaks' cycles that started in the same epoch. Per measure, the mean of
those differences, Student's t on them, and Holm's adjustment across the tweaks.

Descriptive and exploratory: the tweak that stands out was seen before this was written.

    python3 scripts/loop_tweak_replication.py --sprint-logs 'sprint_logs/sprint_log_2026-10-*.md' \
        --run-log run.log.old run.log --since 2026-10-17T14:01:56 --until 2026-10-25T14:30:00 --out reports/X.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epoch_boundary_overhead as ebo  # noqa: E402

TOLERANCE = 0.01  # train.py's F1_NOISE_TOLERANCE
BUDGET = 900
MEASURES = ("val_f1", "roc_auc", "ap_lift", "mean_ap")
# Merges into the loop's checkout (its reflog) that changed run_autoresearch_loop.py, scripts/training/, src/,
# pyproject.toml or uv.lock, from the promotion on. Two other merges changed none of them: 329fadd6 (10-19 21:59)
# and the 20 s checkout of origin/main b808f3d3 at 10-25 00:09 (same files as 139c6873's).
EPOCHS = (
    ("2026-10-17T14:01:56", "1b7a304c", "the promotion commit (batch_size_8)"),
    (
        "2026-10-17T21:16:50",
        "5acb5342",
        "train.py, promotion.py, loader, detector cli, loop",
    ),
    ("2026-10-19T08:51:41", "0102e63a", "#119-#140: train.py, loop"),
    (
        "2026-10-19T19:17:28",
        "86532907",
        "#141-#148: train.py (#145/#146 augmentations off the ridge channel)",
    ),
    (
        "2026-10-20T10:37:22",
        "a362159e",
        "#151-#157: dead code removed from train.py, config, loop",
    ),
    ("2026-10-20T15:36:11", "42f29ba2", "#158-#163: loop only (night budget 900 s)"),
    (
        "2026-10-23T21:01:49",
        "bf8a957c",
        "#164-#213: train.py, mutex_data, loader, promotion, detector",
    ),
    ("2026-10-24T14:13:09", "139c6873", "#214-#225: uv.lock (non-ML packages)"),
)
RUN_START = ebo.RUN_START
VAL = re.compile(r"^val_f1:\s+([0-9.]+) \(thr ([0-9.]+); incumbent ([0-9.]+)\)")
FIELDS = {
    "ap_lift": re.compile(r"^ap_prevalence_lift:\s+([0-9.]+)"),
    "roc_auc": re.compile(r"^roc_auc:\s+([0-9.]+)"),
    "mean_ap": re.compile(r"^avg_mean_ap:\s+([0-9.]+)"),
}


def runs(run_logs: list[str]) -> dict[float, list[dict]]:
    """val_f1 (six decimals) -> each scored run's threshold, incumbent, AUC, AP lift, mean AP and last step."""
    lines = [ln for p in run_logs for ln in Path(p).read_text(errors="replace").split("\n")]  # fmt: skip
    starts = [i for i, ln in enumerate(lines) if ln.startswith(RUN_START)]
    out: dict[float, list[dict]] = defaultdict(list)
    for k, s in enumerate(starts):
        seg = lines[s : starts[k + 1] if k + 1 < len(starts) else len(lines)]
        val = [m for m in map(VAL.match, seg) if m]
        if not val:
            continue
        rec = {
            "threshold": float(val[0].group(2)),
            "incumbent": float(val[0].group(3)),
        }
        for key, rx in FIELDS.items():
            got = [m for m in map(rx.match, seg) if m]
            rec[key] = float(got[0].group(1)) if got else None
        steps = [m for m in (re.match(r"Step (\d+) \|", ln) for ln in seg) if m]
        rec["steps"] = int(steps[-1].group(1)) if steps else None
        out[round(float(val[0].group(1)), 6)].append(rec)
    return out


def epoch_of(start: str) -> str:
    t = dt.datetime.fromisoformat(start)
    names = [sha for when, sha, _ in EPOCHS if t >= dt.datetime.fromisoformat(when)]
    if not names:
        raise ValueError(f"{start} is before the first epoch")
    return names[-1]


def cycles(patterns: list[str], run_logs: list[str], since: str, until: str, incumbent: float, stop_at_promotion: bool = False) -> tuple[list[dict], dict]:  # fmt: skip
    paths = sorted({p for pat in patterns for p in glob.glob(pat)})
    if not paths:
        raise SystemExit(f"no sprint log matches {patterns}")
    lo, hi = dt.datetime.fromisoformat(since), dt.datetime.fromisoformat(until)
    kept = sorted(
        (
            c
            for p in paths
            for c in ebo.cycles(glob.escape(p))
            if lo <= dt.datetime.fromisoformat(c["start"]) < hi
        ),  # fmt: skip
        key=lambda c: c["start"],
    )
    promoted = next((c for c in kept if c["result"] == "SUCCESS"), None)
    if promoted is not None:
        if not stop_at_promotion:
            raise SystemExit(
                "a cycle in the window promoted: the window must face one incumbent"
            )
        kept = kept[
            : kept.index(promoted) + 1
        ]  # the promoted cycle faced this incumbent; the next ones do not
    # Only runs that faced this window's incumbent: a val_f1 can recur under another one (protocol v2's values
    # near the all-ink floor do). A value scored by several cycles is matched to its runs in time order, both being
    # in time order, and left unmatched if the counts differ.
    by_f1 = {
        k: [r for r in v if r["incumbent"] == incumbent]
        for k, v in runs(run_logs).items()
    }
    tally = {"cycles": len(kept), "unscored": 0, "other_budget": 0, "unmatched": 0,
             "promoted": None if promoted is None else {"tweak": promoted["cycle"], "start": promoted["start"]}}  # fmt: skip
    scored = [c for c in kept if c["val_f1"] is not None]
    tally["unscored"] = len(kept) - len(scored)
    # every scored cycle claims its value's runs, the 15-minute ones and the others alike
    claims = defaultdict(list)
    for c in scored:
        claims[round(c["val_f1"], 6)].append(c)
    rows = []
    for c in scored:
        if c["budget"] != BUDGET:
            tally["other_budget"] += 1
            continue
        key = round(c["val_f1"], 6)
        row = {
            "start": c["start"],
            "epoch": epoch_of(c["start"]),
            "tweak": c["cycle"],
            "val_f1": c["val_f1"],
        }
        match = by_f1.get(key, [])
        if match and len(match) == len(claims[key]):
            row.update(match[claims[key].index(c)])
        else:
            tally["unmatched"] += 1
        rows.append(row)
    return rows, tally


def effects(rows: list[dict], measure: str) -> dict:
    """Per tweak: its cycles minus the mean of its epoch's other cycles, with t and Holm-adjusted p."""
    have = [r for r in rows if r.get(measure) is not None]
    by_epoch = defaultdict(list)
    for r in have:
        by_epoch[r["epoch"]].append(r)
    out = {}
    for tweak in sorted({r["tweak"] for r in have}):
        diffs = []
        for r in have:
            if r["tweak"] != tweak:
                continue
            others = [o[measure] for o in by_epoch[r["epoch"]] if o["tweak"] != tweak]
            if others:
                diffs.append(r[measure] - statistics.mean(others))
        n = len(diffs)
        mean = statistics.mean(diffs) if diffs else None
        sd = statistics.stdev(diffs) if n > 1 else None
        t = mean / (sd / math.sqrt(n)) if sd else None
        p = float(2 * stats.t.sf(abs(t), n - 1)) if t is not None else None
        out[tweak] = {"n": n, "mean_diff": mean, "sd": sd, "t": t, "p": p}
    ranked = sorted((v["p"], k) for k, v in out.items() if v["p"] is not None)
    m, running = len(ranked), 0.0
    for i, (p, k) in enumerate(ranked):  # Holm: step-down, kept monotone
        running = max(running, min(1.0, (m - i) * p))
        out[k]["p_holm"] = running
    return out


def summary(rows: list[dict], tweak: str, incumbent: float) -> dict:
    """The standing tweak's cycles against the rest, per epoch, and against the promotion bar."""
    mine = [r for r in rows if r["tweak"] == tweak]
    rest = [r for r in rows if r["tweak"] != tweak]

    def mean(rs, key):
        v = [r[key] for r in rs if r.get(key) is not None]
        return statistics.mean(v) if v else None

    per_epoch = {
        e: {
            "n": sum(r["epoch"] == e for r in mine),
            "n_others": sum(r["epoch"] == e for r in rest),
            **{
                f"{k}_mean": mean([r for r in mine if r["epoch"] == e], k)
                for k in ("val_f1", "roc_auc")
            },  # fmt: skip
            **{
                f"{k}_others": mean([r for r in rest if r["epoch"] == e], k)
                for k in ("val_f1", "roc_auc")
            },  # fmt: skip
        }
        for _, e, _ in EPOCHS
        if any(r["epoch"] == e for r in mine)
    }
    f1 = [r["val_f1"] for r in mine]
    bar = incumbent + TOLERANCE
    if len(f1) < 2 or not rest:
        return {"tweak": tweak, "n": len(mine), "bar": bar}
    mu, sd = statistics.mean(f1), statistics.stdev(f1)
    return {
        "tweak": tweak,
        "n": len(mine),
        "val_f1_mean": mu,
        "val_f1_sd": sd,
        "val_f1_max": max(f1),
        "bar": bar,
        "cleared_bar": sum(v > bar for v in f1),
        "p_clear_one_cycle_normal": float(stats.norm.sf((bar - mu) / sd)),
        "steps_median": statistics.median(r["steps"] for r in mine if r.get("steps")),
        "steps_median_others": statistics.median(
            r["steps"] for r in rest if r.get("steps")
        ),  # fmt: skip
        "per_epoch": per_epoch,
    }


# docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md: the confirmation on the loop's next cycles.
REGISTERED = {
    "since": "2026-10-25T16:00:00",
    "deadline": "2026-10-29T16:00:00",
    "standing": "aug_mode_batchgeneratorsv2",
    "cut_at": 8,  # the window ends with the standing tweak's 8th 15-minute cycle
    "min_standing": 6,
    "min_others": 60,
    "P1_val_f1": 0.0020,
    "P2_roc_auc": 0.0050,
    "P3_ap_lift": 0.015,
}


def registered_verdict(
    rows: list[dict], tally: dict, incumbent: float, reg: dict = REGISTERED
) -> dict:
    """The registered predictions and reading on the window's cycles, or a status that gives none."""
    standing = [r for r in rows if r["tweak"] == reg["standing"]]
    if len(standing) > reg["cut_at"]:
        last = standing[reg["cut_at"] - 1]["start"]
        rows = [r for r in rows if r["start"] <= last]
        standing = standing[: reg["cut_at"]]
    others = [r for r in rows if r["tweak"] != reg["standing"]]
    base = {
        "n_standing": len(standing),
        "n_others": len(others),
        "promoted": tally.get("promoted"),
    }
    if tally.get("unmatched"):
        return dict(base, status="UNMATCHED_RUNS", reading=None)
    if len(standing) < reg["min_standing"] or len(others) < reg["min_others"]:
        return dict(base, status="INCOMPLETE", reading=None)
    eff = {
        m: effects(rows, m)[reg["standing"]]["mean_diff"]
        for m in ("val_f1", "roc_auc", "ap_lift")
    }
    bar = incumbent + TOLERANCE
    p = {
        "P1": eff["val_f1"] >= reg["P1_val_f1"],
        "P2": eff["roc_auc"] >= reg["P2_roc_auc"],
        "P3": eff["ap_lift"] >= reg["P3_ap_lift"],
        "P4": not any(r["val_f1"] > bar for r in standing),
    }
    reading = (
        "CONFIRMED"
        if p["P1"] and p["P2"]
        else "F1_ONLY"
        if p["P1"]
        else "NOT_REPLICATED"
    )
    return dict(base, status="OK", effects=eff, bar=bar, predictions=p, reading=reading)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sprint-logs", nargs="+", required=True)
    ap.add_argument("--run-log", nargs="+", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--incumbent", type=float, default=0.265762)
    ap.add_argument("--standing", default="aug_mode_batchgeneratorsv2")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--registered",
        action="store_true",
        help="the registered confirmation: its window and rule",
    )
    a = ap.parse_args(argv)
    if a.registered and (a.since, a.standing) != (
        REGISTERED["since"],
        REGISTERED["standing"],
    ):
        raise SystemExit(
            f"--registered takes --since {REGISTERED['since']} and the registered standing tweak"
        )
    if a.registered and a.until > REGISTERED["deadline"]:
        raise SystemExit(f"--registered ends by {REGISTERED['deadline']}")
    rows, tally = cycles(a.sprint_logs, a.run_log, a.since, a.until, a.incumbent, stop_at_promotion=a.registered)  # fmt: skip
    faced = {r["incumbent"] for r in rows if "incumbent" in r}
    if faced - {a.incumbent}:
        raise SystemExit(
            f"the runs faced incumbents {sorted(faced)}, not {a.incumbent}"
        )
    out = {
        "since": a.since,
        "until": a.until,
        "incumbent": a.incumbent,
        "tolerance": TOLERANCE,
        "budget_s": BUDGET,
        "epochs": [{"from": w, "sha": s, "change": c} for w, s, c in EPOCHS],
        "sources": {"sprint_logs": a.sprint_logs, "run_logs": a.run_log},
        "tally": tally,
        "effects": {m: effects(rows, m) for m in MEASURES},
        "standing": summary(rows, a.standing, a.incumbent),
        "rows": rows,
    }
    if a.registered:
        out["registered"] = REGISTERED
        out["verdict"] = registered_verdict(rows, tally, a.incumbent)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(
        json.dumps(
            {k: v for k, v in out.items() if k not in ("rows", "effects")}, indent=1
        )
    )
    e = out["effects"]
    for t in sorted(e["val_f1"], key=lambda k: -e["val_f1"][k]["mean_diff"]):
        cells = " ".join(
            f"{m}={e[m][t]['mean_diff']:+.4f}(p_holm {e[m][t]['p_holm']:.1g})"
            if t in e[m] and e[m][t].get("p_holm") is not None
            else f"{m}=-"  # fmt: skip
            for m in MEASURES
        )
        print(f"{t:36s} n={e['val_f1'][t]['n']:3d} {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
