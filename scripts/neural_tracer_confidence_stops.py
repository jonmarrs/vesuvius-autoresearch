"""Registered (docs/preregistration/2026-11-01_neural_tracer_confidence_stops.md): when villa's neural tracer ends a
trace on low confidence, does the hand-traced fiber go on, and how much uncovered fiber lies past those stops?

Reads findings 97's and 98's runs (ccb431818, 128 voxels of CT around each cube) and ScrollGT's fiber targets. No
tracing, CPU only. For each cube:

* the gate: ScrollGT's `score_tracing` on the run's labels at tolerance 2 reproduces the recorded row exactly, and the
  fiber JSONs (stop reasons, links) attach to the `.afv` polylines it scored (same ids, ends within END_AGREEMENT);
* the stops: fiber ends that touch no written fiber (`links` = -1), EDGE voxels or more from every face. villa's
  `_write` cuts a trace to the cube and trims overlaps, and each piece keeps its trace's reasons, so only these ends are
  where a trace stopped. `stop_reasons[0]` is the first point's (the backward half, reversed, comes first);
* for a stop within TOL of the reference: a walk along the matched fiber, in the stop's outward direction, to the
  fiber's end, out of the cube or CAP voxels; its class at L (`continues`, `fiber_ends`, `censored`), and the gap past
  it: the uncovered samples until another trace's label;
* for a stop off the reference: whether the trace's point BACK_LATE voxels back lay on it (it left the fiber first);
* the base rate: BASE_N covered reference samples walked in a random direction by the same rules;
* G: the union of the gaps past `confidence` stops that continue, over the covered length.

The verdict reads the ten held-out cubes at TOL, L and EDGE; the rest is sensitivity. Writes
reports/neural_tracer_confidence_stops.json.

Usage: .venv/bin/python scripts/neural_tracer_confidence_stops.py [--cubes C ...] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import neural_tracer_ct_context as ctx  # noqa: E402

T = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/neural_tracer")
RUNS = {256: T / "ct_context_run" / "neural", 512: T / "ct_context_512_run" / "neural"}
RECORDED = {
    256: Path("reports/neural_tracer_ct_context.json"),
    512: Path("reports/neural_tracer_ct_context_512.json"),
}
# ScrollGT's ten held-out cubes: these decide
HELD_OUT = list(f91.S3) + list(f91.S5_HELDOUT)
IN_SAMPLE = list(f91.IN_SAMPLE)
ALL = HELD_OUT + IN_SAMPLE
# the tracer trained on Scroll 1 only
UNSEEN_SCROLLS = [c for c in ALL if not c.startswith("s1_")]
MARGIN = 128  # CT voxels of context around each cube in findings 97 and 98
TOL = 2.0
L = 20.0
EDGE = 6.0
CAP = 400.0
STEP = 0.5  # ScrollGT's resampling step
BACK_DIRECTION = 8.0
BACK_LATE = 20.0
G_BAR = 0.10  # the strategy's 10% bar
P1_SHARE = 0.5
P2_FACTOR, P2_CUBES = 0.8, 8
BASE_N = 2000
RNG_SEED = 0
END_AGREEMENT = 2.5
LS = (10.0, 20.0, 40.0)
EDGES = (6.0, 12.0)
TOLS = (2.0, 4.0)
GATE_FIELDS = ("coverage", "precision", "splits", "merges", "gt_length", "pred_length")
READINGS = {
    "close": "Even perfect continuation at the tracer's confidence stops would add under 10% to the median held-out "
    "cube's coverage: close the premature-confidence-stop line for this tracer, checkpoint and settings.",
    "open": "The line stays open: a development-pilot proposal for a continuation rule, judged by wrong connections "
    "as well as reach, needs the owner's GPU decision.",
    "mechanism_wrong": "The gap is real, but most on-fiber confidence stops sit where the fiber ends: the mechanism "
    "behind this line is wrong. Propose nothing until the gap is explained.",
}


def _inside(points: np.ndarray, size: int) -> np.ndarray:
    idx = np.rint(points)
    return np.all((idx >= 0) & (idx < size), axis=-1)


class Reference:
    """The ground truth as walkable fibers, every edge resampled as ScrollGT's `_resample_fiber` does."""

    def __init__(self, fibers, size: int, step: float = STEP):
        from scipy.spatial import cKDTree

        self.size = size
        self.coords: list = []  # per fiber: node coordinates
        self.nodes: list = []  # per edge: its two nodes, then its sample count, spacing, direction, fiber
        self.n: list = []
        self.dl: list = []
        self.dir: list = []
        self.fiber: list = []
        self.adj: dict[tuple[int, int], list[tuple[int, int]]] = {}
        pts, keys = [], []
        for fi, f in enumerate(fibers):
            c = np.asarray(f.coords, float)
            self.coords.append(c)
            for a, b in np.asarray(f.edges, int).reshape(-1, 2):
                a, b = int(a), int(b)
                seg = float(np.linalg.norm(c[b] - c[a]))
                k, n = len(self.nodes), max(2, int(np.ceil(seg / step)) + 1)
                self.nodes.append((a, b))
                self.n.append(n)
                self.dl.append(seg / (n - 1))
                self.dir.append((c[b] - c[a]) / seg if seg > 0 else np.zeros(3))
                self.fiber.append(fi)
                self.adj.setdefault((fi, a), []).append((b, k))
                self.adj.setdefault((fi, b), []).append((a, k))
                t = np.linspace(0.0, 1.0, n)[:-1]
                p = c[a] + (c[b] - c[a]) * t[:, None]
                ok = _inside(p, size)
                pts.append(p[ok])
                keys.append(
                    np.stack([np.full(int(ok.sum()), k), np.nonzero(ok)[0]], axis=1)
                )
        self.pts = np.vstack(pts) if pts else np.zeros((0, 3))
        self.keys = np.vstack(keys) if keys else np.zeros((0, 2), int)
        self.tree = cKDTree(self.pts)

    def walk(self, k: int, j: int, sign: int, labels: np.ndarray, cap: float = CAP):
        """(key, label, length) for each sample past sample j of edge k, toward the edge's second node when sign > 0,
        and why the walk ended: 'fiber_end', 'left_cube' or 'cap'. A node is one sample, keyed by the node."""
        fi = self.fiber[k]
        c = self.coords[fi]
        out: list = []
        length = 0.0
        direction = self.dir[k] * sign
        used = {k}
        while True:
            a, b = self.nodes[k]
            n, dl = self.n[k], self.dl[k]
            js = np.arange(j + 1, n) if sign > 0 else np.arange(j - 1, -1, -1)
            p = c[a] + (c[b] - c[a]) * (js / (n - 1))[:, None]
            idx = np.rint(p).astype(int)
            ok = np.all((idx >= 0) & (idx < self.size), axis=1)
            for jj, q, inside in zip(js, idx, ok, strict=True):
                if not inside:
                    return out, "left_cube"
                jj = int(jj)
                key = (
                    ("n", fi, a if jj == 0 else b) if jj in (0, n - 1) else ("e", k, jj)
                )
                length += dl
                out.append((key, int(labels[q[0], q[1], q[2]]), dl))
                if length >= cap:
                    return out, "cap"
            node = b if sign > 0 else a
            nxt = [(m, kk) for m, kk in self.adj[(fi, node)] if kk not in used]
            if not nxt:
                return out, "fiber_end"

            def alignment(edge, node=node, direction=direction):
                v = c[edge[0]] - c[node]
                nv = float(np.linalg.norm(v))
                return (float(np.dot(v / nv, direction)) if nv > 0 else -2.0, -edge[1])

            m, k = max(nxt, key=alignment)
            used.add(k)
            sign = 1 if self.nodes[k][0] == node else -1
            j = 0 if sign > 0 else self.n[k] - 1
            if np.any(self.dir[k]):
                direction = self.dir[k] * sign


def sign_along(ref: Reference, k: int, direction: np.ndarray) -> int:
    """+1 to walk edge k toward its second node, the way `direction` points; -1 otherwise."""
    return 1 if float(np.dot(ref.dir[k], direction)) >= 0 else -1


def classify(length: float, why: str, minimum: float = L) -> str:
    if length >= minimum:
        return "continues"
    return "fiber_ends" if why == "fiber_end" else "censored"


def gap(walked: list, own: int) -> tuple[dict, bool]:
    """The uncovered samples past a stop (key -> length), skipping the stopping fiber's own label, up to the first
    sample another fiber's label covers; and whether one did (a split)."""
    keys: dict = {}
    for key, lab, dl in walked:
        if lab == 0:
            keys[key] = dl
        elif lab != own:
            return keys, True
    return keys, False


def _along(q: np.ndarray, distance: float) -> np.ndarray:
    """The point `distance` voxels of arclength along polyline q from q[0] (q's far end if it is shorter)."""
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
    if s[-1] <= distance:
        return q[-1].copy()
    i = int(np.searchsorted(s, distance, side="right")) - 1
    t = (distance - s[i]) / (s[i + 1] - s[i])
    return q[i] + (q[i + 1] - q[i]) * t


def stops(poly: np.ndarray, reasons, links, size: int) -> list[dict]:
    """Both ends of a written fiber (cube ZYX): point, outward direction, the point BACK_LATE back, reason, link."""
    out = []
    for end in (0, 1):
        q = poly if end == 0 else poly[::-1]
        p = q[0]
        v = p - _along(q, BACK_DIRECTION)
        nv = float(np.linalg.norm(v))
        out.append({"end": end, "point": p, "direction": v / nv if nv > 0 else v, "back": _along(q, BACK_LATE),
                    "reason": str(reasons[end]), "link": int(links[end]),
                    "face_distance": float(min(p.min(), (size - 1 - p).min()))})  # fmt: skip
    return out


def measure_cube(
    ref,
    labels,
    fibers,
    meta,
    size,
    tol,
    covered,
    rng,
    base_n=BASE_N,
    ls=LS,
    edges=EDGES,
) -> dict:
    """Every stop of one cube classified and walked, summarized at each L and EDGE.

    labels: the run's labels grown at `tol`; fibers: id -> cube ZYX polyline; meta: id -> (stop_reasons, links);
    covered: the covered reference length (ScrollGT's coverage x ground-truth length) at `tol`."""
    own = {fid: rank + 1 for rank, fid in enumerate(sorted(fibers))}
    ends = {"linked": 0, "face": 0, "interior": 0}
    records = []
    for fid in sorted(fibers):
        reasons, links = meta[fid]
        for e in stops(fibers[fid], reasons, links, size):
            kind = (
                "linked"
                if e["link"] >= 0
                else ("face" if e["face_distance"] < EDGE else "interior")
            )
            ends[kind] += 1
            if e["link"] >= 0 or e["face_distance"] < min(edges):
                continue
            d, i = ref.tree.query(e["point"])
            rec = {
                "reason": e["reason"],
                "face": e["face_distance"],
                "on": bool(d <= tol),
            }
            if rec["on"]:
                k, j = (int(v) for v in ref.keys[i])
                walked, why = ref.walk(k, j, sign_along(ref, k, e["direction"]), labels)
                rec["length"], rec["why"] = float(sum(dl for _, _, dl in walked)), why
                rec["gap"], rec["split"] = gap(walked, own[fid])
            else:
                rec["left"] = bool(ref.tree.query(e["back"])[0] <= tol)
            records.append(rec)

    at = np.rint(ref.pts).astype(int)
    covered_samples = (
        np.nonzero(labels[at[:, 0], at[:, 1], at[:, 2]])[0]
        if len(at)
        else np.zeros(0, int)
    )
    pick = (rng.choice(covered_samples, size=min(base_n, len(covered_samples)), replace=False)
            if len(covered_samples) else np.zeros(0, int))  # fmt: skip
    signs = rng.choice([-1, 1], size=len(pick))
    base_walks = []
    for i, s in zip(pick, signs, strict=True):
        k, j = (int(v) for v in ref.keys[i])
        walked, why = ref.walk(k, j, int(s), labels)
        base_walks.append((float(sum(dl for _, _, dl in walked)), why))

    settings = {}
    reasons = sorted({r["reason"] for r in records} | {"confidence"})
    for minimum in ls:
        for edge in edges:
            sel = [r for r in records if r["face"] >= edge]
            row: dict = {}
            for reason in reasons:
                rs = [r for r in sel if r["reason"] == reason]
                on = [r for r in rs if r["on"]]
                cls = [classify(r["length"], r["why"], minimum) for r in on]
                row[reason] = {
                    "stops": len(rs),
                    "on_fiber": len(on),
                    "continues": cls.count("continues"),
                    "fiber_ends": cls.count("fiber_ends"),
                    "censored": cls.count("censored"),
                    "splits": sum(
                        r["split"]
                        for r, c in zip(on, cls, strict=True)
                        if c == "continues"
                    ),
                    "off_fiber": len(rs) - len(on),
                    "left_fiber": sum(r["left"] for r in rs if not r["on"]),
                }
            conf = row["confidence"]
            den = conf["continues"] + conf["fiber_ends"]
            union: dict = {}
            for r in sel:
                if (
                    r["reason"] == "confidence"
                    and r["on"]
                    and classify(r["length"], r["why"], minimum) == "continues"
                ):
                    union.update(r["gap"])
            gap_length = float(sum(union.values()))
            row.update(premature_share=conf["continues"] / den if den else None, gap_length=gap_length,
                       G=gap_length / covered if covered > 0 else None)  # fmt: skip
            settings[f"L{int(minimum)}_edge{int(edge)}"] = row
    base = {}
    for minimum in ls:
        cls = [classify(length, why, minimum) for length, why in base_walks]
        den = cls.count("continues") + cls.count("fiber_ends")
        base[f"L{int(minimum)}"] = cls.count("continues") / den if den else None
    return {
        "ends": ends,
        "settings": settings,
        "base_rate": base,
        "base_n": len(base_walks),
        "covered": covered,
    }


def gate_problems(now: dict, recorded: dict) -> list[str]:
    return [f for f in GATE_FIELDS if now.get(f) != recorded.get(f)]


def verdict(cubes: dict, gate: dict) -> dict:
    """cubes: cube -> {G, premature_share, base_rate} at TOL, L and EDGE; gate: cube -> its identity problems."""
    if set(gate) != set(ALL) or any(gate[c] for c in gate):
        return {"status": "GATE_FAILED", "gate": {c: gate.get(c) for c in ALL}}
    need = ("G", "premature_share", "base_rate")
    if any(
        c not in cubes or any(cubes[c].get(k) is None for k in need) for c in HELD_OUT
    ):
        return {"status": "PARTIAL"}
    G = [cubes[c]["G"] for c in HELD_OUT]
    share = [cubes[c]["premature_share"] for c in HELD_OUT]
    p1 = statistics.median(share) >= P1_SHARE
    p2 = (
        sum(
            cubes[c]["premature_share"] >= P2_FACTOR * cubes[c]["base_rate"]
            for c in HELD_OUT
        )
        >= P2_CUBES
    )
    p3 = statistics.median(G) >= G_BAR
    decision = "close" if not p3 else ("open" if p1 else "mechanism_wrong")
    return {"status": "OK", "median_G": statistics.median(G), "G_range": [min(G), max(G)],
            "median_premature_share": statistics.median(share), "premature_share_range": [min(share), max(share)],
            "P1": p1, "P2": p2, "P3": p3, "decision": decision, "reading": READINGS[decision]}  # fmt: skip


def read_meta(run: Path, afv: dict) -> tuple[dict, list[str]]:
    """id -> (stop_reasons, links) from the run's fiber JSONs, and any way they fail to match the `.afv`."""
    meta, ends = {}, {}
    for f in sorted((run / "fibers").rglob("*.json")):
        d = json.loads(f.read_text())
        ff = d["fiber_follow"]
        meta[ff["id"]] = (ff["stop_reasons"], ff["links"])
        ends[ff["id"]] = np.asarray(d["line_points"], float)[[0, -1]]
    if set(meta) != set(afv):
        return meta, ["ids"]
    worst = max(
        (float(np.abs(afv[k][[0, -1]] - ends[k]).max()) for k in meta), default=0.0
    )
    return meta, (["ends"] if worst > END_AGREEMENT else [])


def _medians(per_cube: dict, cubes: list, tol: str, setting: str) -> dict:
    rows = [per_cube[c][tol] for c in cubes if c in per_cube]
    out = {}
    for key in ("G", "premature_share"):
        v = [
            r["settings"][setting][key]
            for r in rows
            if r["settings"][setting][key] is not None
        ]
        out[key] = (
            {"median": statistics.median(v), "min": min(v), "max": max(v), "n": len(v)}
            if v
            else None
        )
    base = [r["base_rate"][setting.split("_")[0]] for r in rows]
    base = [b for b in base if b is not None]
    out["base_rate"] = (
        {"median": statistics.median(base), "n": len(base)} if base else None
    )
    for reason in ("confidence", "owned_or_live"):
        stops_ = sum(
            r["settings"][setting].get(reason, {}).get("stops", 0) for r in rows
        )
        left = sum(
            r["settings"][setting].get(reason, {}).get("left_fiber", 0) for r in rows
        )
        on = sum(
            r["settings"][setting].get(reason, {}).get("on_fiber", 0) for r in rows
        )
        out[reason] = {"stops": stops_, "on_fiber": on, "left_fiber": left,
                       "left_fiber_share": left / stops_ if stops_ else None}  # fmt: skip
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--cubes", nargs="*", help="a subset (a smoke); the verdict then reads PARTIAL"
    )
    ap.add_argument(
        "--out", type=Path, default=Path("reports/neural_tracer_confidence_stops.json")
    )
    args = ap.parse_args(argv)

    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import (
        SCORING_VERSION,
        _dilate_labels,
        score_tracing,
    )
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    recorded = {}
    for path in RECORDED.values():
        d = json.loads(path.read_text())
        for c in d["rows_tol2"]:
            recorded[c] = {2.0: d["rows_tol2"][c], 4.0: d["rows_tol4"][c]}
    cubes = args.cubes or ALL
    gate, per_cube, skeletons = {}, {}, {}
    for n, c in enumerate(cubes, 1):
        size = int(c.rsplit("_", 1)[1])
        run = RUNS[size] / c
        target = f91.SG / "data" / f"fibers_{c}"
        skeletons[c] = hashlib.sha256(
            (target / "skeleton.npz").read_bytes()
        ).hexdigest()
        skel, _, _ = load_fiber_target(target)
        afv = afv_to_labels.read_afv(run / "fibers.afv")
        meta, problems = read_meta(run, afv)
        lab = ctx.labels_of_fibers(afv, MARGIN, size)
        row = score_tracing(skel, lab, tolerance=TOL).as_row()
        gate[c] = problems + gate_problems(row, recorded[c][TOL])
        fibers = {
            k: afv_to_labels.to_cube_zyx(v, (MARGIN,) * 3) for k, v in afv.items()
        }
        ref = Reference(skel.fibers, size)
        per_cube[c] = {}
        for tol in TOLS:
            grown = _dilate_labels(lab, tol)
            covered = recorded[c][tol]["coverage"] * recorded[c][tol]["gt_length"]
            per_cube[c][f"tol{int(tol)}"] = measure_cube(ref, grown, fibers, meta, size, tol, covered,
                                                         np.random.default_rng(RNG_SEED))  # fmt: skip
            del grown
        r = per_cube[c]["tol2"]["settings"]["L20_edge6"]
        print(
            f"[{n}/{len(cubes)}] {c}: gate {gate[c] or 'ok'}; G {r['G']}; premature {r['premature_share']}",
            flush=True,
        )

    setting, tol = f"L{int(L)}_edge{int(EDGE)}", f"tol{int(TOL)}"
    registered = {c: {"G": v[tol]["settings"][setting]["G"],
                      "premature_share": v[tol]["settings"][setting]["premature_share"],
                      "base_rate": v[tol]["base_rate"][f"L{int(L)}"]} for c, v in per_cube.items()}  # fmt: skip
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
    summary = {name: {t: {s: _medians(per_cube, members, t, s) for s in per_cube[cubes[0]][t]["settings"]}
                      for t in per_cube[cubes[0]]} for name, members in sets.items()}  # fmt: skip
    sg_commit = subprocess.run(["git", "-C", str(f91.SG), "rev-parse", "HEAD"], capture_output=True, text=True,
                               check=True).stdout.strip()  # fmt: skip
    checkpoints = sorted({json.loads((RUNS[int(c.rsplit("_", 1)[1])] / c / "run.json").read_text())["checkpoint"]
                          for c in cubes})  # fmt: skip
    out = {
        "registration": "docs/preregistration/2026-11-01_neural_tracer_confidence_stops.md",
        "verdict": v,
        "registered": registered,
        "gate": gate,
        "settings": {
            "tol": TOL,
            "L": L,
            "edge": EDGE,
            "cap": CAP,
            "step": STEP,
            "base_n": BASE_N,
            "rng_seed": RNG_SEED,
            "back_direction": BACK_DIRECTION,
            "back_late": BACK_LATE,
        },  # fmt: skip
        "sets": sets,
        "summary": summary,
        "per_cube": per_cube,
        "provenance": {
            "runs": {str(k): "/".join(p.parts[-3:]) for k, p in RUNS.items()},
            "scrollgt_commit": sg_commit,
            "scoring_version": SCORING_VERSION,
            "skeleton_sha256": skeletons,
            "checkpoints": checkpoints,
        },  # fmt: skip
    }
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(v, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
