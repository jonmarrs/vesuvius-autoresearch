"""Registered (docs/preregistration/2026-11-01_neural_tracer_continuity_ceiling.md): finding 101's continuity
question. If villa's neural tracer went on from each confidence stop where the hand-traced fiber goes on, how much
could ScrollGT's merge-penalized ERL (ERLpen) rise?

Reads findings 97's and 98's runs and ScrollGT's fiber targets, as finding 101 did. No tracing, CPU only. For each
cube and tolerance τ:

* the stops and gaps are finding 101's (`confidence`, unlinked, EDGE from every face, on the reference, continuing L
  voxels): the uncovered samples past each stop, up to the next trace (a split), the fiber's end, the face or CAP;
* every edit acts on the run's labels grown at τ, and every score is ScrollGT's `score_tracing` at tolerance 0;
* fill: each gap sample's voxel takes the stopping trace's label (the first stop in fiber-id order wins a voxel);
  join: a split's two traces take one label;
* the ceiling U: traces that merge at baseline zeroed, the other stops' gaps filled, splits joined where neither trace
  merges, scored by ERL. U bounds the ERLpen of any rule that goes on from these stops along the right fiber, no
  farther than the next trace;
* beside it, two rules a tracer could follow, scored by ERLpen: fill, and fill and join; and U_k, continuation
  bounded to k voxels.

The verdict reads the ten held-out cubes at τ = 2. Writes reports/neural_tracer_continuity_ceiling.json.

Usage: .venv/bin/python scripts/neural_tracer_continuity_ceiling.py [--cubes C ...] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_confidence_stops as cs  # noqa: E402
import neural_tracer_ct_context as ctx  # noqa: E402

HELD_OUT, IN_SAMPLE, ALL, UNSEEN_SCROLLS = (
    cs.HELD_OUT,
    cs.IN_SAMPLE,
    cs.ALL,
    cs.UNSEEN_SCROLLS,
)
TOL, L, EDGE, STEP = cs.TOL, cs.L, cs.EDGE, cs.STEP
TOLS = (2.0, 4.0)
KS = (10.0, 20.0, 50.0)
GAIN_BAR = 0.10  # the strategy's 10% useful-continuity bar
P3_FRACTION = 0.5
COVERED_SLACK = (0.05, 10.0)  # gate 5: relative, voxels; the larger applies
FINDING_101 = Path("reports/neural_tracer_confidence_stops.json")
ROW_FIELDS = ("erl", "erl_merge_penalized", "erl_covered", "erl_merge_penalized_covered", "coverage", "splits",
              "merges", "merged_instances", "gt_length", "n_gt_fibers")  # fmt: skip
# a <= b, each checked where both were scored
BOUNDS = (("base", "U_fill"), ("U_fill", "U"), ("base", "U"), ("fill", "U"), ("fill_join", "U"), ("U_10", "U"),
          ("U_20", "U"), ("U_50", "U"), ("U_10", "U_20"), ("U_20", "U_50"))  # fmt: skip
READINGS = {
    "close": "Even perfect continuation from the tracer's confidence stops, joining every split it could join without "
    "a merge, would raise the median held-out cube's ERLpen by under 10%. With finding 101, close premature confidence "
    "stops for this tracer, checkpoint and settings, for coverage and continuity alike.",
    "open": "The line stays open as a continuity lever: a development-pilot proposal for a continuation rule, judged "
    "by ERLpen and wrong connections against the stock tracer, needs the owner's GPU decision.",
}


def continuation(walked: list, own: int) -> tuple[dict, int, float | None]:
    """Past a stop: the uncovered samples (key -> (length, arclength from the stop)), skipping the stopping trace's own
    label, up to the first sample another trace covers; that trace's label (0 if none) and the arclength there."""
    keys: dict = {}
    s = 0.0
    for key, lab, dl in walked:
        s += dl
        if lab == 0:
            keys[key] = (dl, s)
        elif lab != own:
            return keys, lab, s
    return keys, 0, None


def voxel(ref, key) -> tuple[int, int, int]:
    """The voxel ScrollGT reads for a walk's sample key."""
    if key[0] == "n":
        p = ref.coords[key[1]][key[2]]
    else:
        _, k, jj = key
        a, b = ref.nodes[k]
        c = ref.coords[ref.fiber[k]]
        p = c[a] + (c[b] - c[a]) * (jj / (ref.n[k] - 1))
    z, y, x = (int(v) for v in np.rint(p))
    return z, y, x


def record(ref, walked: list, own: int) -> dict:
    keys, other, at = continuation(walked, own)
    return {"own": own, "keys": {k: (dl, s, voxel(ref, k)) for k, (dl, s) in keys.items()}, "other": other,
            "at": at}  # fmt: skip


def confidence_gaps(ref, grown, fibers, meta, size, tol) -> list[dict]:
    """Finding 101's continuing confidence stops at `tol`, in its order (fiber id, then end), each with its gap."""
    own = {fid: rank + 1 for rank, fid in enumerate(sorted(fibers))}
    out = []
    for fid in sorted(fibers):
        reasons, links = meta[fid]
        for e in cs.stops(fibers[fid], reasons, links, size):
            if (
                e["reason"] != "confidence"
                or e["link"] >= 0
                or e["face_distance"] < EDGE
            ):
                continue
            d, i = ref.tree.query(e["point"])
            if d > tol:
                continue
            k, j = (int(v) for v in ref.keys[i])
            walked, why = ref.walk(k, j, cs.sign_along(ref, k, e["direction"]), grown)
            if (
                cs.classify(float(sum(dl for _, _, dl in walked)), why, L)
                == "continues"
            ):
                out.append(record(ref, walked, own[fid]))
    return out


def merging_labels(gt, grown, fiber_runs, step=STEP) -> frozenset:
    """The traces whose runs cover more than one reference fiber: the ones ScrollGT's ERLpen zeroes."""
    per: dict[int, set] = {}
    for gi, fiber in enumerate(gt.fibers):
        runs, _, _, _ = fiber_runs(fiber, grown, step, True)
        for lab, _ in runs:
            per.setdefault(lab, set()).add(gi)
    return frozenset(lab for lab, v in per.items() if len(v) > 1)


def edited(
    grown, recs, *, join=True, fill=True, zero=frozenset(), k=None
) -> np.ndarray:
    """`grown` with the stops' gaps filled with their own trace's label and each split's two traces joined; traces in
    `zero` set to 0 and neither filled nor joined; with `k`, only within k voxels of the stop."""
    out = grown.copy()
    n = int(grown.max()) + 1
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for r in recs:
        own = r["own"]
        if own in zero:
            continue
        if fill:
            for _, s, v in r["keys"].values():
                if (k is None or s <= k) and out[v] == 0:
                    out[v] = own
        other = r["other"]
        if join and other and other not in zero and (k is None or r["at"] <= k):
            a, b = find(own), find(other)
            if a != b:
                parent[max(a, b)] = min(a, b)
    lut = np.array([find(x) for x in range(n)], dtype=grown.dtype)
    lut[sorted(zero)] = 0
    return lut[out]


def _row(scores, value: str) -> dict:
    return {"value": float(getattr(scores, value)), "erl": scores.erl, "erl_merge_penalized": scores.erl_merge_penalized,
            "coverage": scores.coverage, "covered": scores.coverage * scores.gt_length, "splits": scores.splits,
            "merges": scores.merges, "merged_instances": scores.merged_instances}  # fmt: skip


def ceiling(gt, grown, recs, score, fiber_runs, ks=KS, full=True) -> dict:
    """Every policy scored on one cube's grown labelling. score(gt, labelling): ScrollGT's score_tracing at tolerance 0.
    full=False scores only the baseline, U with no edits, U, and fill and join (the τ = 4 sensitivity)."""
    zero = merging_labels(gt, grown, fiber_runs)
    base = score(gt, grown)
    plans: dict[str, tuple[list, dict, str]] = {"U_none": ([], {"zero": zero}, "erl"), "U": (recs, {"zero": zero}, "erl"),
             "fill_join": (recs, {}, "erl_merge_penalized")}  # fmt: skip
    if full:
        plans.update({"U_fill": (recs, {"zero": zero, "join": False}, "erl"),
                      "fill": (recs, {"join": False}, "erl_merge_penalized")})  # fmt: skip
        plans.update({f"U_{int(k)}": (recs, {"zero": zero, "k": k}, "erl") for k in ks})
    out = {
        "base": _row(base, "erl_merge_penalized"),
        "row": base.as_row(),
        "merging": len(zero),
    }
    for name, (rs, kw, value) in plans.items():
        vol = edited(grown, rs, **kw)
        out[name] = _row(score(gt, vol), value)
        del vol
    b = out["base"]["value"]
    for name in ["base", *plans]:
        out[name]["gain"] = out[name]["value"] / b - 1 if b > 0 else None
    union: dict = {}
    for r in recs:
        union.update({key: dl for key, (dl, _, _) in r["keys"].items()})
    out["union_length"] = float(sum(union.values()))
    out["misaligned"] = sum(
        int(grown[v] != 0) for r in recs for _, _, v in r["keys"].values()
    )
    out["counts"] = {
        "stops": len(recs),
        "splits": sum(bool(r["other"]) for r in recs),
        "joins_unmerged": sum(
            bool(r["other"]) and r["own"] not in zero and r["other"] not in zero
            for r in recs
        ),
        "own_merging": sum(r["own"] in zero for r in recs),
        "other_merging": sum(bool(r["other"]) and r["other"] in zero for r in recs),
    }
    return out


def bound_problems(out: dict) -> list[str]:
    return [f"{a} <= {b}" for a, b in BOUNDS
            if a in out and b in out and out[a]["value"] > out[b]["value"] + 1e-12 * max(1.0, abs(out[b]["value"]))]  # fmt: skip


def check_problems(
    out: dict, row: dict, recorded: dict, merging: int, filled: str
) -> list[str]:
    """Gate checks 2-6 for one cube and τ. row: ScrollGT's row of the unedited grown labelling at tolerance 0;
    recorded: the recorded τ row, plus finding 101's `gap_length`; filled: the policy whose coverage shows the fill."""
    problems = [f"row:{f}" for f in ROW_FIELDS if row.get(f) != recorded.get(f)]
    if merging != recorded["merged_instances"]:
        problems.append("merging")
    if out["U_none"]["value"] != out["base"]["value"]:
        problems.append("U_none")
    union = out["union_length"]
    if not math.isclose(union, recorded["gap_length"], rel_tol=1e-9, abs_tol=1e-9):
        problems.append("union_length")
    if out["misaligned"]:
        problems.append("misaligned")
    rise = out[filled]["covered"] - out["base"]["covered"]
    if abs(rise - union) > max(COVERED_SLACK[0] * union, COVERED_SLACK[1]):
        problems.append("covered")
    return problems + bound_problems(out)


def verdict(cubes: dict, gate: dict) -> dict:
    """cubes: cube -> {U, U_20, fill_join}: the gains at τ = 2; gate: cube -> its problems."""
    if set(gate) != set(ALL) or any(gate[c] for c in gate):
        return {"status": "GATE_FAILED", "gate": {c: gate.get(c) for c in ALL}}
    if any(
        c not in cubes
        or any(cubes[c].get(k) is None for k in ("U", "U_20", "fill_join"))
        for c in HELD_OUT
    ):
        return {"status": "PARTIAL"}
    u = [cubes[c]["U"] for c in HELD_OUT]
    m, m20, mj = (
        statistics.median(cubes[c][k] for c in HELD_OUT)
        for k in ("U", "U_20", "fill_join")
    )
    p1, p2, p3 = m >= GAIN_BAR, m20 >= GAIN_BAR, mj >= P3_FRACTION * m
    decision = "open" if p1 else "close"
    return {"status": "OK", "median_U": m, "U_range": [min(u), max(u)], "median_U_20": m20, "median_fill_join": mj,
            "P1": p1, "P2": p2, "P3": p3, "decision": decision, "reading": READINGS[decision]}  # fmt: skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--cubes", nargs="*", help="a subset (a smoke); the verdict then reads PARTIAL"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/neural_tracer_continuity_ceiling.json"),
    )
    args = ap.parse_args(argv)

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

    def score(gt, vol):
        return score_tracing(gt, vol, tolerance=0.0)

    f101 = json.loads(FINDING_101.read_text())["per_cube"]
    recorded = {}
    for path in cs.RECORDED.values():
        d = json.loads(path.read_text())
        for c in d["rows_tol2"]:
            recorded[c] = {2.0: d["rows_tol2"][c], 4.0: d["rows_tol4"][c]}
    cubes = args.cubes or ALL
    gate, per_cube, skeletons = {}, {}, {}
    for n, c in enumerate(cubes, 1):
        t0 = time.time()
        size = int(c.rsplit("_", 1)[1])
        run = cs.RUNS[size] / c
        target = f91.SG / "data" / f"fibers_{c}"
        skeletons[c] = hashlib.sha256(
            (target / "skeleton.npz").read_bytes()
        ).hexdigest()
        skel, _, _ = load_fiber_target(target)
        afv = afv_to_labels.read_afv(run / "fibers.afv")
        meta, problems = cs.read_meta(run, afv)
        lab = ctx.labels_of_fibers(afv, cs.MARGIN, size)
        problems += cs.gate_problems(
            score_tracing(skel, lab, tolerance=TOL).as_row(), recorded[c][TOL]
        )
        fibers = {
            k: afv_to_labels.to_cube_zyx(v, (cs.MARGIN,) * 3) for k, v in afv.items()
        }
        ref = cs.Reference(skel.fibers, size)
        per_cube[c] = {}
        for tol in TOLS:
            t = f"tol{int(tol)}"
            grown = _dilate_labels(lab, tol)
            recs = confidence_gaps(ref, grown, fibers, meta, size, tol)
            full = tol == TOL
            out = ceiling(skel, grown, recs, score, _fiber_runs, full=full)
            want = dict(
                recorded[c][tol],
                gap_length=f101[c][t]["settings"][f"L{int(L)}_edge{int(EDGE)}"][
                    "gap_length"
                ],
            )
            problems += [f"{t}:{p}" for p in check_problems(out, out["row"], want, out["merging"],
                                                           "fill" if full else "fill_join")]  # fmt: skip
            per_cube[c][t] = out
            del grown
        gate[c] = problems
        g = per_cube[c]["tol2"]
        print(f"[{n}/{len(cubes)}] {c}: gate {gate[c] or 'ok'}; U {g['U']['gain']:.3f}; U_20 {g['U_20']['gain']:.3f}; "
              f"fill+join {g['fill_join']['gain']:.3f}; {time.time() - t0:.0f} s", flush=True)  # fmt: skip

    registered = {
        c: {k: v["tol2"][k]["gain"] for k in ("U", "U_20", "fill_join")}
        for c, v in per_cube.items()
    }
    v = (
        verdict(registered, gate)
        if not args.cubes
        else {"status": "PARTIAL", "smoke_of": cubes}
    )
    sets = {
        "held_out": HELD_OUT,
        "in_sample": IN_SAMPLE,
        "unseen_scrolls": UNSEEN_SCROLLS,
    }
    summary = {}
    for name, members in sets.items():
        rows = [per_cube[c] for c in members if c in per_cube]
        summary[name] = {t: {p: {"median_gain": statistics.median(r[t][p]["gain"] for r in rows), "n": len(rows)}
                             for p in rows[0][t] if isinstance(rows[0][t][p], dict) and "gain" in rows[0][t][p]}
                         for t in rows[0]} if rows else None  # fmt: skip
    sg_commit = subprocess.run(["git", "-C", str(f91.SG), "rev-parse", "HEAD"], capture_output=True, text=True,
                               check=True).stdout.strip()  # fmt: skip
    checkpoints = sorted({json.loads((cs.RUNS[int(c.rsplit("_", 1)[1])] / c / "run.json").read_text())["checkpoint"]
                          for c in cubes})  # fmt: skip
    out = {
        "registration": "docs/preregistration/2026-11-01_neural_tracer_continuity_ceiling.md",
        "verdict": v,
        "registered": registered,
        "gate": gate,
        "settings": {
            "tol": TOL,
            "tols": list(TOLS),
            "L": L,
            "edge": EDGE,
            "ks": list(KS),
            "gain_bar": GAIN_BAR,
            "p3_fraction": P3_FRACTION,
            "covered_slack": list(COVERED_SLACK),
        },  # fmt: skip
        "sets": sets,
        "summary": summary,
        "per_cube": per_cube,
        "provenance": {
            "runs": {str(k): "/".join(p.parts[-3:]) for k, p in cs.RUNS.items()},
            "scrollgt_commit": sg_commit,
            "scoring_version": SCORING_VERSION,
            "skeleton_sha256": skeletons,
            "checkpoints": checkpoints,
            "finding_101": str(FINDING_101),
        },  # fmt: skip
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(v, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
