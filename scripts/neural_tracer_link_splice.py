"""Registered (docs/preregistration/2026-11-05_neural_tracer_link_splice.md): villa's neural volume tracer writes each
fiber once, "small overlaps kept for joining", and records for each written piece the fibers its two ends touch
('links'), "so overlapping pieces of one fiber can be joined later". Nothing in villa joins them. If each piece were
spliced to the fiber whose end it overlaps, how would continuity (ScrollGT's merge-penalized ERL, ERLpen) and wrong
connections (merges) move on the held-out cubes?

Reads findings 97's and 98's runs and ScrollGT's fiber targets, as findings 101 and 102 did. No tracing, CPU only.
Per cube and tolerance τ, every score is ScrollGT's `score_tracing` at tolerance 0 on the run's labels grown at τ:

* base: as written;
* splice: each chain of spliced pieces takes one label (the rule: `splice_candidates`, `choose_splices`);
* all (sensitivity): every recorded link joined, chains or not.

The verdict reads the ten held-out cubes. Writes reports/neural_tracer_link_splice.json.

Usage: .venv/bin/python scripts/neural_tracer_link_splice.py [--cubes C ...] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_confidence_stops as cs  # noqa: E402
import neural_tracer_ct_context as ctx  # noqa: E402

HELD_OUT, IN_SAMPLE, ALL = cs.HELD_OUT, cs.IN_SAMPLE, cs.ALL
TOLS = (2.0, 4.0)
SPLICE_ARC = 32.0  # cube voxels from the linked fiber's nearer end
KTAN = 4  # points spanned by an end's direction
GAIN_BAR = 0.10  # the strategy's 10% useful-continuity bar
MERGE_SLACK = 0.05  # summed held-out merges may rise by at most 5%
WRONG_SHARE = 0.05  # splices joining two different reference fibers, of those whose pieces both touch one
FIELDS = ("erl", "erl_merge_penalized", "erl_covered", "erl_merge_penalized_covered", "coverage", "splits",
          "merges", "merged_instances", "gt_length", "n_gt_fibers")  # fmt: skip


def arclength(q: np.ndarray) -> np.ndarray:
    return np.concatenate(
        [[0.0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
    )


def splice_candidates(
    fibers: dict, meta: dict, arc_limit: float = SPLICE_ARC
) -> tuple[list[tuple], int]:
    """(distance, P, P's end, Q, Q's nearer end) for each recorded link of piece P's end (0: first point, 1: last) to
    fiber Q where P's end lies within `arc_limit` (registered: SPLICE_ARC) voxels of arclength of Q's nearer end and P,
    leaving that end, heads into Q; and the number of links to a fiber the run does not hold."""
    out, missing = [], 0
    for p_id in sorted(meta):
        _, links = meta[p_id]
        p = fibers[p_id]
        for end, q_id in zip((0, 1), links, strict=False):
            if q_id < 0:
                continue
            if q_id not in fibers or q_id == p_id:
                missing += q_id not in fibers
                continue
            q = fibers[q_id]
            arc = arclength(q)
            x = p[0] if end == 0 else p[-1]
            dist = np.linalg.norm(q - x, axis=1)
            j = int(np.argmin(dist))
            q_end = 0 if arc[j] <= arc[-1] - arc[j] else 1
            if min(arc[j], arc[-1] - arc[j]) > arc_limit:
                continue
            k = min(KTAN, len(p) - 1)
            leaving = (p[0] - p[k]) if end == 0 else (p[-1] - p[-1 - k])
            inward = q[min(j + KTAN, len(q) - 1)] if q_end == 0 else q[max(j - KTAN, 0)]
            if float(leaving @ (inward - q[j])) <= 0:
                continue
            out.append((float(dist[j]), p_id, end, q_id, q_end))
    return out, missing


def choose_splices(candidates: list[tuple]) -> list[tuple[int, int, int, int]]:
    """(P, P's end, Q, Q's end), nearest first: a splice uses two fiber ends, each end at most once, and never closes a
    ring, so every chain of spliced pieces is one polyline."""
    parent: dict = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    used, out = set(), []
    for _, a, ea, b, eb in sorted(candidates):
        if (a, ea) in used or (b, eb) in used:
            continue
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        parent[max(ra, rb)] = min(ra, rb)
        used |= {(a, ea), (b, eb)}
        out.append((a, ea, b, eb))
    return out


def relabel(grown: np.ndarray, pairs) -> np.ndarray:
    """Each pair's two labels, and everything joined to them, take the smallest of them."""
    n = int(grown.max()) + 1
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return np.array([find(x) for x in range(n)], dtype=grown.dtype)[grown]


def covers(gt, grown, fiber_runs) -> dict:
    """label -> the reference fibers its runs cover (ScrollGT's runs, as findings 101 and 102 count merges)."""
    per: dict = {}
    for gi, fiber in enumerate(gt.fibers):
        runs, _, _, _ = fiber_runs(fiber, grown, cs.STEP, True)
        for lab, _ in runs:
            per.setdefault(int(lab), set()).add(gi)
    return per


def kinds(pairs, cov: dict) -> dict:
    """same: the two labels cover a reference fiber in common; different: each covers some, none in common;
    unknown: one covers none."""
    out: Counter = Counter()
    for a, b in pairs:
        sa, sb = cov.get(a, set()), cov.get(b, set())
        out[
            "unknown" if not sa or not sb else ("same" if sa & sb else "different")
        ] += 1
    return {k: out.get(k, 0) for k in ("same", "different", "unknown")}


def chain_problems(
    splices: list[tuple[int, int, int, int]], candidates: list[tuple]
) -> list[str]:
    """Gate 4: every splice is a candidate's, joins two distinct fibers, uses each fiber end at most once, and the
    splices form a forest."""
    allowed = {tuple(c[1:]) for c in candidates}
    problems, used, parent = [], Counter(), {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    for a, ea, b, eb in splices:
        if (a, ea, b, eb) not in allowed or a == b:
            problems.append("not_a_candidate")
            continue
        used[(a, ea)] += 1
        used[(b, eb)] += 1
        ra, rb = find(a), find(b)
        if ra == rb:
            problems.append("ring")
        parent[max(ra, rb)] = min(ra, rb)
    if any(v > 1 for v in used.values()):
        problems.append("end_reused")
    return problems


def measure_cube(
    c: str, score, dilate, fiber_runs, load_fiber_target, recorded: dict
) -> tuple[dict, list[str]]:
    size = int(c.rsplit("_", 1)[1])
    run = cs.RUNS[size] / c
    skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{c}")
    afv = afv_to_labels.read_afv(run / "fibers.afv")
    meta, problems = cs.read_meta(run, afv)
    lab = ctx.labels_of_fibers(afv, cs.MARGIN, size)
    for tol in TOLS:
        problems += [
            f"tol{int(tol)}:{p}"
            for p in cs.gate_problems(score(skel, lab, tol).as_row(), recorded[tol])
        ]
    fibers = {k: afv_to_labels.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in afv.items()}
    id2lab = {fid: rank + 1 for rank, fid in enumerate(sorted(afv))}
    candidates, missing = splice_candidates(fibers, meta)
    splices = choose_splices(candidates)
    problems += chain_problems(splices, candidates)
    links = [
        (k, q)
        for k, (_, ls) in meta.items()
        for q in ls
        if q >= 0 and q in fibers and q != k
    ]
    pairs = {
        "splice": [(id2lab[a], id2lab[b]) for a, _, b, _ in splices],
        "all": [(id2lab[a], id2lab[b]) for a, b in links],
    }
    out: dict = {"pieces": len(afv), "links": len(links), "missing_targets": missing, "candidates": len(candidates),
                 "splices": len(splices)}  # fmt: skip
    for tol in TOLS:
        t = f"tol{int(tol)}"
        grown = dilate(lab, tol)
        base = score(skel, grown, 0.0).as_row()
        problems += [
            f"{t}:row:{f}" for f in FIELDS if base.get(f) != recorded[tol].get(f)
        ]
        cov = covers(skel, grown, fiber_runs)
        out[t] = {
            "base": {f: base[f] for f in FIELDS},
            "kinds": {name: kinds(p, cov) for name, p in pairs.items()},
        }
        for name, p in pairs.items():
            row = score(skel, relabel(grown, p), 0.0).as_row()
            out[t][name] = {f: row[f] for f in FIELDS}
            if row["coverage"] != base["coverage"]:
                problems.append(f"{t}:{name}:coverage")
        b = base["erl_merge_penalized"]
        for name in pairs:
            out[t][name]["gain"] = (
                out[t][name]["erl_merge_penalized"] / b - 1 if b > 0 else None
            )
        del grown
    return out, problems


def verdict(per_cube: dict, gate: dict) -> dict:
    """per_cube: cube -> measure_cube's record; gate: cube -> its problems."""
    if any(gate.get(c) for c in gate):
        return {"status": "GATE_FAILED", "gate": {c: v for c, v in gate.items() if v}}
    if any(c not in per_cube for c in HELD_OUT):
        return {"status": "PARTIAL"}
    rows = [per_cube[c] for c in HELD_OUT]
    gains = {t: [r[t]["splice"]["gain"] for r in rows] for t in ("tol2", "tol4")}
    if any(g is None for v in gains.values() for g in v):
        return {"status": "NO_BASELINE", "gains": gains}
    median = {t: statistics.median(v) for t, v in gains.items()}
    merges = {k: sum(r["tol2"][k]["merges"] for r in rows) for k in ("base", "splice")}
    sk = Counter()
    for r in rows:
        sk.update(r["tol2"]["kinds"]["splice"])
    known = sk["same"] + sk["different"]
    wrong = sk["different"] / known if known else None
    p = {
        "P1": median["tol2"] >= GAIN_BAR,
        "P2": merges["splice"] <= (1 + MERGE_SLACK) * merges["base"],
        "P3": median["tol4"] >= GAIN_BAR,
        "P4": wrong is not None and wrong <= WRONG_SHARE,
    }
    if not p["P2"]:
        decision = "COSTS_MERGES"
    elif p["P1"]:
        decision = "SUPPORTED"
    elif p["P3"]:
        decision = "SUPPORTED_AT_TOL4_ONLY"
    else:
        decision = "NOT_SUPPORTED"
    return {"status": "OK", "decision": decision, "predictions": p, "median_gain": median, "gains": gains,
            "merges_tol2": merges, "splice_kinds_tol2": dict(sk), "wrong_share_tol2": wrong}  # fmt: skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--cubes", nargs="*", help="a subset (a smoke); the verdict then reads PARTIAL"
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_link_splice.json")
    )
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists: the record is written once")
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import (
        SCORING_VERSION,
        _dilate_labels,
        _fiber_runs,
        score_tracing,
    )
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )

    def score(gt, vol, tol):
        return score_tracing(gt, vol, tolerance=tol)

    recorded = {}
    for path in cs.RECORDED.values():
        d = json.loads(path.read_text())
        for c in d["rows_tol2"]:
            recorded[c] = {2.0: d["rows_tol2"][c], 4.0: d["rows_tol4"][c]}
    cubes = args.cubes or HELD_OUT + IN_SAMPLE
    per_cube, gate, skeletons = {}, {}, {}
    for n, c in enumerate(cubes, 1):
        t0 = time.time()
        skeletons[c] = hashlib.sha256(
            (f91.SG / "data" / f"fibers_{c}" / "skeleton.npz").read_bytes()
        ).hexdigest()
        per_cube[c], gate[c] = measure_cube(
            c, score, _dilate_labels, _fiber_runs, load_fiber_target, recorded[c]
        )
        g = per_cube[c]["tol2"]["splice"]["gain"]
        print(f"[{n}/{len(cubes)}] {c}: gate {gate[c] or 'ok'}; {per_cube[c]['splices']} splices; "
              f"tol2 gain {g if g is None else round(g, 3)}; {time.time() - t0:.0f} s", flush=True)  # fmt: skip
    v = (
        verdict(per_cube, gate)
        if not args.cubes
        else {"status": "PARTIAL", "smoke_of": cubes}
    )
    sg_commit = subprocess.run(["git", "-C", str(f91.SG), "rev-parse", "HEAD"], capture_output=True, text=True,
                               check=True).stdout.strip()  # fmt: skip
    summary = {}
    for name, members in (("held_out", HELD_OUT), ("in_sample", IN_SAMPLE)):
        rows = [per_cube[c] for c in members if c in per_cube]
        summary[name] = (
            {
                t: {
                    p: statistics.median(r[t][p]["gain"] for r in rows)
                    for p in ("splice", "all")
                }
                for t in ("tol2", "tol4")
            }
            if rows
            and all(  # fmt: skip
                r[t][p]["gain"] is not None
                for r in rows
                for t in ("tol2", "tol4")
                for p in ("splice", "all")
            )
            else None
        )
    out = {
        "registration": "docs/preregistration/2026-11-05_neural_tracer_link_splice.md",
        "verdict": v,
        "gate": gate,
        "settings": {
            "tols": list(TOLS),
            "splice_arc": SPLICE_ARC,
            "ktan": KTAN,
            "gain_bar": GAIN_BAR,
            "merge_slack": MERGE_SLACK,
            "wrong_share": WRONG_SHARE,
        },  # fmt: skip
        "summary_median_gain": summary,
        "per_cube": per_cube,
        "inputs": {
            "scrollgt_commit": sg_commit,
            "scoring_version": SCORING_VERSION,
            "skeleton_sha256": skeletons,
            "runs": {str(k): str(p) for k, p in cs.RUNS.items()},
        },  # fmt: skip
    }
    args.out.write_text(json.dumps(out, indent=1) + "\n")
    print(f"{v['status']} {v.get('decision', '')} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
