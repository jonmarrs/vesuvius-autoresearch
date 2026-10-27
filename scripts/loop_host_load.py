"""Does the host's measured load move a loop cycle's ranking only through the steps it costs? Exploratory, on the cycles
before the batchgeneratorsv2 window (reports/loop_tweak_replication_2026-10-25.json), and fixed before that window's
readout.

scripts/loop_steps_vs_ranking.py (#250) finds that within one tweak, a cycle that trains fewer steps ranks ink better
(ROC AUC, AP lift) and scores the same val_f1. It assumes that a cycle's steps differ from its group's mean by the
host's load alone, and that load changes nothing in a cycle but its steps. sysstat samples the host's CPU every 10
minutes. A cycle's load is the time-weighted mean over its 990 s (the median gap between cycle starts: 900 s of
training and its setup) of busy (100 - %idle, in points of the host's 4 CPUs together) and of %nice (processes above
nice 0, which is where side jobs run; the loop runs at 0). Within tweak x epoch, the standing tweak left out:

- how many steps a point of busy costs (the first stage), and how much of the steps' spread it explains;
- the steps slope with busy as its instrument: from load's part of the steps alone;
- the slope on the part of the steps that load leaves;
- busy beside the steps: does load move a measure other than through the steps?

    python3 scripts/loop_host_load.py cycles --record reports/loop_tweak_replication_2026-10-25.json \
        --sysstat local_data/sysstat/sa1[89] local_data/sysstat/sa2[0-5] --out reports/loop_host_load_cycles_2026-10-26.json
    python3 scripts/loop_host_load.py analyse --record reports/loop_tweak_replication_2026-10-25.json \
        --load reports/loop_host_load_cycles_2026-10-26.json --out reports/loop_host_load_2026-10-26.json

sysstat deletes a file in /var/log/sysstat once it is more than 7 whole days old (HISTORY=7): copy the files to
local_data/sysstat before that. Its daily files leave 23:50 to 00:00 unsampled.

At the readout, `window` gives the window's cycles' load, from the confirmation's output and a `cycles` table made from
it, cut at the 8th standing cycle as the verdict is: the standing tweak's load beside the other tweaks', and by tweak,
the cycles a side job overlapped. It changes no reading.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop_steps_vs_ranking as svr  # noqa: E402

ltr = svr.ltr
STANDING = svr.STANDING
MEASURES = svr.MEASURES
SPAN = 990
COVERED = 0.8  # share of a cycle's span its samples must cover
# America/Los_Angeles, the host's zone, as a POSIX TZ
HOST_TZ = "PST8PDT,M3.2.0,M11.1.0"
SIDE_JOB_NICE = 10.0  # a cycle's mean %nice: a nice job on 40% or more of one CPU
BOOTSTRAPS = 2_000
SEED = 0


def clock(stamp: str) -> float:
    """Seconds on the host's naive local clock, which `sadf -t` and the loop both write, the same on every machine.
    .timestamp() would read them in the runner's zone (#253). The host's clock does not change between 10-18 and
    11-01, so its differences are elapsed time."""
    return (dt.datetime.fromisoformat(stamp) - svr.EPOCH).total_seconds()


def parse_sadf(text: str) -> list[tuple[float, int, float, float]]:
    """`sadf -d -t <file> -- -u` -> (sample end, its interval in s, %nice, %idle), all CPUs together."""
    out, cols = [], None
    for ln in text.splitlines():
        if ln.startswith("# "):
            cols = ln[2:].split(";")
            continue
        f = ln.split(";")
        if not ln or cols is None or len(f) != len(cols):
            continue
        row = dict(zip(cols, f, strict=True))
        if row["CPU"] != "-1":
            continue
        end = clock(row["timestamp"])
        out.append(
            (end, int(row["interval"]), float(row["%nice"]), float(row["%idle"]))
        )
    return out


def samples(paths: list[str]) -> list[tuple[float, int, float, float]]:
    # sadf -t (sysstat 12.6.1) takes the time of day from the host's clock but the date from the runner's zone, so
    # it runs in the host's zone, given as its rules: no tz database needed.
    env = {**os.environ, "TZ": HOST_TZ}
    got = set()
    for p in paths:
        cmd = ["sadf", "-d", "-t", p, "--", "-u"]
        got.update(parse_sadf(subprocess.run(cmd, capture_output=True, text=True, check=True, env=env).stdout))  # fmt: skip
    return sorted(got)


def cycle_load(start: str, table: list[tuple], span: int = SPAN) -> dict | None:
    """Time-weighted busy and %nice over [start, start + span); None when samples cover less than COVERED of it."""
    t = np.array(table, dtype=float).reshape(-1, 4)
    t0 = clock(start)
    w = np.clip(np.minimum(t[:, 0], t0 + span) - np.maximum(t[:, 0] - t[:, 1], t0), 0, None)  # fmt: skip
    if w.sum() < COVERED * span:
        return None
    return {"busy": float(100 - w @ t[:, 3] / w.sum()), "nice": float(w @ t[:, 2] / w.sum())}  # fmt: skip


def cycles(record: dict, table: list[tuple]) -> dict:
    got, uncovered = [], []
    for r in sorted(record["rows"], key=lambda r: r["start"]):
        load = cycle_load(r["start"], table)
        if load is None:
            uncovered.append(r["start"])
        else:
            got.append({"start": r["start"], "tweak": r["tweak"], **load})
    return {"span_s": SPAN, "covered": COVERED, "cycles": got, "uncovered": uncovered}


def _joined(rows: list[dict], load: dict) -> list[dict]:
    by_start = {c["start"]: c for c in load["cycles"]}
    out = []
    for r in rows:
        c = by_start.get(r["start"])
        if c is not None:
            if c["tweak"] != r["tweak"]:
                raise SystemExit(
                    f"{r['start']}: the load table's tweak is not the record's"
                )
            out.append(dict(r, busy=c["busy"], nice=c["nice"]))
    return out


def deviations(rows: list[dict], leave_out=(STANDING,)) -> list[dict]:
    """Steps, load and measures minus each tweak x epoch group's means. Groups of one are dropped."""
    groups = defaultdict(list)
    for r in rows:
        if r["tweak"] not in leave_out:
            groups[r["tweak"], r["epoch"]].append(r)
    keys = ("steps", "busy", "nice", *MEASURES)
    out = []
    for (tweak, epoch), members in groups.items():
        if len(members) < 2:
            continue
        mean = {k: np.mean([r[k] for r in members]) for k in keys}
        for r in members:
            d = {k: r[k] - mean[k] for k in keys}
            out.append(dict(d, group=f"{tweak}@{epoch}", day=r["start"][:10]))
    return out


def _col(dev, k):
    return np.array([d[k] for d in dev], dtype=float)


def _fit(y, X, df):
    """Least squares through the origin: coefficients and their standard errors."""
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    se = np.sqrt(np.diag(e @ e / df * np.linalg.inv(X.T @ X)))
    return b, se


def _iv(x, z, y):
    """Steps slope per 100 steps, with busy as the steps' instrument."""
    return float((z @ y) / (z @ x) * 100)


def _resampled(dev, y, key, n, rng) -> list[float]:
    """95% interval of the instrumented slope with whole groups (or days) resampled."""
    x, z = _col(dev, "steps"), _col(dev, "busy")
    labels = np.array([d[key] for d in dev])
    units = np.unique(labels)
    rows_of = [np.where(labels == u)[0] for u in units]
    draws = []
    for _ in range(n):
        idx = np.concatenate([rows_of[j] for j in rng.integers(0, len(units), len(units))])  # fmt: skip
        draws.append(_iv(x[idx], z[idx], y[idx]))
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def _gap(rows: list[dict], key: str, standing: str = STANDING) -> dict:
    """Each standing cycle's `key` minus its epoch's other cycles' mean (UAMT off and batch 16 left out): the mean and
    its standard error."""
    by_epoch = defaultdict(list)
    for r in rows:
        if r["tweak"] not in (standing, *svr.OTHER_STEP_COSTS):
            by_epoch[r["epoch"]].append(r[key])
    g = np.array([r[key] - np.mean(by_epoch[r["epoch"]]) for r in rows if r["tweak"] == standing])  # fmt: skip
    mean = float(g.mean()) if len(g) else None
    se = float(g.std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 else None
    return {"mean": mean, "se": se, "n": len(g)}


def analyse(record: dict, load: dict, bootstraps=BOOTSTRAPS, seed=SEED) -> dict:
    rows = record["rows"]
    if max(r["start"] for r in rows) >= ltr.REGISTERED["since"]:
        raise SystemExit("the record reaches into the confirmation's window")
    joined = _joined(rows, load)
    dev = deviations(joined)
    n, groups = len(dev), len({d["group"] for d in dev})
    x, z = _col(dev, "steps"), _col(dev, "busy")
    (b,), (se,) = _fit(x, z[:, None], n - groups - 1)
    first = {
        "steps_per_busy_point": float(b),
        "se": float(se),
        "F": float((b / se) ** 2),
        "within_r2": float(1 - ((x - b * z) @ (x - b * z)) / (x @ x)),
    }
    bn, sn = _fit(x, np.column_stack([z, _col(dev, "nice")]), n - groups - 2)
    first["with_nice"] = {"busy": float(bn[0]), "nice": float(bn[1]), "se": sn.tolist()}  # fmt: skip
    left = x - b * z  # the part of the steps that load leaves
    rng = np.random.default_rng(seed)
    measures = {}
    for m in MEASURES:
        y = _col(dev, m)
        (bo,), (so,) = _fit(y, x[:, None] / 100, n - groups - 1)
        bj, sj = _fit(y, np.column_stack([x / 100, z]), n - groups - 2)
        measures[m] = {
            "per_100_steps": float(bo),
            "se": float(so),
            "instrumented": _iv(x, z, y),
            "instrumented_groups95": _resampled(dev, y, "group", bootstraps, rng),
            "instrumented_days95": _resampled(dev, y, "day", bootstraps, rng),
            "left_by_load": float((left @ y) / (left @ left) * 100),
            "beside": {
                "per_100_steps": float(bj[0]),
                "per_busy_point": float(bj[1]),
                "per_busy_point_se": float(sj[1]),
                "per_busy_sd": float(bj[1] * z.std(ddof=1)),
                "per_busy_sd95": [
                    float((bj[1] + q * 1.96 * sj[1]) * z.std(ddof=1)) for q in (-1, 1)
                ],
                "through_steps_per_busy_sd": float(bo * b / 100 * z.std(ddof=1)),
            },
        }
    return {
        "cycles": len(rows),
        "with_load": len(joined),
        "deviations": n,
        "groups": groups,
        "days": len({d["day"] for d in dev}),
        "steps_sd": float(x.std(ddof=1)),
        "busy_sd": float(z.std(ddof=1)),
        "nice_sd": float(_col(dev, "nice").std(ddof=1)),
        "bootstraps": bootstraps,
        "seed": seed,
        "first_stage": first,
        "measures": measures,
        "standing": {
            "tweak": STANDING,
            "cycles": sum(r["tweak"] == STANDING for r in joined),
            "busy_gap": _gap(joined, "busy"),
            "nice_gap": _gap(joined, "nice"),
            "busy_gap_by_other_step_costs": {
                t: _gap(joined, "busy", t) for t in svr.OTHER_STEP_COSTS
            },
        },
    }


def window(confirmation: dict, load: dict) -> dict:
    """The window's cycles' load, cut at the 8th standing cycle as the confirmation's verdict is."""
    reg = ltr.REGISTERED
    rows = sorted(confirmation["rows"], key=lambda r: r["start"])
    standing = [j for j, r in enumerate(rows) if r["tweak"] == reg["standing"]]
    if len(standing) > reg["cut_at"]:
        rows = rows[: standing[reg["cut_at"] - 1] + 1]
    joined = _joined(rows, load)
    side = defaultdict(lambda: [0, 0])
    for r in joined:
        side[r["tweak"]][0] += r["nice"] >= SIDE_JOB_NICE
        side[r["tweak"]][1] += 1
    mine = [r for r in joined if r["tweak"] == reg["standing"]]
    rest = [r for r in joined if r["tweak"] != reg["standing"]]
    return {
        "cycles": len(rows),
        "without_load": len(rows) - len(joined),
        "busy_gap": _gap(joined, "busy", reg["standing"]),
        "nice_gap": _gap(joined, "nice", reg["standing"]),
        "side_job_nice": SIDE_JOB_NICE,
        "standing_with_side_job": [
            sum(r["nice"] >= SIDE_JOB_NICE for r in mine),
            len(mine),
        ],
        "others_with_side_job": [
            sum(r["nice"] >= SIDE_JOB_NICE for r in rest),
            len(rest),
        ],
        "by_tweak": {k: side[k] for k in sorted(side)},
        "standing_cycles": [{k: r[k] for k in ("start", "busy", "nice")} for r in mine],
    }


def _source(path: str) -> dict:
    return {"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cycles", help="each cycle's load, from sysstat files")
    c.add_argument("--record", required=True)
    c.add_argument("--sysstat", nargs="+", required=True)
    a = sub.add_parser("analyse", help="the pre-window analysis")
    a.add_argument("--record", required=True)
    a.add_argument("--load", required=True)
    w = sub.add_parser("window", help="at the readout: the window's cycles' load")
    w.add_argument("--confirmation", required=True)
    w.add_argument("--load", required=True)
    for p in (c, a, w):
        p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "cycles":
        out = {"source": _source(args.record), "sysstat": [_source(p) for p in args.sysstat]}  # fmt: skip
        out.update(cycles(json.loads(Path(args.record).read_text()), samples(args.sysstat)))  # fmt: skip
    elif args.cmd == "analyse":
        out = {"source": _source(args.record), "load": _source(args.load)}
        out.update(analyse(json.loads(Path(args.record).read_text()), json.loads(Path(args.load).read_text())))  # fmt: skip
    else:
        out = {"source": _source(args.confirmation), "load": _source(args.load)}
        out.update(window(json.loads(Path(args.confirmation).read_text()), json.loads(Path(args.load).read_text())))  # fmt: skip
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
