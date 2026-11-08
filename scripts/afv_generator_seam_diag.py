# ruff: noqa
"""Scratch: why the trim loses face crossings. For one held-out cube and arm (real or same), rebuild main's and the
patched stitching from the chain's cached fields exactly as scripts/afv_generator_block_seams.py does, check the rebuild
reproduces the record's row, then follow every reference crossing through four stages:

  pieces    the block splines given to the catalogue (after the trim, for patched);
  sources   the catalogue sources left unaliased (>= 5 points, not suppressed as a duplicate), and short splines kept;
  stitched  the catalogue chains and the short splines kept (what clean() receives);
  written   after clean() (sharp joins cut, black, --min-length 100, thinning).

Each stage gets the record's kind (whole / broken / lost). For each crossing whose kind differs between main and
patched, the covering sources from different blocks are compared: catalogue record (linked / dup / candidate / none),
and, without a candidate, compare()'s first rejecting tests.

Usage: python -I diag_lost.py CUBE ARM --work WORK --pr PR_SRC --patched-stitch PATH --out DIR
"""

import argparse
import inspect
import json
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

REPO = Path(
    "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/.claude/worktrees/research/afv-generator-block-seams"
)
sys.path.insert(0, str(REPO / "scripts"))
import afv_generator_block_seams as bs  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cube")
ap.add_argument("arm", choices=("real", "same"))
ap.add_argument("--work", type=Path, required=True)
ap.add_argument("--pr", type=Path, required=True)
ap.add_argument("--patched-stitch", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--ct", type=Path, default=bs.CT)
args = ap.parse_args()

trim_cut_ends, cut_end = bs.load(args.pr, args.patched_stitch)
import zarr  # noqa: E402
from vesuvius.afv_spline_generator import cli  # noqa: E402
from vesuvius.afv_spline_generator.cleanup import ExteriorBlack, clean  # noqa: E402
from vesuvius.afv_spline_generator.extend import overlap as ov  # noqa: E402
from vesuvius.afv_spline_generator.extend.stitch import FAMILIES, Stitcher  # noqa: E402
from vesuvius.afv_spline_generator.splines import extract_splines, threshold_to_u8  # noqa: E402

# compare() with a record of the line of every `continue` / `return None` it takes
src = textwrap.dedent(inspect.getsource(ov.compare))
first = inspect.getsourcelines(ov.compare)[1]
lines = []
for i, ln in enumerate(src.splitlines()):
    s = ln.strip()
    ind = ln[: len(ln) - len(ln.lstrip())]
    # the line before each `continue` / `return None` is the test that took it
    lines.append(
        f"{ind}_WHY.append({first + i - 1}); {s}"
        if s in ("continue", "return None")
        else ln
    )
ns = dict(vars(ov))
ns["_WHY"] = []
exec("\n".join(lines).replace("def compare(", "def compare_why(", 1), ns)
compare_why, WHY = ns["compare_why"], ns["_WHY"]
OV_LINES = inspect.getsource(ov).splitlines()

c, arm = args.cube, args.arm
work = args.work / c
n = int(c.rsplit("_", 1)[1])
record = json.loads((work / "result.json").read_text())
ct = np.asarray(zarr.open(str(args.ct / f"{c}.zarr"), mode="r")[:])
shape_xyz = np.asarray(ct.shape[::-1])
threshold = threshold_to_u8(bs.THRESHOLD)
z = np.load(work / "one_main_fibers.npz")
o = z["offsets"]
ref = [z["points"][o[i] : o[i + 1]] for i in range(len(o) - 1)]
ref_fam = [int(f) for f in z["family"]]
xs = bs.crossings(ref, ref_fam, n)

cache = args.out / "cache" / c
cache.mkdir(parents=True, exist_ok=True)
whole = np.load(work / "prob_one.npy", mmap_mode="r")
blocks = []
for i, (origin, size) in enumerate(cli.zone_blocks([0, 0, 0], list(shape_xyz), n // 2)):
    low = np.maximum(np.asarray(origin) - cli.BLOCK_MARGIN, 0)
    high = np.minimum(
        np.asarray(origin) + np.asarray(size) + cli.BLOCK_MARGIN, shape_xyz
    )
    sl = tuple(slice(int(a), int(b)) for a, b in zip(low[::-1], high[::-1]))
    f = cache / f"{arm}_{i}.npz"
    if f.exists():
        q = np.load(f)
        traces = [(str(fam), q[f"p{k}"]) for k, fam in enumerate(q["family"])]
    else:
        prob = (
            np.load(work / f"prob_real_{i}.npy")
            if arm == "real"
            else np.asarray(whole[sl])
        )
        traces = [(fam, np.asarray(p)) for fam, p in extract_splines(prob, threshold)]
        np.savez(
            f,
            family=np.array([t[0] for t in traces]),
            **{f"p{k}": t[1] for k, t in enumerate(traces)},
        )
    blocks.append((np.asarray(origin), np.asarray(size), low, high, sl, traces))


def kinds(fibers, families):
    """Per crossing, the record's kind (bs.crossing_kinds, one crossing at a time)."""
    trees = [cKDTree(bs.dense(f)[0]) for f in fibers]
    out = []
    for fam, win in xs:
        best, cover = 0.0, np.zeros(len(win), bool)
        for t, f in zip(trees, families):
            if f == fam:
                q = t.query(win)[0] <= 2.0
                cover |= q
                best = max(best, float(q.mean()))
        out.append(
            "whole" if best >= 0.95 else ("broken" if cover.mean() >= 0.8 else "lost")
        )
    return out


def covers(fibers, families):
    """Per crossing, over the written fibers of its family: the best one's share of the window within 2 voxels, the
    union's share, and how many fibers cover at least 10% of it (1 = a lone copy)."""
    trees = [cKDTree(bs.dense(f)[0]) for f in fibers]
    out = []
    for fam, win in xs:
        best, cover, count = 0.0, np.zeros(len(win), bool), 0
        for t, f in zip(trees, families):
            if f == fam:
                q = t.query(win)[0] <= 2.0
                cover |= q
                best = max(best, float(q.mean()))
                count += int(q.mean() >= 0.1)
        out.append(
            dict(best=round(best, 3), union=round(float(cover.mean()), 3), n=count)
        )
    return out


result = {
    "cube": c,
    "arm": arm,
    "cut_end": cut_end,
    "n_crossings": len(xs),
    "variants": {},
}
per = {}
for variant in bs.VARIANTS:
    black = ExteriorBlack(np.zeros(3, int), shape_xyz)
    scratch = tempfile.TemporaryDirectory(prefix="afv-diag-", dir=str(args.out))
    st = Stitcher(scratch.name)
    pieces, piece_fam = [], []
    for i, (origin, size, low, high, sl, traces) in enumerate(blocks):
        black.add(ct[sl], low)
        t = (
            trim_cut_ends(traces, low[::-1], high[::-1], shape_xyz[::-1])
            if variant == "patched"
            else list(traces)
        )
        for fam, line in t:
            pieces.append(np.asarray(line, float)[:, ::-1] + low)
            piece_fam.append(FAMILIES[fam])
        st.add_block(
            f"block-{i}",
            low.tolist(),
            (high - low).tolist(),
            t,
            (origin, origin + size),
        )
    stitched = st.stitched()
    written = clean(
        stitched, bs.MAX_JOIN_ANGLE, bs.MIN_LENGTH, black, bs.BLACK_DISTANCE
    )
    cat, db = st.catalog, st.catalog.db
    S = {
        int(r[0]): dict(job=r[1], fam=int(r[2]), length=float(r[3]))
        for r in db.execute(
            "SELECT id, job_id, family, length FROM sources WHERE alias IS NULL"
        )
    }
    G = {s: np.asarray(cat.source(s)["geometry"], float) for s in S}
    chain = {
        int(s): int(ch) for s, ch in db.execute("SELECT source, chain FROM members")
    }
    chain_len = {
        int(r[0]): float(r[1]) for r in db.execute("SELECT id, length FROM chains")
    }
    dups = {
        frozenset((int(a), int(b)))
        for a, b, _ in db.execute("SELECT * FROM duplicates")
    }
    cands = {}
    for r in db.execute("SELECT id, a, ea, b, eb, kind, strict FROM candidates"):
        cands.setdefault(frozenset((int(r[1]), int(r[3]))), []).append(
            dict(
                id=int(r[0]),
                a=int(r[1]),
                ea=int(r[2]),
                b=int(r[3]),
                eb=int(r[4]),
                kind=r[5],
                strict=int(r[6]),
            )
        )
    links = {
        frozenset((int(r[0]), int(r[1]))) for r in db.execute("SELECT a, b FROM links")
    }

    def options(sid, end):
        return len([r for r in cat._options(sid, end) if r["kind"] == "overlap"])

    src_fibers = [G[s] for s in S] + [np.asarray(s["points"], float) for s in st.short]
    src_fam = [S[s]["fam"] for s in S] + [int(s["family"]) for s in st.short]
    k = {
        "pieces": kinds(pieces, piece_fam),
        "sources": kinds(src_fibers, src_fam),
        "stitched": kinds(
            [np.asarray(t["points"], float) for t in stitched],
            [int(t["family"]) for t in stitched],
        ),
        "written": kinds(
            [np.asarray(t["points"], float) for t in written],
            [int(t["family"]) for t in written],
        ),
    }
    row = record["rows"][f"{arm}/{variant}"]
    length = round(
        float(
            sum(bs.dense(np.asarray(t["points"], np.float64))[1][-1] for t in written)
        ),
        1,
    )
    check = {
        "written": [len(written), row["written"]],
        "length": [length, row["length"]],
        "crossings": [dict(Counter(k["written"])), row["crossings"]],
    }
    result["variants"][variant] = {
        "check": check,
        "stage_counts": {s: dict(Counter(v)) for s, v in k.items()},
        "pieces": len(pieces),
        "sources": len(S),
        "short": len(st.short),
        "stitched": len(stitched),
        "written": len(written),
    }
    cover = covers(
        [np.asarray(t["points"], float) for t in written],
        [int(t["family"]) for t in written],
    )
    per[variant] = dict(
        scratch=scratch,
        k=k,
        cover=cover,
        S=S,
        G=G,
        chain=chain,
        chain_len=chain_len,
        dups=dups,
        cands=cands,
        links=links,
        options=options,
        stitched=stitched,
        written=written,
    )
    print(variant, json.dumps(result["variants"][variant]), flush=True)

# where each patched-not-main loss happens, and why the covering sources were not joined
trans = Counter(zip(per["main"]["k"]["written"], per["patched"]["k"]["written"]))
result["transitions_main_to_patched"] = {
    f"{a}->{b}": v for (a, b), v in sorted(trans.items())
}
stage_of_loss = Counter()
details = []
for j, (fam, win) in enumerate(xs):
    km, kp = per["main"]["k"]["written"][j], per["patched"]["k"]["written"][j]
    if km == kp:
        continue
    P = per["patched"]
    path = {s: P["k"][s][j] for s in ("pieces", "sources", "stitched", "written")}
    stage_of_loss[(f"{km}->{kp}",) + tuple(path.values())] += 1
    d = {
        "crossing": j,
        "family": fam,
        "main": {s: per["main"]["k"][s][j] for s in path},
        "patched": path,
        "sources": [],
        "written_cover": {v: per[v]["cover"][j] for v in bs.VARIANTS},
    }
    for variant in bs.VARIANTS:
        V = per[variant]
        cov = []
        for sid, info in V["S"].items():
            if info["fam"] != fam:
                continue
            q = cKDTree(bs.dense(V["G"][sid])[0]).query(win)[0] <= 2.0
            if q.mean() >= 0.1:
                ch = V["chain"].get(sid)
                cov.append(
                    dict(
                        sid=sid,
                        block=info["job"],
                        length=round(info["length"], 1),
                        share=round(float(q.mean()), 3),
                        chain=ch,
                        chain_length=None
                        if ch is None
                        else round(V["chain_len"][ch], 1),
                    )
                )
        pairs = []
        for a in range(len(cov)):
            for b in range(a + 1, len(cov)):
                A, B = cov[a]["sid"], cov[b]["sid"]
                if V["S"][A]["job"] == V["S"][B]["job"]:
                    continue
                key = frozenset((A, B))
                rec = (
                    "linked"
                    if key in V["links"]
                    else "dup"
                    if key in V["dups"]
                    else "candidate"
                    if key in V["cands"]
                    else "none"
                )
                entry = dict(a=A, b=B, catalogue=rec)
                if rec == "candidate":
                    entry["candidates"] = [
                        dict(
                            r,
                            options_a=V["options"](r["a"], r["ea"]),
                            options_b=V["options"](r["b"], r["eb"]),
                        )
                        for r in V["cands"][key]
                    ]
                if rec == "none":
                    WHY.clear()
                    r = compare_why(V["G"][A], V["G"][B])
                    entry["compare"] = None if r is None else r["kind"]
                    entry["rejects"] = sorted(
                        {OV_LINES[t - 1].strip()[:70] for t in WHY}
                    )
                    # the test furthest into compare() that any orientation reached
                    entry["deepest"] = (
                        OV_LINES[max(WHY) - 1].strip()[:70] if WHY else None
                    )
                pairs.append(entry)
        d["sources"].append({"variant": variant, "covering": cov, "pairs": pairs})
    details.append(d)
result["patched_path_of_changed"] = {
    " ".join(k): v for k, v in sorted(stage_of_loss.items())
}
args.out.mkdir(parents=True, exist_ok=True)
(args.out / f"{c}_{arm}.json").write_text(
    json.dumps(dict(result, details=details), indent=1, default=str)
)
print(
    json.dumps({k: v for k, v in result.items() if k != "variants"}, indent=1),
    flush=True,
)
