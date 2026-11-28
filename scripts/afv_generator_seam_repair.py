"""Finding 140: the repaired seam trim of villa #2711 on findings 106's and 109's cached fiber fields.

Three arms per cube, from the cached `real` fields (each block predicted from its own crop), so only the trim differs:
  main      untrimmed; must equal the cube's recorded real/main row
  trim      finding 106's trim (its first form on Scroll 3, its zone form on Scrolls 1 and 5); must equal the recorded
            real/patched (Scroll 3) or real/trim (Scrolls 1 and 5) row
  repaired  the review-repaired trim: each block trimmed against the untrimmed splines of the blocks whose read box
            meets its own, as villa's `generate` does once it holds each block until its neighbours are fitted

Usage (the generator's venv, CPU):
  python -I scripts/afv_generator_seam_repair.py run SET CUBE --fields DIR --out DIR --pr PR_SRC --old-first PATH \
      --old-zone PATH --repaired PATH
  python -I scripts/afv_generator_seam_repair.py verdict --out DIR --record RECORD
  python -I scripts/afv_generator_seam_repair.py zone --work F107_WORK --out DIR --pr PR_SRC --old-zone PATH \
      --repaired PATH   (addendum 1: finding 107's 1024³ zone, described)
  addendum 2, villa #2434 in both arms (GATED = --out DIR --pr PKG_2434 --pr1934 PR_SRC --repaired HEAD_STITCH
      --gate GATE_OUT --f140 RECORD; GATE_OUT holds `run scroll3 GATE_CUBE`'s result, as finding 140 ran it):
  python -I scripts/afv_generator_seam_repair.py after2434 SET CUBE --fields DIR GATED
  python -I scripts/afv_generator_seam_repair.py zone2434 --work F107_WORK GATED
  python -I scripts/afv_generator_seam_repair.py record2434 --out DIR --gate GATE_OUT --f140 RECORD --record RECORD
SET is scroll3 (finding 106's eight cubes) or confirm (finding 109's ten).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_cross_block_duplicates as xd  # noqa: E402
import afv_generator_seam_confirmation as sc  # noqa: E402

SETS = {
    "scroll3": (tuple(bs.HELD_OUT), "real/patched"),
    "confirm": (tuple(sc.CUBES), "real/trim"),
}
UP_LINE, KEEP_MEDIAN, LOSE_MEDIAN, LOST_LINE = 7, 0.06, 0.03, 190

# Addendum 2: #1934's package with villa #2434's diff, the four files it changes, and #2711's head stitch.py.
PATCH_2434_SHA256 = "d4f47ea84dec479f55fd97e3ecc335ddff146d910899c0536a359c900850828a"
PACKAGE_2434_SHA256 = {
    "cleanup.py": "8a488f150cf529fc34d7db973f4e82058c511f040fb0379d9c11b0d0c48258a2",
    "extend/catalog.py": "5310073ba5db29aff3791740cec07702a2695a4978f0bf620ce0f12e6c7838dc",
    "extend/expander.py": "b575b5d7733829ecd948dbfd7c588884c6cec41fe1734736401403b9adb6bc19",
    "extend/stitch.py": "ddd4cfd9a1c2838c4133b932a7f3091231fa18cfa4299393198c411ea96698d5",
}
REPAIRED_HEAD_SHA256 = (
    "60d4bc10e53767f67cdef1759000d638f105d002219cd2a301bde9d98c7927c0"  # 8a7f76803
)
GATE_CUBE = "s3_00994_00494_01994_512"
LOST_MARGIN = 18  # finding 140's 190 = main's 172 + 18


def module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        f"vesuvius.afv_spline_generator.extend.{name}", path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def meeting(blocks) -> list[list[int]]:
    """For each block, the other blocks whose read box meets its own."""
    return [[j for j, (lo2, hi2, *_r) in enumerate(blocks) if j != i and np.all(lo2 < hi) and np.all(lo < hi2)]
            for i, (lo, hi, *_rest) in enumerate(blocks)]  # fmt: skip


def stitch_repaired(blocks, trim, reach_low_xyz, reach_high_xyz, black):
    """`cli.generate` with the repaired trim: every block's splines fitted, then each trimmed against its neighbours'."""
    from vesuvius.afv_spline_generator.cleanup import clean
    from vesuvius.afv_spline_generator.extend.stitch import Stitcher
    from vesuvius.afv_spline_generator.splines import extract_splines, threshold_to_u8

    fitted = []
    for low, high, origin, size, ct_block, field in blocks:
        black.add(ct_block, low)
        fitted.append(extract_splines(field(), threshold_to_u8(bs.THRESHOLD)))
    meets = meeting(blocks)
    with tempfile.TemporaryDirectory(prefix="afv-stitch-") as scratch:
        st = Stitcher(scratch)
        try:
            for i, (low, high, origin, size, _ct, _f) in enumerate(blocks):
                neighbours = [(family, np.asarray(points) + blocks[j][0][::-1], blocks[j][0][::-1], blocks[j][1][::-1])
                              for j in meets[i] for family, points in fitted[j]]  # fmt: skip
                traces = trim(
                    fitted[i],
                    low[::-1],
                    high[::-1],
                    reach_low_xyz[::-1],
                    reach_high_xyz[::-1],
                    neighbours,
                )
                st.add_block(f"block-{i}", low.tolist(), (high - low).tolist(), traces,
                             (np.asarray(origin), np.asarray(origin) + np.asarray(size)))  # fmt: skip
            traces = st.stitched()
        finally:
            st.close()
    return clean(traces, bs.MAX_JOIN_ANGLE, bs.MIN_LENGTH, black, bs.BLACK_DISTANCE)


def score(fibers, families, skel, reference, n) -> dict:
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing

    labels = afv_to_labels.rasterize({k: afv_to_labels.to_cube_zyx(v, (0, 0, 0)) for k, v in enumerate(fibers)},
                                     (n,) * 3)  # fmt: skip
    row = {
        f"tol{int(t)}": score_tracing(skel, labels, tolerance=t).as_row()
        for t in bs.TOLS
    }
    row["written"] = len(fibers)
    row["length"] = round(float(sum(bs.dense(f)[1][-1] for f in fibers)), 1)
    row["duplicated_share"] = round(bs.duplicated_share(fibers, families), 4)
    row["crossings"] = bs.crossing_kinds(
        bs.crossings(reference[0], reference[1], n), fibers, families
    )
    return row


def run(args) -> None:
    cubes, trim_key = SETS[args.set]
    if args.cube not in cubes:
        raise SystemExit(f"{args.cube} is not in set {args.set}")
    out_dir = args.out / args.set / args.cube
    if (out_dir / "result.json").exists():
        raise SystemExit(f"{out_dir / 'result.json'} exists: each cube runs once")
    fields = args.fields / args.cube
    recorded = json.loads((fields / "result.json").read_text())
    bs.load(
        args.pr, args.old_first
    )  # puts the #1934 head's package and ScrollGT on the path
    sc.scrollgt_on_path()
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    first, zone = (
        module(args.old_first, "stitch_first"),
        module(args.old_zone, "stitch_zone"),
    )
    repaired = module(args.repaired, "stitch_repaired")
    if args.set == "scroll3":
        import zarr

        ct = np.asarray(zarr.open(str(bs.CT / f"{args.cube}.zarr"), mode="r")[:])
        skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{args.cube}")

        def old_trim(traces, low, high, _reach_low, reach_high):
            return first.trim_cut_ends(traces, low, high, reach_high)
    else:
        ct, skel = sc.cube_image(args.cube), sc.ground_truth(args.cube)
        old_trim = zone.trim_cut_ends
    n = ct.shape[0]
    shape = np.asarray(ct.shape[::-1])

    def field_of(arm, i, sl):
        return np.load(fields / f"prob_real_{i}.npy")

    blocks = sc.blocks_of(cli, "real", ct, field_of)
    blocks = [(lo, hi, o, s, c, (lambda i=i: np.load(fields / f"prob_real_{i}.npy")))
              for i, (lo, hi, o, s, c, _f) in enumerate(blocks)]  # fmt: skip
    ref = np.load(fields / "one_main_fibers.npz")
    reference = ([ref["points"][a:b] for a, b in zip(ref["offsets"][:-1], ref["offsets"][1:], strict=True)],
                 [int(f) for f in ref["family"]])  # fmt: skip
    zero = np.zeros(3, int)
    rows = {}
    for arm, make in (
        (
            "main",
            lambda: xd.stitch_blocks(
                blocks, sc.untrimmed, zero, shape, ExteriorBlack(zero, shape), Catalog
            ),
        ),
        (
            "trim",
            lambda: xd.stitch_blocks(
                blocks, old_trim, zero, shape, ExteriorBlack(zero, shape), Catalog
            ),
        ),
        (
            "repaired",
            lambda: stitch_repaired(
                blocks, repaired.trim_cut_ends, zero, shape, ExteriorBlack(zero, shape)
            ),
        ),
    ):
        traces = make()
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        rows[arm] = score(fibers, families, skel, reference, n)
        r4 = rows[arm]["tol4"]
        print(f"{args.cube} {arm:8s} written {rows[arm]['written']:4d} dup {rows[arm]['duplicated_share']:.3f} "
              f"crossings {rows[arm]['crossings']} | t4 {r4['erl_merge_penalized']} m{r4['merges']}", flush=True)  # fmt: skip
    problems = []
    for arm, key in (("main", "real/main"), ("trim", trim_key)):
        if (
            json.loads(json.dumps(rows[arm])) != recorded["rows"][key]
        ):  # as the record stores it
            problems.append(f"{arm} does not reproduce the recorded {key} row")
    out = {"finding": 140, "set": args.set, "cube": args.cube, "size": n, "block": n // 2, "rows": rows,
           "reproduced": not problems, "problems": problems,
           "sha256": {"old_first": sha(args.old_first), "old_zone": sha(args.old_zone),
                      "repaired_stitch": sha(args.repaired)}}  # fmt: skip
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(out, indent=1))
    print(f"{args.cube}: {problems or 'reproduced'}", flush=True)


def zone_row(fibers, families, skel, dz) -> dict:
    """Finding 107's row for one variant of its 1024³ zone (`afv_generator_default_zone.run`'s, unchanged)."""
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing

    lo, hi = np.full(3, dz.PAD), np.full(3, dz.PAD + dz.SIZE)
    labels = afv_to_labels.rasterize({k: afv_to_labels.to_cube_zyx(v, (dz.PAD,) * 3) for k, v in enumerate(fibers)},
                                     (dz.SIZE,) * 3)  # fmt: skip
    inside = [bs.dense(f)[0] for f in fibers]
    inside = [p[np.all((p >= lo) & (p < hi), axis=1)] for p in inside]
    return {
        "zone": {
            "written": len(fibers),
            "length": round(float(sum(bs.dense(f)[1][-1] for f in fibers)), 1),
            "duplicated_share": round(bs.duplicated_share(fibers, families), 4),
        },
        "cube": {
            "written_inside": sum(len(p) > 0 for p in inside),
            "duplicated_share": round(dz.duplicated_share_in(fibers, families, lo, hi), 4),
            **{f"tol{int(t)}": score_tracing(skel, labels, tolerance=t).as_row() for t in bs.TOLS},
        },
    }  # fmt: skip


def zone(args) -> None:
    """Addendum 1: finding 107's 1024³ zone from its cached fields, main and its trim gated on its recorded rows."""
    import afv_generator_default_zone as dz

    out_file = args.out / "zone" / "result.json"
    if out_file.exists():
        raise SystemExit(f"{out_file} exists: the zone runs once")
    work = args.work  # finding 107's work directory, read only
    recorded = json.loads((work / "result.json").read_text())
    missing = [i for i in range(8) if not (work / f"prob_block_{i}.npy").exists()]
    if (
        missing
        or recorded["identity_problems"]
        or sha(args.old_zone) != dz.PATCHED_STITCH_SHA256
    ):
        raise SystemExit(f"gate failed: fields missing {missing}, identity {recorded['identity_problems']}, "
                         f"zone trim {sha(args.old_zone)[:16]}")  # fmt: skip
    bs.load(args.pr, args.old_zone)
    sc.scrollgt_on_path()
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    old, repaired = (
        module(args.old_zone, "stitch_zone"),
        module(args.repaired, "stitch_repaired"),
    )
    ct = np.load(work / "context.npy", mmap_mode="r")
    if dz.file_sha256(work / "context.npy") != recorded["context_sha256"]:
        raise SystemExit("gate failed: the scan is not finding 107's")
    shape_xyz = np.asarray(ct.shape[::-1])
    reach_low, reach_high = dz.read_box(shape_xyz)
    blocks = []
    for i, (origin, size, low, high) in enumerate(dz.block_crops(cli, shape_xyz)):
        sl = tuple(
            slice(int(a), int(b)) for a, b in zip(low[::-1], high[::-1], strict=True)
        )
        blocks.append((low, high, origin, size, np.asarray(ct[sl]),
                       (lambda i=i: np.load(work / f"prob_block_{i}.npy"))))  # fmt: skip
    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{dz.CUBE}")
    rows = {}
    for variant, make in (
        ("main", lambda: xd.stitch_blocks(blocks, sc.untrimmed, reach_low, reach_high,
                                          ExteriorBlack(reach_low, reach_high), Catalog)),
        ("patched", lambda: xd.stitch_blocks(blocks, old.trim_cut_ends, reach_low, reach_high,
                                             ExteriorBlack(reach_low, reach_high), Catalog)),
        ("repaired", lambda: stitch_repaired(blocks, repaired.trim_cut_ends, reach_low, reach_high,
                                             ExteriorBlack(reach_low, reach_high))),
    ):  # fmt: skip
        traces = make()
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        rows[variant] = zone_row(fibers, families, skel, dz)
        z, c = rows[variant]["zone"], rows[variant]["cube"]
        print(f"{variant:8s} zone written {z['written']} dup {z['duplicated_share']:.3f} | cube dup "
              f"{c['duplicated_share']:.3f} t2 {c['tol2']['erl_merge_penalized']} m{c['tol2']['merges']} "
              f"t4 {c['tol4']['erl_merge_penalized']} m{c['tol4']['merges']}", flush=True)  # fmt: skip
    problems = [f"{v} does not reproduce finding 107's row" for v in ("main", "patched")
                if json.loads(json.dumps(rows[v])) != recorded["rows"][v]]  # fmt: skip
    out = {"finding": 140, "addendum": 1, "cube": dz.CUBE, "zone": dz.ZONE, "block": dz.BLOCK, "rows": rows,
           "reproduced": not problems, "problems": problems,
           "sha256": {"old_zone": sha(args.old_zone), "repaired_stitch": sha(args.repaired),
                      "context": recorded["context_sha256"]}}  # fmt: skip
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, indent=1))
    print(f"zone: {problems or 'reproduced'}", flush=True)


def gain(row, base, tol="tol4") -> float:
    return row[tol]["erl_merge_penalized"] / base[tol]["erl_merge_penalized"] - 1


def summary(results: dict) -> dict:
    g = {c: gain(r["rows"]["repaired"], r["rows"]["main"]) for c, r in results.items()}
    g2 = {
        c: gain(r["rows"]["repaired"], r["rows"]["main"], "tol2")
        for c, r in results.items()
    }
    cov = {c: r["rows"]["repaired"]["tol4"]["coverage"] / r["rows"]["main"]["tol4"]["coverage"] - 1
           for c, r in results.items()}  # fmt: skip
    cov_trim = {c: r["rows"]["trim"]["tol4"]["coverage"] / r["rows"]["main"]["tol4"]["coverage"] - 1
                for c, r in results.items()}  # fmt: skip
    lost = {
        arm: sum(r["rows"][arm]["crossings"]["lost"] for r in results.values())
        for arm in ("main", "trim", "repaired")
    }
    return {
        "cubes": len(results),
        "up_tol4": sum(v > 0 for v in g.values()),
        "median_gain_tol4": round(statistics.median(g.values()), 4),
        "gain_tol4_range": [round(min(g.values()), 4), round(max(g.values()), 4)],
        "median_gain_tol2": round(statistics.median(g2.values()), 4),
        "merges_tol2": {
            arm: sum(r["rows"][arm]["tol2"]["merges"] for r in results.values())
            for arm in ("main", "trim", "repaired")
        },  # fmt: skip
        "duplicated_share_median": {
            arm: round(
                statistics.median(
                    r["rows"][arm]["duplicated_share"] for r in results.values()
                ),
                4,
            )
            for arm in ("main", "trim", "repaired")
        },  # fmt: skip
        "lost_crossings": lost,
        "coverage_tol4_median_change": {
            "trim": round(statistics.median(cov_trim.values()), 4),
            "repaired": round(statistics.median(cov.values()), 4),
        },  # fmt: skip
        "by_cube_gain_tol4": {c: round(v, 4) for c, v in g.items()},
    }


def verdict(s3: dict) -> str:
    if (
        s3["up_tol4"] >= UP_LINE
        and s3["median_gain_tol4"] >= KEEP_MEDIAN
        and s3["lost_crossings"]["repaired"] <= LOST_LINE
    ):
        return "REPAIR_KEEPS_THE_GAIN"
    if s3["median_gain_tol4"] < LOSE_MEDIAN or s3["up_tol4"] <= 5:
        return "REPAIR_LOSES_THE_GAIN"
    return "REPAIR_PARTLY"


def package_problems(old_src: Path, new_src: Path) -> list[str]:
    """Addendum 2's package gate: #1934's package file for file, but for #2434's four files."""
    old, new = (p / "vesuvius" / "afv_spline_generator" for p in (old_src, new_src))
    names = {p.relative_to(old).as_posix() for p in old.rglob("*.py")}
    found = {p.relative_to(new).as_posix() for p in new.rglob("*.py")}
    problems = [f"{n} missing from the #2434 package" for n in sorted(names - found)]
    problems += [f"{n} is not in #1934's package" for n in sorted(found - names)]
    for n in sorted(names & found):
        want = PACKAGE_2434_SHA256.get(n) or sha(old / n)
        if sha(new / n) != want:
            problems.append(f"{n} sha256 {sha(new / n)[:16]}, want {want[:16]}")
    return problems


def joins_a_shared_end() -> bool:
    """#2434's test case on the loaded stitcher: two splines meeting at one end point chain into one fiber."""
    from vesuvius.afv_spline_generator.extend.stitch import Stitcher

    def line(x0, x1):
        x = np.arange(x0, x1 + 0.25, 0.5)
        return np.stack([np.full_like(x, 48.0), np.full_like(x, 48.0), x], axis=1)

    with tempfile.TemporaryDirectory(prefix="afv-2434-") as scratch:
        st = Stitcher(scratch)
        try:
            st.add_block("block-0", [0, 0, 0], [320, 96, 96], [("V", line(10, 60)), ("V", line(60, 130))],
                         (np.zeros(3), np.array([320, 96, 96])))  # fmt: skip
            return len(list(st.chains())) == 1
        finally:
            st.close()


def gate_problems(gate_dir: Path, f140: dict) -> list[str]:
    """Addendum 2's reproduction gate: the gate cube rerun as finding 140 ran it."""
    path = gate_dir / "scroll3" / GATE_CUBE / "result.json"
    if not path.exists():
        return [f"{path} missing: the gate cube has not run"]
    g, recorded = json.loads(path.read_text()), f140["cubes"]["scroll3"][GATE_CUBE]
    problems = [f"gate: {p}" for p in g["problems"]]
    if g["rows"]["repaired"] != recorded["rows"]["repaired"]:
        problems.append("gate: repaired does not reproduce finding 140's row")
    if g["sha256"] != recorded["sha256"]:
        problems.append("gate: not the files finding 140 ran")
    return problems


def load_2434(args) -> None:
    """Gate the #2434 package and the repaired file, then put the package on the path."""
    f140 = json.loads(args.f140.read_text())
    problems = gate_problems(args.gate, f140) + package_problems(args.pr1934, args.pr)
    if sha(args.repaired) != REPAIRED_HEAD_SHA256:
        problems.append(
            f"repaired stitch.py sha256 {sha(args.repaired)[:16]}, not 8a7f76803's"
        )
    if problems:
        raise SystemExit("gate failed: " + "; ".join(problems))
    bs.load(args.pr, args.repaired)
    sc.scrollgt_on_path()
    if not joins_a_shared_end():
        raise SystemExit(
            "gate failed: the loaded stitcher does not join at a shared end point"
        )


def after2434(args) -> None:
    """Addendum 2: main and the repaired trim, both with #2434, on finding 140's cached fields."""
    cubes, _key = SETS[args.set]
    if args.cube not in cubes:
        raise SystemExit(f"{args.cube} is not in set {args.set}")
    out_dir = args.out / args.set / args.cube
    if (out_dir / "result.json").exists():
        raise SystemExit(f"{out_dir / 'result.json'} exists: each cube runs once")
    fields = args.fields / args.cube
    load_2434(args)
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    repaired = module(args.repaired, "stitch_repaired")
    if args.set == "scroll3":
        import zarr

        ct = np.asarray(zarr.open(str(bs.CT / f"{args.cube}.zarr"), mode="r")[:])
        skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{args.cube}")
    else:
        ct, skel = sc.cube_image(args.cube), sc.ground_truth(args.cube)
    n = ct.shape[0]
    shape = np.asarray(ct.shape[::-1])
    blocks = sc.blocks_of(
        cli, "real", ct, lambda arm, i, sl: np.load(fields / f"prob_real_{i}.npy")
    )
    blocks = [(lo, hi, o, s, c, (lambda i=i: np.load(fields / f"prob_real_{i}.npy")))
              for i, (lo, hi, o, s, c, _f) in enumerate(blocks)]  # fmt: skip
    ref = np.load(fields / "one_main_fibers.npz")
    reference = ([ref["points"][a:b] for a, b in zip(ref["offsets"][:-1], ref["offsets"][1:], strict=True)],
                 [int(f) for f in ref["family"]])  # fmt: skip
    zero = np.zeros(3, int)
    rows = {}
    for arm, make in (
        ("main", lambda: xd.stitch_blocks(blocks, sc.untrimmed, zero, shape, ExteriorBlack(zero, shape), Catalog)),
        ("repaired", lambda: stitch_repaired(blocks, repaired.trim_cut_ends, zero, shape, ExteriorBlack(zero, shape))),
    ):  # fmt: skip
        traces = make()
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        rows[arm] = score(fibers, families, skel, reference, n)
        r4 = rows[arm]["tol4"]
        print(f"{args.cube} {arm:8s} written {rows[arm]['written']:4d} dup {rows[arm]['duplicated_share']:.3f} "
              f"crossings {rows[arm]['crossings']} | t4 {r4['erl_merge_penalized']} m{r4['merges']}", flush=True)  # fmt: skip
    out = {"finding": 140, "addendum": 2, "set": args.set, "cube": args.cube, "size": n, "block": n // 2,
           "rows": rows, "sha256": {"repaired_stitch": sha(args.repaired), **PACKAGE_2434_SHA256}}  # fmt: skip
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(out, indent=1))


def zone2434(args) -> None:
    """Addendum 2 on finding 107's 1024³ zone: main and the repaired trim, both with #2434, described."""
    import afv_generator_default_zone as dz

    out_file = args.out / "zone" / "result.json"
    if out_file.exists():
        raise SystemExit(f"{out_file} exists: the zone runs once")
    work = args.work
    recorded = json.loads((work / "result.json").read_text())
    missing = [i for i in range(8) if not (work / f"prob_block_{i}.npy").exists()]
    if missing or recorded["identity_problems"]:
        raise SystemExit(
            f"gate failed: fields missing {missing}, identity {recorded['identity_problems']}"
        )
    load_2434(args)
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    repaired = module(args.repaired, "stitch_repaired")
    ct = np.load(work / "context.npy", mmap_mode="r")
    if dz.file_sha256(work / "context.npy") != recorded["context_sha256"]:
        raise SystemExit("gate failed: the scan is not finding 107's")
    shape_xyz = np.asarray(ct.shape[::-1])
    reach_low, reach_high = dz.read_box(shape_xyz)
    blocks = []
    for i, (origin, size, low, high) in enumerate(dz.block_crops(cli, shape_xyz)):
        sl = tuple(
            slice(int(a), int(b)) for a, b in zip(low[::-1], high[::-1], strict=True)
        )
        blocks.append((low, high, origin, size, np.asarray(ct[sl]),
                       (lambda i=i: np.load(work / f"prob_block_{i}.npy"))))  # fmt: skip
    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{dz.CUBE}")
    rows = {}
    for variant, make in (
        ("main", lambda: xd.stitch_blocks(blocks, sc.untrimmed, reach_low, reach_high,
                                          ExteriorBlack(reach_low, reach_high), Catalog)),
        ("repaired", lambda: stitch_repaired(blocks, repaired.trim_cut_ends, reach_low, reach_high,
                                             ExteriorBlack(reach_low, reach_high))),
    ):  # fmt: skip
        traces = make()
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        rows[variant] = zone_row(fibers, families, skel, dz)
        z, c = rows[variant]["zone"], rows[variant]["cube"]
        print(f"{variant:8s} zone written {z['written']} dup {z['duplicated_share']:.3f} | cube dup "
              f"{c['duplicated_share']:.3f} t2 {c['tol2']['erl_merge_penalized']} m{c['tol2']['merges']} "
              f"t4 {c['tol4']['erl_merge_penalized']} m{c['tol4']['merges']}", flush=True)  # fmt: skip
    out = {"finding": 140, "addendum": 2, "cube": dz.CUBE, "zone": dz.ZONE, "block": dz.BLOCK, "rows": rows,
           "sha256": {"repaired_stitch": sha(args.repaired), "context": recorded["context_sha256"],
                      **PACKAGE_2434_SHA256}}  # fmt: skip
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, indent=1))


def summary2434(results: dict, f140_cubes: dict) -> dict:
    """Repaired over main, both with #2434; and #2434's own effect on main against finding 140's main row."""
    g = {c: gain(r["rows"]["repaired"], r["rows"]["main"]) for c, r in results.items()}
    g2 = {
        c: gain(r["rows"]["repaired"], r["rows"]["main"], "tol2")
        for c, r in results.items()
    }
    on_main = {
        c: gain(r["rows"]["main"], f140_cubes[c]["rows"]["main"])
        for c, r in results.items()
    }
    cov = {c: r["rows"]["repaired"]["tol4"]["coverage"] / r["rows"]["main"]["tol4"]["coverage"] - 1
           for c, r in results.items()}  # fmt: skip
    arms = ("main", "repaired")
    return {
        "cubes": len(results),
        "up_tol4": sum(v > 0 for v in g.values()),
        "median_gain_tol4": round(statistics.median(g.values()), 4),
        "gain_tol4_range": [round(min(g.values()), 4), round(max(g.values()), 4)],
        "median_gain_tol2": round(statistics.median(g2.values()), 4),
        "merges_tol2": {a: sum(r["rows"][a]["tol2"]["merges"] for r in results.values()) for a in arms},
        "duplicated_share_median": {a: round(statistics.median(r["rows"][a]["duplicated_share"]
                                                               for r in results.values()), 4) for a in arms},
        "lost_crossings": {a: sum(r["rows"][a]["crossings"]["lost"] for r in results.values()) for a in arms},
        "coverage_tol4_median_change": round(statistics.median(cov.values()), 4),
        "main_change_from_2434_tol4_median": round(statistics.median(on_main.values()), 4),
        "by_cube_gain_tol4": {c: round(v, 4) for c, v in g.items()},
    }  # fmt: skip


def verdict2434(s3: dict) -> str:
    lost = s3["lost_crossings"]
    if (
        s3["up_tol4"] >= UP_LINE
        and s3["median_gain_tol4"] >= KEEP_MEDIAN
        and lost["repaired"] <= lost["main"] + LOST_MARGIN
    ):
        return "GAIN_HOLDS_AFTER_2434"
    if s3["median_gain_tol4"] < LOSE_MEDIAN or s3["up_tol4"] <= 5:
        return "GAIN_LOST_AFTER_2434"
    return "GAIN_PARTLY_AFTER_2434"


def record2434(args) -> None:
    """Addendum 2's record, written once: the gate, the verdict on Scroll 3, Scrolls 1 and 5, and the zone."""
    if args.record.exists():
        raise SystemExit(f"{args.record} exists: the record is written once")
    f140 = json.loads(args.f140.read_text())
    problems = gate_problems(args.gate, f140)
    results = {s: {p.parent.name: json.loads(p.read_text()) for p in sorted((args.out / s).glob("*/result.json"))}
               for s in SETS}  # fmt: skip
    missing = [
        f"{s}/{c}"
        for s, (cubes, _k) in SETS.items()
        for c in cubes
        if c not in results[s]
    ]
    zone_file = args.out / "zone" / "result.json"
    s3 = (
        summary2434(results["scroll3"], f140["cubes"]["scroll3"])
        if len(results["scroll3"]) == 8
        else None
    )
    record = {
        "finding": 140,
        "addendum": 2,
        "verdict": "DOES_NOT_RUN" if problems or missing or s3 is None else verdict2434(s3),
        "problems": problems,
        "missing": missing,
        "scroll3": s3,
        "confirm": summary2434(results["confirm"], f140["cubes"]["confirm"]) if results["confirm"] else None,
        "zone": json.loads(zone_file.read_text())["rows"] if zone_file.exists() else None,
        "lines": {"up": UP_LINE, "keep_median": KEEP_MEDIAN, "lose_median": LOSE_MEDIAN, "lost_margin": LOST_MARGIN},
        "sha256": {"patch_2434": PATCH_2434_SHA256, "repaired_stitch": REPAIRED_HEAD_SHA256, **PACKAGE_2434_SHA256},
        "cubes": results,
    }  # fmt: skip
    args.record.write_text(json.dumps(record, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: record[k]
                for k in ("verdict", "problems", "missing", "scroll3", "confirm")
            },
            indent=1,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("set", choices=sorted(SETS))
    r.add_argument("cube")
    for name in (
        "--fields",
        "--out",
        "--pr",
        "--old-first",
        "--old-zone",
        "--repaired",
    ):
        r.add_argument(name, type=Path, required=True)
    z = sub.add_parser("zone")
    for name in ("--work", "--out", "--pr", "--old-zone", "--repaired"):
        z.add_argument(name, type=Path, required=True)
    v = sub.add_parser("verdict")
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--record", type=Path, required=True)
    gated = ("--out", "--pr", "--pr1934", "--repaired", "--gate", "--f140")
    a2 = sub.add_parser("after2434")
    a2.add_argument("set", choices=sorted(SETS))
    a2.add_argument("cube")
    for name in ("--fields", *gated):
        a2.add_argument(name, type=Path, required=True)
    z2 = sub.add_parser("zone2434")
    for name in ("--work", *gated):
        z2.add_argument(name, type=Path, required=True)
    r2 = sub.add_parser("record2434")
    for name in ("--out", "--gate", "--f140", "--record"):
        r2.add_argument(name, type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
        return
    if a.cmd == "zone":
        zone(a)
        return
    if a.cmd in ("after2434", "zone2434", "record2434"):
        {"after2434": after2434, "zone2434": zone2434, "record2434": record2434}[a.cmd](
            a
        )
        return
    results = {s: {p.parent.name: json.loads(p.read_text()) for p in sorted((a.out / s).glob("*/result.json"))}
               for s in SETS}  # fmt: skip
    problems = [
        f"{s}/{c}: {p}"
        for s, rs in results.items()
        for c, r in rs.items()
        for p in r["problems"]
    ]
    missing = [
        f"{s}/{c}"
        for s, (cubes, _k) in SETS.items()
        for c in cubes
        if c not in results[s]
    ]
    s3 = (
        summary(results["scroll3"])
        if len(results["scroll3"]) == len(SETS["scroll3"][0])
        else None
    )
    record = {
        "finding": 140,
        "verdict": "DOES_NOT_RUN" if problems or missing or s3 is None else verdict(s3),
        "problems": problems,
        "missing": missing,
        "scroll3": s3,
        "confirm": summary(results["confirm"]) if results["confirm"] else None,
        "lines": {
            "up": UP_LINE,
            "keep_median": KEEP_MEDIAN,
            "lose_median": LOSE_MEDIAN,
            "lost": LOST_LINE,
        },
        "cubes": results,
    }
    if a.record.exists():
        raise SystemExit(f"{a.record} exists: the record is written once")
    a.record.write_text(json.dumps(record, indent=1) + "\n")
    print(
        json.dumps(
            {
                k: record[k]
                for k in ("verdict", "problems", "missing", "scroll3", "confirm")
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
