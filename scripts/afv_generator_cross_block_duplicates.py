"""Suppressing a block's copy of a fiber another block also fitted, on top of the seam trim (finding 108's run).

villa's catalogue suppresses a source from another block only when `strict_duplicate` matches it: full containment
within a median 0.20 voxel. Two blocks' copies of one fiber, each fitted to a field its block predicted from its own
crop, lie a few tenths of a voxel apart where both blocks read it, so both are written. The change
(`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`, on top of the seam trim) also suppresses,
for sources of different blocks, a copy that `compare()` classifies as a duplicate (full containment within a median
1.5 voxels).

`run` stitches finding 106's eight held-out Scroll-3 cubes from its cached per-block fields (arm real: 8 blocks of 256,
each predicted from its own crop), with the amended seam trim (`trim`) and with the trim and the change (`trim+dup`),
scored as finding 106 scored them. `zone` does the same on finding 107's 1024³ zone at block 512 from its cached
fields. `verdict` applies the registered rule.

Usage (the generator's venv):
  python -I scripts/afv_generator_cross_block_duplicates.py run --cube CUBE --fields DIR --work DIR --pr PR_SRC \
      --villa VILLA --main REV --patched-stitch PATH --patched-catalog PATH
  python -I scripts/afv_generator_cross_block_duplicates.py zone --zone-work DIR --work DIR --pr PR_SRC --villa VILLA \
      --main REV --patched-stitch PATH --patched-catalog PATH
  python -I scripts/afv_generator_cross_block_duplicates.py verdict --work DIR --out RECORD
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
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_generator_block_seams as bs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD_106 = ROOT / "reports/afv_generator_block_seams.json"
RECORD_107 = ROOT / "reports/afv_generator_default_zone.json"
PATCH = (
    ROOT / "repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch"
)
VARIANTS = ("trim", "trim+dup")
# The cube at the centre of finding 107's zone, whose zone-wide doubling (no ground truth) the change was diagnosed on.
DIAGNOSED = "s3_04494_00994_01494_512"
CATALOG = "vesuvius/src/vesuvius/fiber_spline_generator/extend/catalog.py"
CALL = (
    "            if dup is None and np.all(slo>=llo-ov.MAX_P90) and np.all(shi<=lhi+ov.MAX_P90):\n"
    "                dup = cross_block_duplicate(sp,lp)\n"
)
COMMENT = (
    "            # Other contained neighbours are kept: compare() classifies them as\n"
    "            # duplicate, but only the two tests above may suppress them.\n",
    "            # Reject proximity-only contained neighbours; compare() classifies\n"
    "            # these as duplicate but only strict_duplicate may suppress them.\n",
)


def catalog_problems(villa: Path, rev: str, patched_catalog: Path) -> list[str]:
    """The patched catalog.py must be villa main's plus `cross_block_duplicate`, its call and the comment; nothing else."""
    main = subprocess.run(["git", "-C", str(villa), "show", f"{rev}:{CATALOG}"], capture_output=True, check=True,
                          text=True).stdout  # fmt: skip
    text = patched_catalog.read_text()
    start, end = text.find("def cross_block_duplicate("), text.find("SCHEMA = '''")
    if not 0 <= start < end or text.count(CALL) != 1 or text.count(COMMENT[0]) != 1:
        return [
            "the patched catalog.py has no cross_block_duplicate, call or comment where the patch puts them"
        ]
    restored = (text[:start] + text[end:]).replace(CALL, "").replace(*COMMENT)
    if restored != main:
        return [
            "the patched catalog.py changes more than cross_block_duplicate and its call"
        ]
    # The function itself must be the patch's: its added catalogue lines, less the call and the comment.
    added = [line[1:] for line in catalog_patch_lines() if line.startswith("+")]
    function = [
        line
        for line in added
        if line not in CALL.splitlines() + COMMENT[0].splitlines()
    ]
    if text[start:end].splitlines() != function:
        return ["the patched catalog.py's cross_block_duplicate is not the patch's"]
    return []


def catalog_patch_lines() -> list[str]:
    """The catalog.py hunks' + and - lines of the patch under test."""
    out, current = [], None
    for line in PATCH.read_text().splitlines():
        if line.startswith("diff --git"):
            current = line.rsplit("/", 1)[1]
        elif (
            current == "catalog.py"
            and line[:1] in "+-"
            and line[:3] not in ("+++", "---")
        ):
            out.append(line)
    return out


def load(pr_src: Path, patched_stitch: Path, patched_catalog: Path):
    """The PR head's package, the amended trim, and the patched catalogue module beside the head's own."""
    trim_cut_ends, cut_end = bs.load(pr_src, patched_stitch)
    spec = importlib.util.spec_from_file_location(
        "vesuvius.afv_spline_generator.extend.catalog_patched", patched_catalog
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return trim_cut_ends, cut_end, mod


def stitch_blocks(
    blocks, trim_cut_ends, reach_low_xyz, reach_high_xyz, black, catalog_cls
):
    """Stitch (low_xyz, high_xyz, origin, size, field) blocks as `cli.generate` does, with the trim on every block."""
    from vesuvius.afv_spline_generator.cleanup import clean
    from vesuvius.afv_spline_generator.extend import stitch
    from vesuvius.afv_spline_generator.splines import extract_splines, threshold_to_u8

    original = stitch.Catalog
    stitch.Catalog = catalog_cls  # Stitcher builds its catalogue from this module name
    try:
        with tempfile.TemporaryDirectory(prefix="afv-stitch-") as scratch:
            st = stitch.Stitcher(scratch)
            try:
                for i, (low, high, origin, size, ct_block, field) in enumerate(blocks):
                    black.add(ct_block, low)
                    traces = extract_splines(field(), threshold_to_u8(bs.THRESHOLD))
                    traces = trim_cut_ends(
                        traces,
                        low[::-1],
                        high[::-1],
                        reach_low_xyz[::-1],
                        reach_high_xyz[::-1],
                    )
                    st.add_block(f"block-{i}", low.tolist(), (high - low).tolist(), traces,
                                 (np.asarray(origin), np.asarray(origin) + np.asarray(size)))  # fmt: skip
                traces = st.stitched()
            finally:
                st.close()
    finally:
        stitch.Catalog = original
    return clean(traces, bs.MAX_JOIN_ANGLE, bs.MIN_LENGTH, black, bs.BLACK_DISTANCE)


def run(args) -> None:
    import zarr

    trim_cut_ends, cut_end, patched = load(
        args.pr, args.patched_stitch, args.patched_catalog
    )
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    c = args.cube
    n = int(c.rsplit("_", 1)[1])
    fields = args.fields / c
    problems = bs.identity(args.pr, args.villa, args.main, args.patched_stitch)
    problems += catalog_problems(args.villa, args.main, args.patched_catalog)
    f106 = json.loads(RECORD_106.read_text())["cubes"][c]
    if f106["identity_problems"] or f106["settings"]["revision"] != bs.REVISION:
        problems.append(
            "finding 106's record of this cube has identity problems or another model revision"
        )
    ct = np.asarray(zarr.open(str(bs.CT / f"{c}.zarr"), mode="r")[:])
    shape_xyz = np.asarray(ct.shape[::-1])
    z = np.load(fields / "one_main_fibers.npz")
    o = z["offsets"]
    reference = (
        [z["points"][o[i] : o[i + 1]] for i in range(len(o) - 1)],
        [int(f) for f in z["family"]],
    )
    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{c}")
    out = {
        "cube": c,
        "size": n,
        "block": n // 2,
        "cut_end": cut_end,
        "identity_problems": problems,
        "rows": {},
    }
    for variant in args.variants:
        blocks = []
        for i, (origin, size) in enumerate(
            cli.zone_blocks([0, 0, 0], list(shape_xyz), n // 2)
        ):
            low = np.maximum(np.asarray(origin) - cli.BLOCK_MARGIN, 0)
            high = np.minimum(
                np.asarray(origin) + np.asarray(size) + cli.BLOCK_MARGIN, shape_xyz
            )
            sl = tuple(
                slice(int(a), int(b))
                for a, b in zip(low[::-1], high[::-1], strict=True)
            )
            blocks.append(
                (
                    low,
                    high,
                    origin,
                    size,
                    ct[sl],
                    lambda i=i: np.load(fields / f"prob_real_{i}.npy"),
                )
            )
        black = ExteriorBlack(np.zeros(3, int), shape_xyz)
        catalog_cls = patched.Catalog if variant == "trim+dup" else Catalog
        traces = stitch_blocks(
            blocks, trim_cut_ends, np.zeros(3, int), shape_xyz, black, catalog_cls
        )
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
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
        out["rows"][variant] = row
        print(f"{c} {variant:8s} written {row['written']:4d} dup {row['duplicated_share']:.3f} crossings "
              f"{row['crossings']} | t2 {row['tol2']['erl_merge_penalized']} m{row['tol2']['merges']} | "
              f"t4 {row['tol4']['erl_merge_penalized']} m{row['tol4']['merges']}", flush=True)  # fmt: skip
    if out["rows"]["trim"] != f106["rows"]["real/patched"]:
        problems.append(
            "the trim arm does not reproduce finding 106's real/patched row"
        )
    out["patched_stitch_sha256"] = hashlib.sha256(
        args.patched_stitch.read_bytes()
    ).hexdigest()
    out["patched_catalog_sha256"] = hashlib.sha256(
        args.patched_catalog.read_bytes()
    ).hexdigest()
    out["villa_main"] = args.main
    if tuple(args.variants) != VARIANTS:
        print(
            f"{c}: smoke ({args.variants}), not written; identity problems {problems or 'none'}",
            flush=True,
        )
        return
    args.work.mkdir(parents=True, exist_ok=True)
    (args.work / f"{c}.json").write_text(json.dumps(out, indent=1))
    print(f"{c}: identity problems {problems or 'none'}", flush=True)


def zone(args) -> None:
    """Finding 107's zone at block 512 from its cached fields: reported beside the verdict, not deciding."""
    import afv_generator_default_zone as dz

    trim_cut_ends, cut_end, patched = load(
        args.pr, args.patched_stitch, args.patched_catalog
    )
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing
    from scrollgt.fibers.target import load_fiber_target
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog

    problems = bs.identity(args.pr, args.villa, args.main, args.patched_stitch)
    problems += catalog_problems(args.villa, args.main, args.patched_catalog)
    f107 = json.loads(RECORD_107.read_text())["result"]
    ct = np.load(args.zone_work / "context.npy", mmap_mode="r")
    if dz.file_sha256(args.zone_work / "context.npy") != f107["context_sha256"]:
        problems.append("the zone's scan is not finding 107's")
    shape_xyz = np.asarray(ct.shape[::-1])
    reach_low, reach_high = dz.read_box(shape_xyz)
    crops = dz.block_crops(cli, shape_xyz)
    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{dz.CUBE}")
    lo, hi = np.full(3, dz.PAD), np.full(3, dz.PAD + dz.SIZE)
    out = {
        "cube": dz.CUBE,
        "zone": dz.ZONE,
        "block": dz.BLOCK,
        "identity_problems": problems,
        "rows": {},
    }
    for variant in args.variants:
        blocks = []
        for i, (origin, size, low, high) in enumerate(crops):
            sl = tuple(
                slice(int(a), int(b))
                for a, b in zip(low[::-1], high[::-1], strict=True)
            )
            blocks.append((low, high, origin, size, np.asarray(ct[sl]),
                           lambda i=i: np.load(args.zone_work / f"prob_block_{i}.npy")))  # fmt: skip
        black = ExteriorBlack(reach_low, reach_high)
        catalog_cls = patched.Catalog if variant == "trim+dup" else Catalog
        traces = stitch_blocks(
            blocks, trim_cut_ends, reach_low, reach_high, black, catalog_cls
        )
        fibers = [np.asarray(t["points"], np.float64) for t in traces]
        families = [int(t["family"]) for t in traces]
        labels = afv_to_labels.rasterize(
            {
                k: afv_to_labels.to_cube_zyx(v, (dz.PAD,) * 3)
                for k, v in enumerate(fibers)
            },
            (dz.SIZE,) * 3,
        )
        inside = [bs.dense(f)[0] for f in fibers]
        inside = [p[np.all((p >= lo) & (p < hi), axis=1)] for p in inside]
        row = {
            "zone": {"written": len(fibers), "length": round(float(sum(bs.dense(f)[1][-1] for f in fibers)), 1),
                     "duplicated_share": round(bs.duplicated_share(fibers, families), 4)},
            "cube": {"written_inside": sum(len(p) > 0 for p in inside),
                     "duplicated_share": round(dz.duplicated_share_in(fibers, families, lo, hi), 4),
                     **{f"tol{int(t)}": score_tracing(skel, labels, tolerance=t).as_row() for t in bs.TOLS}},
        }  # fmt: skip
        out["rows"][variant] = row
        print(f"zone {variant:8s} {json.dumps(row['zone'])} | t4 {row['cube']['tol4']['erl_merge_penalized']}",
              flush=True)  # fmt: skip
    if out["rows"]["trim"] != f107["rows"]["patched"]:
        problems.append("the trim arm does not reproduce finding 107's patched row")
    if tuple(args.variants) != VARIANTS:
        print(
            f"zone: smoke ({args.variants}), not written; identity problems {problems or 'none'}",
            flush=True,
        )
        return
    args.work.mkdir(parents=True, exist_ok=True)
    (args.work / "zone.json").write_text(json.dumps(out, indent=1))
    print(f"zone: identity problems {problems or 'none'}", flush=True)


def gain(rows: dict, tol: str) -> float:
    return (
        rows["trim+dup"][tol]["erl_merge_penalized"]
        / rows["trim"][tol]["erl_merge_penalized"]
        - 1
    )


def verdict(results: dict) -> dict:
    """The registered decision rule, over the eight held-out cubes."""
    rows = [results[c]["rows"] for c in bs.HELD_OUT]
    g4 = [gain(r, "tol4") for r in rows]
    merges = [sum(r[v]["tol2"]["merges"] for r in rows) for v in VARIANTS]
    dup = [statistics.median(r[v]["duplicated_share"] for r in rows) for v in VARIANTS]
    checks = {
        "P1_tol4_up": [sum(x > 0 for x in g4), sum(x > 0 for x in g4) >= 6],
        "P2_median_gain_tol4": [
            round(statistics.median(g4), 4),
            statistics.median(g4) >= 0.03,
        ],
        "P3_merges_tol2": [merges, merges[1] <= 1.05 * merges[0]],
        "P4_median_duplicated_share": [
            [round(d, 4) for d in dup],
            dup[1] <= 0.7 * dup[0],
        ],
    }
    held = {k: v[1] for k, v in checks.items()}
    if any(results[c]["identity_problems"] for c in bs.HELD_OUT):
        decision = "NO_VERDICT"
    elif not (held["P1_tol4_up"] and held["P3_merges_tol2"]):
        decision = "NOT_SUPPORTED"
    elif not (held["P2_median_gain_tol4"] and held["P4_median_duplicated_share"]):
        decision = "PARTIAL"
    else:
        decision = "SUPPORTED"
    return {"decision": decision, **checks}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "zone"):
        p = sub.add_parser(name)
        if name == "run":
            p.add_argument("--cube", required=True)
            p.add_argument("--fields", type=Path, required=True)
        else:
            p.add_argument("--zone-work", type=Path, required=True)
        p.add_argument("--work", type=Path, required=True)
        p.add_argument("--pr", type=Path, required=True)
        p.add_argument("--villa", type=Path, required=True)
        p.add_argument("--main", required=True)
        p.add_argument("--patched-stitch", type=Path, required=True)
        p.add_argument("--patched-catalog", type=Path, required=True)
        # The smoke before registration runs `trim` alone: it reproduces a recorded row and sees nothing of the change.
        p.add_argument(
            "--variants", type=lambda s: tuple(s.split(",")), default=VARIANTS
        )
    v = sub.add_parser("verdict")
    v.add_argument("--work", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
    elif args.cmd == "zone":
        zone(args)
    else:
        if args.out.exists():
            raise SystemExit(f"{args.out} exists: the record is written once")
        results = {
            c: json.loads((args.work / f"{c}.json").read_text()) for c in bs.HELD_OUT
        }
        record = {"verdict": verdict(results), "cubes": results}
        zone_file = args.work / "zone.json"
        if zone_file.exists():
            record["zone"] = json.loads(zone_file.read_text())
        args.out.write_text(json.dumps(record, indent=1) + "\n")
        print(json.dumps(record["verdict"], indent=1))


if __name__ == "__main__":
    main()
