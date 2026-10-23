"""docs/preregistration/2026-10-23_tracing_context.md -- is the neural tracer's tolerance-4 deficit on the 256³
in-sample cubes the tracing context of a 256³ run? Both tracers, and the mask model under ours, run on the 24 octants
of the three in-sample 512³ cubes as cubes in their own right. They are scored exactly as finding 95 scored its crops
of the whole-cube runs, against the same crop of the ground truth.

  prepare  each octant as a stand-in cube named by its absolute origin, so bench_cli's loader places it:
           DATA/<stem>_image.tif (the parent's CT, cropped) and DATA/<stem>.nml (the parent's annotation, which the
           loader localizes to the stem), with no probability: `bench_cli trace` runs the mask model on the octant, as
           it did on every real cube. Its CT for the neural tracer is CT/<stem>.zarr/0, written from the same crop
           after finding 85's array for the parent is checked equal to the parent's TIFF. The smoke cube is copied
           whole, without its probability cache.
  stems    the chain's list: each stand-in stem with its parent.
  smoke    the identity checks on the smoke cube: the recomputed probability, our tracer's labelling and the neural
           tracer's .afv must each equal the published one. Exit 0 only if all three do.
  score    every octant run at tolerances 4 and 2 against finding 95's crop of the ground truth, beside finding 95's
           crop rows; the registered predictions and decision rule. Writes reports/tracing_context.json.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_to_labels  # noqa: E402
import neural_tracer_analysis as f91  # noqa: E402
import octant_crop_rescore as f95  # noqa: E402
import tolerance4_rescore as t4  # noqa: E402

PEN = f91.PEN
SIZE = f95.SIZE
PARENTS = f95.CUBES
OCTANTS = f95.OCTANTS
TOLS = f95.TOLS
ENTRANTS = ("neural", "tracer")
SMOKE = "s5_07997_02997_05497_256"
SRC = Path(
    "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/fiber_skeletons"
)
G = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen")
NEURAL_RUN = f95.NEURAL
MIN_SCORED = 20  # of 24, scored for both tracers, or INCOMPLETE
P2_BAND = (
    0.90,
    1.10,
)  # each tracer's median, octant run over finding 95's crop, at tolerance 4
SAME_GT = (
    "n_gt_fibers",
    "gt_length",
)  # a row's ground truth, which must be finding 95's crop


def stand_in(parent: str, origin, size: int = SIZE) -> str:
    """The stem of the octant of `parent` at `origin` (z, y, x): its absolute origin, zero-padded as the cube stems."""
    from vesuvius_autoresearch.fibers.skeleton_io import origin_from_stem

    scroll = parent.split("_")[0]
    z, y, x = (
        int(a) + int(b) for a, b in zip(origin_from_stem(parent), origin, strict=False)
    )
    return f"{scroll}_{z:05d}_{y:05d}_{x:05d}_{size}"


def octant_key(parent: str, origin) -> str:
    """Finding 95's row key."""
    return f"{parent}@{origin[0]}_{origin[1]}_{origin[2]}"


def stems(
    parents=PARENTS, octants=OCTANTS, size: int = SIZE
) -> list[tuple[str, str, tuple[int, int, int]]]:
    out = [(stand_in(p, o, size), p, o) for p in parents for o in octants]
    names = [s for s, _, _ in out]
    if len(set(names)) != len(names) or set(names) & set(f91.ALL) or SMOKE in names:
        raise ValueError("a stand-in stem repeats or names a real cube")
    return out


def crop(volume: np.ndarray, origin, size: int = SIZE) -> np.ndarray:
    z, y, x = origin
    c = np.ascontiguousarray(volume[z : z + size, y : y + size, x : x + size])
    if c.shape != (size,) * 3:
        raise ValueError(f"octant at {origin} is {c.shape}, not {size}³")
    return c


def _replace_from_tmp(path: Path, write) -> None:
    """Write through `write(tmp_path)` beside PATH, then rename it into place. mkstemp's 0600 becomes the mode a new
    file gets from the umask, or the replaced file's (tests/test_file_modes.py)."""
    from vesuvius_autoresearch.core.file_modes import replacement_mode

    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    try:
        write(Path(tmp))
        os.chmod(tmp, replacement_mode(path))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_image(path: Path, image: np.ndarray) -> None:
    """A TIFF bench_cli reads back identical. One already there must already be identical (a resume)."""
    import tifffile

    if path.exists():
        if not np.array_equal(tifffile.imread(path), image):
            raise FileExistsError(f"{path} differs from the crop it should hold")
        return
    _replace_from_tmp(path, lambda t: tifffile.imwrite(t, image))


def write_ct(out: Path, image: np.ndarray) -> None:
    """OUT/0: the CT as a zarr v2 uint8 array (blosc lz4, 128³ chunks), as finding 85 and finding 92 wrote theirs;
    built beside OUT and renamed. One already there must already be identical."""
    import zarr
    from numcodecs import Blosc

    from vesuvius_autoresearch.core.file_modes import current_umask

    if out.exists():
        if not np.array_equal(zarr.open(str(out / "0"), mode="r")[...], image):
            raise FileExistsError(f"{out} differs from the crop it should hold")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix=f".{out.name}.building-", dir=out.parent))
    try:
        arr = zarr.open(str(build / "0"), mode="w-", shape=image.shape, chunks=(128, 128, 128), dtype="u1",
                        compressor=Blosc(cname="lz4", clevel=5, shuffle=Blosc.SHUFFLE))  # fmt: skip
        arr[...] = image
        # mkdtemp's 0700 -> a new directory's mode
        os.chmod(build, 0o777 & ~current_umask())
        build.rename(out)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise


def copy_exact(src: Path, dst: Path) -> None:
    if dst.exists():
        if dst.read_bytes() != src.read_bytes():
            raise FileExistsError(f"{dst} differs from {src}")
        return
    _replace_from_tmp(dst, lambda t: shutil.copyfile(src, t))


def prepare(data: Path, ct: Path, src: Path = SRC, zarrs: Path = G / "zarr", parents=PARENTS, octants=OCTANTS,
            size: int = SIZE) -> dict:  # fmt: skip
    import tifffile
    import zarr

    # Nothing here writes a probability: every *_fiberprob.npy in DATA is bench_cli's own, on that cube's image.
    data.mkdir(parents=True, exist_ok=True)
    ct.mkdir(parents=True, exist_ok=True)
    for parent in parents:
        image = tifffile.imread(src / f"{parent}_image.tif")
        if not np.array_equal(
            zarr.open(str(zarrs / f"{parent}.zarr"), mode="r")[...], image
        ):
            raise SystemExit(f"finding 85's array for {parent} differs from its TIFF")
        for stem, p, o in stems(parents, octants, size):
            if p != parent:
                continue
            c = crop(image, o, size)
            write_image(data / f"{stem}_image.tif", c)
            copy_exact(src / f"{parent}.nml", data / f"{stem}.nml")
            write_ct(ct / f"{stem}.zarr", c)
            print(f"PREPARED {stem} <- {octant_key(parent, o)}", flush=True)
    copy_exact(src / f"{SMOKE}_image.tif", data / f"{SMOKE}_image.tif")
    copy_exact(src / f"{SMOKE}.nml", data / f"{SMOKE}.nml")
    link = ct / f"{SMOKE}.zarr" / "0"
    if not link.is_symlink():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(
            zarrs / f"{SMOKE}.zarr"
        )  # finding 91's CT for the smoke cube, as its chain linked it
    return {"stems": [s for s, _, _ in stems(parents, octants, size)], "smoke": SMOKE}


def smoke_problems(
    prob, published_prob, labels, published_labels, afv_same: bool
) -> list[str]:
    """The three identity checks, in the chain's order. Empty means the octants may run."""
    out = []
    if prob.shape != published_prob.shape or not np.array_equal(prob, published_prob):
        diff = (
            float(np.max(np.abs(prob.astype(float) - published_prob.astype(float))))
            if prob.shape == published_prob.shape
            else None
        )
        out.append(f"probability differs from the published cache (max |diff| {diff})")
    if labels.shape != published_labels.shape or not np.array_equal(
        labels, published_labels
    ):
        out.append("our tracer's labelling differs from finding 94's")
    if not afv_same:
        out.append("the neural tracer's .afv differs from finding 91's")
    return out


def afv_identical(a: Path, b: Path) -> bool:
    """The same fibers point for point, whatever their ids (as finding 93's smoke compared them)."""

    def fibers(p):
        return sorted(
            np.ascontiguousarray(v, "<f8").tobytes()
            for v in afv_to_labels.read_afv(p).values()
        )

    return fibers(a) == fibers(b)


def verdict(rows: dict, crops: dict) -> dict:
    """The registered predictions and decision rule. rows: key -> entrant -> tolerance -> row, for each octant scored
    for both tracers; crops: finding 95's rows (its JSON's "octants", tolerances as strings)."""
    keys = [k for k, r in rows.items() if all(r.get(e, {}).get(4.0) for e in ENTRANTS)]
    n = len(keys)
    leads = sum(rows[k]["neural"][4.0][PEN] > rows[k]["tracer"][4.0][PEN] for k in keys)
    leads2 = sum(
        rows[k]["neural"][2.0][PEN] > rows[k]["tracer"][2.0][PEN] for k in keys
    )
    out: dict = {
        "scored": n,
        "neural_leads_at_4": [leads, n],
        "neural_leads_at_2": [leads2, n],
    }
    if zero := [(k, e) for k in keys for e in ENTRANTS if crops[k][e]["4.0"][PEN] <= 0]:
        raise ValueError(f"no ratio over a crop score of 0: {zero}")
    medians = {
        e: (statistics.median(rows[k][e][4.0][PEN] / crops[k][e]["4.0"][PEN] for k in keys) if keys else None)
        for e in ENTRANTS
    }  # fmt: skip
    out["median_run_over_crop_at_4"] = medians
    if n < MIN_SCORED:
        out.update(prediction_P1=None, prediction_P2=None, reading=None)
        return out
    lo, hi = P2_BAND
    out["prediction_P1"] = 3 * leads >= 2 * n
    out["prediction_P2"] = all(lo <= medians[e] <= hi for e in ENTRANTS)
    if 3 * leads >= 2 * n:
        out["reading"] = ("not the tracing context: run on the octants, the neural tracer keeps its tolerance-4 lead, "
                          "so what remains for the 256³ in-sample deficit is those cubes' own content and annotation")  # fmt: skip
    elif 3 * leads <= n:
        out["reading"] = ("the tracing context reproduces it: run on the octants as cubes, the neural tracer trails our "
                          "tracer at tolerance 4 as on the real 256³ cubes")  # fmt: skip
    else:
        out["reading"] = (
            "inconclusive: running small weakens the lead without reversing it"
        )
    return out


def outcome(identity: dict, rows: dict, crops: dict):
    if any(identity.values()):
        return "IDENTITY_FAILED", None
    v = verdict(rows, crops)
    return ("OK" if v["prediction_P1"] is not None else "INCOMPLETE"), v


def octant_labels(work: Path, stem: str) -> dict:
    """Each entrant's labelling of one octant run, or None where the run wrote nothing."""
    out: dict = {"neural": None, "tracer": None}
    afv = work / "neural" / stem / "fibers.afv"
    if afv.exists():
        fibers = {
            k: afv_to_labels.to_cube_zyx(v, (0, 0, 0))
            for k, v in afv_to_labels.read_afv(afv).items()
        }
        out["neural"] = afv_to_labels.rasterize(fibers, (SIZE,) * 3)
    inst = work / "tracer" / f"{stem}_instances.npy"
    if inst.exists():
        lab = np.load(inst)
        out["tracer"] = lab if lab.shape == (SIZE,) * 3 else None
    return out


def cmd_smoke(work: Path) -> int:
    data = work / "data"
    prob = data / f"{SMOKE}_fiberprob.npy"
    inst = work / "tracer" / f"{SMOKE}_instances.npy"
    afv = work / "neural" / SMOKE / "fibers.afv"
    if missing := [str(p) for p in (prob, inst, afv) if not p.exists()]:
        problems = [f"missing: {', '.join(missing)}"]
    else:
        problems = smoke_problems(
            np.load(prob),
            np.load(SRC / f"{SMOKE}_fiberprob.npy"),
            np.load(inst),
            np.load(t4.tracer_labelling(SMOKE)),
            afv_identical(afv, NEURAL_RUN / SMOKE / "fibers.afv"),
        )
    (work / "smoke.json").write_text(
        json.dumps({"cube": SMOKE, "problems": problems}, indent=1) + "\n"
    )
    print("SMOKE_OK" if not problems else "SMOKE_FAILED: " + "; ".join(problems))
    return 0 if not problems else 1


def cmd_score(work: Path, crops_path: Path, out_path: Path) -> int:
    sys.path.insert(0, str(f91.SG / "src"))
    from scrollgt.fibers.eval_trace import SCORING_VERSION, score_tracing
    from scrollgt.fibers.target import load_fiber_target

    if SCORING_VERSION != 3:
        raise SystemExit(
            f"registered against ScrollGT scoring version 3, found {SCORING_VERSION}"
        )
    crops = json.loads(crops_path.read_text())["octants"]
    smoke = json.loads((work / "smoke.json").read_text())
    rows: dict = {}
    failed: list[str] = []
    identity: dict = {}
    if smoke["problems"]:
        identity["smoke"] = smoke["problems"]
    for parent in PARENTS:
        skel, _, _ = load_fiber_target(f91.SG / "data" / f"fibers_{parent}")
        for o in OCTANTS:
            key, stem = octant_key(parent, o), stand_in(parent, o)
            labels = octant_labels(work, stem)
            if any(v is None for v in labels.values()):
                failed.append(
                    f"{key} ({stem}): "
                    + ", ".join(e for e, v in labels.items() if v is None)
                )
                continue
            sk = f95.crop_skeleton(skel, o)
            rows[key] = {e: {t: f95._keep(score_tracing(sk, lab, tolerance=t).as_row()) for t in TOLS}
                         for e, lab in labels.items()}  # fmt: skip
            for e in ENTRANTS:
                ref = crops[key][e]["4.0"]
                if bad := [k for k in SAME_GT if rows[key][e][4.0][k] != ref[k]]:
                    identity[f"{e} {key}"] = bad
            print(
                key,
                {e: {t: rows[key][e][t][PEN] for t in TOLS} for e in ENTRANTS},
                flush=True,
            )
    status, reading = outcome(identity, rows, crops)
    out = {
        "status": status,
        "size": SIZE,
        "tolerances": list(TOLS),
        "parents": PARENTS,
        "smoke": SMOKE,
        "identity_problems": identity,
        "failed": failed,
        "stems": {octant_key(p, o): s for s, p, o in stems()},
        "octants": {k: {e: {str(t): r for t, r in v.items()} for e, v in r.items()} for k, r in rows.items()},
    }  # fmt: skip
    if reading is not None:
        out.update(reading)
    out_path.write_text(json.dumps(out, indent=1) + "\n")
    print(f"status {status}; wrote {out_path}")
    return 0 if status == "OK" else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--work", type=Path, required=True)
    sub.add_parser("stems")
    p = sub.add_parser("smoke")
    p.add_argument("--work", type=Path, required=True)
    p = sub.add_parser("score")
    p.add_argument("--work", type=Path, required=True)
    p.add_argument(
        "--crops", type=Path, default=Path("reports/octant_crop_rescore.json")
    )
    p.add_argument("--out", type=Path, default=Path("reports/tracing_context.json"))
    args = ap.parse_args(argv)
    if args.cmd == "prepare":
        print(json.dumps(prepare(args.work / "data", args.work / "ct"), indent=1))
        return 0
    if args.cmd == "stems":
        for s, parent, _ in stems():
            print(s, parent)
        return 0
    if args.cmd == "smoke":
        return cmd_smoke(args.work)
    return cmd_score(args.work, args.crops, args.out)


if __name__ == "__main__":
    sys.exit(main())
