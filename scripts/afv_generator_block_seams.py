"""Block seams in villa's automated fiber generator, and a fix that trims the ends a block's border cuts.

villa's `vesuvius.fiber_spline_generator` (PR #1934, merged 2026-11-01; VC3D's "Generate automated fibers...") cuts a
zone into blocks, each read with a 32-voxel margin, and stitches the blocks' splines in a catalogue. This runs one ScrollGT
cube as villa's generator would in three ways, each with villa main's stitching and with the fix:

  one:   the cube as one block (the reference);
  real:  the cube in 8 blocks of half its side, each predicted from its own CT crop (what a multi-block zone gets);
  same:  8 blocks cut from arm one's probability field (the stitching alone).

The fix (`trim_cut_ends`, in the villa patch beside this script's record) drops, at each end of a block's spline, the
points within `CUT_END` voxels of a border of the block that the volume continues past, unless that end lies at the
volume's own border. It is read from the patched villa source given by --patched-stitch, not copied here.

The prediction, spline and stitching code is the #1934 head 2d8577e (pure Python; finding 85 ran it). Its stitching
and prediction modules are byte-identical to villa main's and its spline module differs only by scipy -> vc_reader
calls (villa #2440), which needs villa's native build; `identity()` checks the first against the villa commit given.
Settings are villa's defaults: model Qualzz20/afv_fiber_9um at its recorded revision, threshold 60%, margin 32, no
mirroring, no --extend, join angle 45, minimum length 100, black distance 16 (no cube has any exterior black).

Usage (the generator's venv; CPU unless --device says otherwise):
  python -I scripts/afv_generator_block_seams.py run CUBE --work DIR --pr PR_SRC --villa VILLA --main REV \
      --patched-stitch PATH [--device cpu]
  python -I scripts/afv_generator_block_seams.py verdict --work DIR --out RECORD
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SG = Path(
    "/home/jon/openclaw-workspace/Neo-VM/projects/scrollgt"
)  # the sibling checkout, as finding 91 reads it
HELD_OUT = [
    "s3_00994_00494_01994_512",
    "s3_00994_01994_00494_512",
    "s3_00994_02494_01494_512",
    "s3_01994_01494_00994_512",
    "s3_01994_01994_01494_512",
    "s3_02994_02494_01994_512",
    "s3_03494_01494_00494_512",
    "s3_04494_00994_01494_512",
]
CT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/zarr")
REVISION = "e189af7507d16d85d510c372e33d798fc509bb59"
PR_HEAD = "2d8577ed"
# PR-head module -> villa main module, byte-identical
IDENTICAL = {
    f"extend/{m}.py": f"extend/{m}.py"
    for m in ("stitch", "catalog", "overlap", "candidates", "expander")
} | {"predict.py": "predict.py"}
THRESHOLD = 60.0
MAX_JOIN_ANGLE = 45.0
MIN_LENGTH = 100.0
BLACK_DISTANCE = 16.0
TOLS = (2.0, 4.0)
DUPLICATE = 1.5  # voxels: length beside a different same-family fiber
CROSSING_WINDOW = 40.0  # voxels of arclength each side of a face crossing
VARIANTS = ("main", "patched")
ARMS = ("one", "real", "same")


def identity(pr_src: Path, villa: Path, rev: str, patched_stitch: Path) -> list[str]:
    """Problems: the PR-head modules that must equal villa main's, and the patch adding only `trim_cut_ends`."""
    bad = []
    pkg = pr_src / "vesuvius" / "afv_spline_generator"
    for mine, theirs in IDENTICAL.items():
        main = subprocess.run(["git", "-C", str(villa), "show", f"{rev}:vesuvius/src/vesuvius/fiber_spline_generator/{theirs}"],
                              capture_output=True, check=True).stdout  # fmt: skip
        if (pkg / mine).read_bytes() != main:
            bad.append(f"{mine} differs from villa {rev[:9]}")
    main = subprocess.run(["git", "-C", str(villa), "show", f"{rev}:vesuvius/src/vesuvius/fiber_spline_generator/extend/stitch.py"],
                          capture_output=True, check=True, text=True).stdout  # fmt: skip
    patched = patched_stitch.read_text()
    # The patch adds a comment and CUT_END after FAMILIES, and trim_cut_ends before _Frozen; nothing else.
    head, sep, rest = patched.partition('FAMILIES = {"V": 0, "H": 1}\n')
    constant_end = rest.find("CUT_END = ")
    function = rest.find("def trim_cut_ends(")
    frozen = rest.find("class _Frozen:")
    if not sep or constant_end < 0 or not 0 <= function < frozen:
        return bad + [
            "the patched stitch.py has no CUT_END or trim_cut_ends where the patch puts them"
        ]
    after_constant = rest.index("\n", constant_end) + 1
    restored = head + sep + rest[after_constant:function] + rest[frozen:]
    if restored != main:
        bad.append("the patched stitch.py changes more than CUT_END and trim_cut_ends")
    return bad


def load(pr_src: Path, patched_stitch: Path):
    sys.path.insert(0, str(pr_src))
    sys.path.insert(0, str(SG / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from vesuvius.afv_spline_generator import cli  # noqa: F401  (PR-head package)

    spec = importlib.util.spec_from_file_location(
        "vesuvius.afv_spline_generator.extend.stitch_patched", patched_stitch
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.trim_cut_ends, mod.CUT_END


def dense(points: np.ndarray, step: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    t = np.arange(0.0, s[-1] + 1e-9, step)
    return np.column_stack([np.interp(t, s, points[:, k]) for k in range(3)]), t


def duplicated_share(fibers: list[np.ndarray], families: list[int]) -> float:
    """Share of written length within DUPLICATE voxels of a different fiber of the same family."""
    from scipy.spatial import cKDTree

    dup = total = 0.0
    for fam in set(families):
        idx = [i for i, f in enumerate(families) if f == fam]
        pts = [dense(fibers[i])[0] for i in idx]
        allp = np.concatenate(pts)
        own = np.concatenate([np.full(len(p), k) for k, p in enumerate(pts)])
        tree = cKDTree(allp)
        for k, p in enumerate(pts):
            near = tree.query_ball_point(p, DUPLICATE)
            dup += sum(bool(np.any(own[n] != k)) for n in near)
            total += len(p)
    return dup / total if total else 0.0


def crossings(
    reference: list[np.ndarray], ref_families: list[int], size: int
) -> list[tuple[int, np.ndarray]]:
    """(family, window) for each reference fiber crossing a mid plane with CROSSING_WINDOW voxels on both sides."""
    h, out = size / 2, []
    for p, fam in zip(reference, ref_families, strict=False):
        d, s = dense(p)
        for ax in range(3):
            side = np.where(
                d[:, ax] >= h, 1, -1
            )  # a sample on the plane counts on its far side
            for j in np.flatnonzero(side[:-1] * side[1:] < 0):
                if s[j] >= CROSSING_WINDOW and s[-1] - s[j] >= CROSSING_WINDOW:
                    out.append(
                        (
                            fam,
                            d[
                                (s >= s[j] - CROSSING_WINDOW)
                                & (s <= s[j] + CROSSING_WINDOW)
                            ],
                        )
                    )
    return out


def crossing_kinds(xs, fibers, families) -> dict:
    """whole: one fiber within 2 voxels of >= 95% of the window; broken: covered (>= 80%) by no single fiber; lost."""
    from scipy.spatial import cKDTree

    trees = [cKDTree(dense(f)[0]) for f in fibers]
    k = Counter({"whole": 0, "broken": 0, "lost": 0})
    for fam, win in xs:
        best, cover = 0.0, np.zeros(len(win), bool)
        for t, f in zip(trees, families, strict=False):
            if f == fam:
                q = t.query(win)[0] <= 2.0
                cover |= q
                best = max(best, float(q.mean()))
        k[
            "whole" if best >= 0.95 else ("broken" if cover.mean() >= 0.8 else "lost")
        ] += 1
    return dict(k)


def run(args) -> None:
    import torch
    import zarr

    trim_cut_ends, cut_end = load(args.pr, args.patched_stitch)
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack, clean
    from vesuvius.afv_spline_generator.extend.stitch import Stitcher
    from vesuvius.afv_spline_generator.predict import predict_fibers
    from vesuvius.afv_spline_generator.splines import extract_splines, threshold_to_u8

    c = args.cube
    n = int(c.rsplit("_", 1)[1])
    work = args.work / c
    work.mkdir(parents=True, exist_ok=True)
    problems = identity(args.pr, args.villa, args.main, args.patched_stitch)
    ct = np.asarray(zarr.open(str(CT / f"{c}.zarr"), mode="r")[:])
    shape_xyz = np.asarray(ct.shape[::-1])
    device = torch.device(args.device)
    folder, provenance = cli.resolve_model(cli.DEFAULT_MODEL)
    if provenance.get("revision", REVISION) != REVISION:
        problems.append(
            f"model revision {provenance.get('revision')} is not {REVISION}"
        )
    network, patch = cli.load_network(folder, device)
    threshold = threshold_to_u8(THRESHOLD)
    timing = {}

    def predicted(name: str, sl) -> np.ndarray:
        f = work / f"prob_{name}.npy"
        if f.exists():
            return np.load(f)
        t = time.time()
        p = predict_fibers(network, ct[sl], patch, device=device, mirror=False)
        timing[name] = round(time.time() - t, 1)
        np.save(f, p)
        return p

    whole = predicted("one", (slice(None),) * 3)

    def generate(arm: str, variant: str) -> list[dict]:
        block = n if arm == "one" else n // 2
        black = ExteriorBlack(np.zeros(3, int), shape_xyz)
        with tempfile.TemporaryDirectory(prefix="afv-stitch-") as scratch:
            st = Stitcher(scratch)
            try:
                for i, (origin, size) in enumerate(
                    cli.zone_blocks([0, 0, 0], list(shape_xyz), block)
                ):
                    low = np.maximum(np.asarray(origin) - cli.BLOCK_MARGIN, 0)
                    high = np.minimum(
                        np.asarray(origin) + np.asarray(size) + cli.BLOCK_MARGIN,
                        shape_xyz,
                    )
                    sl = tuple(
                        slice(int(a), int(b))
                        for a, b in zip(low[::-1], high[::-1], strict=False)
                    )
                    black.add(ct[sl], low)
                    if arm == "real" and block < n:
                        prob = predicted(f"real_{i}", sl)
                    else:
                        prob = whole[sl]
                    traces = extract_splines(prob, threshold)
                    if variant == "patched":
                        traces = trim_cut_ends(
                            traces, low[::-1], high[::-1], shape_xyz[::-1]
                        )
                    st.add_block(f"block-{i}", low.tolist(), (high - low).tolist(), traces,
                                 (np.asarray(origin), np.asarray(origin) + np.asarray(size)))  # fmt: skip
                traces = st.stitched()
            finally:
                st.close()
        return clean(traces, MAX_JOIN_ANGLE, MIN_LENGTH, black, BLACK_DISTANCE)

    skel, _, _ = load_fiber_target(SG / "data" / f"fibers_{c}")
    out = {
        "cube": c,
        "size": n,
        "block": n // 2,
        "cut_end": cut_end,
        "identity_problems": problems,
        "rows": {},
    }
    reference: tuple[list[np.ndarray], list[int]] | None = (
        None  # arm one at main, which ARMS runs first
    )
    for arm in ARMS:
        for variant in VARIANTS:
            traces = generate(arm, variant)
            fibers = [np.asarray(t["points"], np.float64) for t in traces]
            families = [int(t["family"]) for t in traces]
            if arm == "one" and variant == "main":
                reference = (fibers, families)
            assert reference is not None
            if arm == "one" and variant == "patched":
                # one block has no inner border: the patch must change nothing (gate 3); not scored again
                same = families == reference[1] and all(
                    np.array_equal(a, b)
                    for a, b in zip(fibers, reference[0], strict=False)
                )
                if not same or len(fibers) != len(reference[0]):
                    problems.append(
                        "the one-block arm differs between main and patched (it has no inner border)"
                    )
                continue
            if arm == "one" and variant == "main":
                np.savez(work / "one_main_fibers.npz", points=np.concatenate(fibers),
                         offsets=np.r_[0, np.cumsum([len(f) for f in fibers])], family=np.array(families))  # fmt: skip
            labels = afv_to_labels.rasterize(
                {
                    k: afv_to_labels.to_cube_zyx(v, (0, 0, 0))
                    for k, v in enumerate(fibers)
                },
                (n,) * 3,
            )
            row = {
                f"tol{int(t)}": score_tracing(skel, labels, tolerance=t).as_row()
                for t in TOLS
            }
            row["written"] = len(fibers)
            row["length"] = round(float(sum(dense(f)[1][-1] for f in fibers)), 1)
            row["duplicated_share"] = round(duplicated_share(fibers, families), 4)
            row["crossings"] = crossing_kinds(
                crossings(reference[0], reference[1], n), fibers, families
            )
            out["rows"][f"{arm}/{variant}"] = row
            r2, r4 = row["tol2"], row["tol4"]
            print(f"{c} {arm:4s} {variant:7s} written {row['written']:4d} dup {row['duplicated_share']:.3f} "
                  f"crossings {row['crossings']} | t2 {r2['erl_merge_penalized']} m{r2['merges']} | "
                  f"t4 {r4['erl_merge_penalized']} m{r4['merges']}", flush=True)  # fmt: skip
    out["patched_stitch_sha256"] = hashlib.sha256(
        args.patched_stitch.read_bytes()
    ).hexdigest()
    out["timing_s"] = timing
    out["settings"] = {"threshold": THRESHOLD, "margin": cli.BLOCK_MARGIN, "mirror": False, "extend": False,
                       "max_join_angle": MAX_JOIN_ANGLE, "min_length": MIN_LENGTH, "black_distance": BLACK_DISTANCE,
                       "model": cli.DEFAULT_MODEL, "revision": REVISION, "pr_head": PR_HEAD, "villa_main": args.main,
                       "device": args.device}  # fmt: skip
    (work / "result.json").write_text(json.dumps(out, indent=1))
    print(f"{c}: identity problems {problems or 'none'}", flush=True)


def gain(rows: dict, arm: str, tol: str) -> float:
    return (
        rows[f"{arm}/patched"][tol]["erl_merge_penalized"]
        / rows[f"{arm}/main"][tol]["erl_merge_penalized"]
        - 1
    )


def verdict(results: dict) -> dict:
    """The registered predictions on the held-out cubes (docs/preregistration/2026-11-06_afv_generator_block_seams.md)."""
    if sorted(results) != sorted(HELD_OUT):
        return {"decision": "NO_VERDICT", "why": "not every held-out cube was run"}
    bad = {
        c: r["identity_problems"] for c, r in results.items() if r["identity_problems"]
    }
    if bad:
        return {"decision": "NO_VERDICT", "why": f"identity problems: {bad}"}
    rows = {c: r["rows"] for c, r in results.items()}
    g4 = {c: gain(r, "real", "tol4") for c, r in rows.items()}
    g2 = {c: gain(r, "real", "tol2") for c, r in rows.items()}
    m_main = sum(r["real/main"]["tol2"]["merges"] for r in rows.values())
    m_fix = sum(r["real/patched"]["tol2"]["merges"] for r in rows.values())
    p1 = sum(v > 0 for v in g4.values()) >= 6
    p2 = statistics.median(g4.values()) >= 0.10
    p3 = m_fix <= 1.05 * m_main
    p4 = statistics.median(g2.values()) >= 0.05
    if not p3:
        decision = "COSTS_MERGES"
    elif p1 and p2:
        decision = "SUPPORTED"
    else:
        decision = "NOT_SUPPORTED"
    return {
        "decision": decision,
        "P1_gain_tol4_cubes_up": [sum(v > 0 for v in g4.values()), p1],
        "P2_median_gain_tol4": [round(statistics.median(g4.values()), 4), p2],
        "P3_merges_tol2": [m_main, m_fix, p3],
        "P4_median_gain_tol2": [round(statistics.median(g2.values()), 4), p4],
        "gain_tol4": {c: round(v, 4) for c, v in g4.items()},
        "gain_tol2": {c: round(v, 4) for c, v in g2.items()},
        "defect_real_vs_one_tol4": {
            c: round(
                r["real/main"]["tol4"]["erl_merge_penalized"]
                / r["one/main"]["tol4"]["erl_merge_penalized"],
                4,
            )
            for c, r in rows.items()
        },  # fmt: skip
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("cube")
    r.add_argument("--work", type=Path, required=True)
    r.add_argument(
        "--pr", type=Path, required=True, help="the #1934 head's vesuvius/src"
    )
    r.add_argument("--villa", type=Path, required=True)
    r.add_argument(
        "--main", required=True, help="villa main commit the PR-head modules must equal"
    )
    r.add_argument("--patched-stitch", type=Path, required=True)
    r.add_argument("--device", default="cpu")
    v = sub.add_parser("verdict")
    v.add_argument("--work", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    else:
        results = {
            p.parent.name: json.loads(p.read_text())
            for p in sorted(a.work.glob("*/result.json"))
            if p.parent.name in HELD_OUT
        }
        record = {"verdict": verdict(results), "cubes": results}
        if a.out.exists():
            raise SystemExit(f"{a.out} exists: the record is written once")
        a.out.write_text(json.dumps(record, indent=1))
        print(json.dumps(record["verdict"], indent=1))


if __name__ == "__main__":
    main()
