"""villa's fiber generator's two seam changes on ten hand-traced cubes of Scrolls 1 and 5 (finding 109's run).

Findings 106 and 108 measured two changes to villa's automated fiber generator (`vesuvius.fiber_spline_generator`,
VC3D's **Generate automated fibers…**) on eight Scroll-3 cubes, the same eight both times:
* the seam trim (`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch`);
* on top of it, suppressing a block's copy of a fiber another block also fitted
  (`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`).

This runs both on the ten fiber-skeletons cubes ScrollGT does not ship (Scrolls 1 and 5), which the generator has never
run on here. Each cube is generated as one block and as 8 blocks of half its side, each block predicted from its own
crop with the CLI's 32-voxel margin. The blocked fields are stitched three ways: villa main (`main`), with the trim
(`trim`), and with the trim and the catalogue change (`trim+dup`).

`smoke` re-stitches one of finding 106's cubes from its cached fields and predicts nothing: its rows must equal
findings 106's and 108's. `run` predicts and scores one cube, `verdict` applies the registered rule.

Usage (the generator's venv):
  python -I scripts/afv_generator_seam_confirmation.py run --cube CUBE --work DIR --pr PR_SRC --villa VILLA \
      --main REV --patched-stitch PATH --patched-catalog PATH
  python -I scripts/afv_generator_seam_confirmation.py smoke --fields F106_CUBE_DIR --work DIR --pr ... (as run)
  python -I scripts/afv_generator_seam_confirmation.py verdict --work DIR --out RECORD
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_cross_block_duplicates as xd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD_106 = ROOT / "reports/afv_generator_block_seams.json"
RECORD_108 = ROOT / "reports/afv_generator_cross_block_duplicates.json"
D = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/fiber_d004/unshipped")
# The ten Dataset004 cubes ScrollGT does not ship (reports/evidence/fiber_skeletons_unshipped_2026-11-02.json), as
# scripts/seed_heading_confirmation.py lists them. The first seven were first released in Dataset002, which trained
# fiber_hz_vt, the base model the generator's model was fine-tuned from; the last three were first released later.
CUBES = (
    "s1_02494_01494_03994_512",
    "s1_08994_02494_03494_512",
    "s1_09997_02497_03497_256",
    "s5_05497_01997_02997_256",
    "s5_05497_02497_02497_256",
    "s5_08994_02994_03994_512",
    "s5_08997_02497_04997_256",
    "s5_11497_05497_03997_256",
    "s5_15494_04494_02494_512",
    "s5_16997_03497_03997_256",
)
BASE_MODEL_UNSEEN = (
    "s1_08994_02494_03494_512",
    "s1_09997_02497_03497_256",
    "s5_15494_04494_02494_512",
)
# Each cube's (nml, image) sha256, as scripts/seed_heading_confirmation.py registered them on 2026-11-03.
DATA_SHA256 = {
    "s1_02494_01494_03994_512": ("08158b12e4e7ea9919b1e45c77bab8d34fe74c92e4a078bbe944736221caabbc",
                                 "1f5752040c0be008b8d4cc887a35f42d4944275d30e0163615b6403c4b807000"),
    "s1_08994_02494_03494_512": ("ac3e4ce198dd1190585afc157dccc01e9c41db01d11a1f7ff9df4463e425f99f",
                                 "c63427319d6829fb3d3777fd3acdc0c319d74e36ae4fd5e5fd68b6730256fb55"),
    "s1_09997_02497_03497_256": ("2e6377c131843281713c7d71dcc0c3f1189a860ecc509d0518013f4c889d1f48",
                                 "bc665cbaba66b1974b5bbdd2c74e359b045ff9e1190fc865155879bdb56e9d9b"),
    "s5_05497_01997_02997_256": ("affbce7a420684f63926952357faa4540fdb1bf4b2a1bb5dcdeef4e21607e186",
                                 "f70efb2272b107a141ddc34d0026801120498d197ce94e068ac4da3b8457eef9"),
    "s5_05497_02497_02497_256": ("d66fc2d33c47d282716389634e19aa64e7454a5c6485fa63cf23543b5e787c2f",
                                 "4b7cbdc7f99360cb74133f58ae6632915a65e2ad2bdebebd55359cd8c6351485"),
    "s5_08994_02994_03994_512": ("ff89cab79e990a5d91bb5823ed1607e0d6818f4ece0fe16ad3aad4ef2a2e04ed",
                                 "1b4b46736196b35f541996967268557ea3eccbe6ba21c0a1812092345db1b310"),
    "s5_08997_02497_04997_256": ("20c21c99a81cae5e2871be5a558fb1b6140020c9e62349723e0f58b86ac624b9",
                                 "b738435a45b52e51a0e46ffab0a164b64558d9d3d90e6190f4e99fd3365d97e4"),
    "s5_11497_05497_03997_256": ("a43fee7385b6589b8a976da6dfb3a054754864c518bc7953ca7029008542ad91",
                                 "fadef8712299b747833a4469400afac76e1a6cc8238c8e3f53f8eec26481e30e"),
    "s5_15494_04494_02494_512": ("d84fd73609f0f10052a8a580abc5f185b0af0ae25d7228d64e9a27375ac8508b",
                                 "2f82f9ec2ac0543b8f72c22e5c00e5f6d22ecebc026095fe1c72c9319b8732ab"),
    "s5_16997_03497_03997_256": ("6c88f50cbb7b33189bd0e68470986c8f6418fe23c0cf183289820d4379ec2cc1",
                                 "23611035a83434b34e6d670d50b0cc19b35913d011ae2c3c53b941d16496e769"),
}  # fmt: skip
VARIANTS = ("main", "trim", "trim+dup")
ARMS = ("one", "real")
# The smoke's cube: finding 106's first held-out cube, whose fields finding 106 cached and findings 106 and 108 scored.
SMOKE = bs.HELD_OUT[0]
# The registered predictions (docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md).
P1_UP = 8  # both changes: ERLpen at tolerance 4 above main's on at least this many of the ten
P2_GAIN = 0.10  # both changes: median ERLpen gain over main at tolerance 4
P3_MERGES = 1.05  # both changes: summed merges at tolerance 2 at most this times main's
P4_UP = 7  # the catalogue change: ERLpen at tolerance 4 above the trim's on at least this many
P5_DUP = 0.5  # both changes: median duplicated share at most this times main's


def size_of(cube: str) -> int:
    return int(cube.rsplit("_", 1)[1])


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def registered(cube: str, path: Path, kind: str) -> Path:
    """path, if it is the cube's registered NML or image (DATA_SHA256)."""
    want = DATA_SHA256[cube][("nml", "image").index(kind)]
    if sha256_of(path) != want:
        raise SystemExit(f"{cube}: {path} is not the registered {kind} (sha256 {want})")
    return path


def nml_path(cube: str, nml_dir: Path = D / "nml") -> Path:
    """Dataset004's NML for the cube (Scroll 1's are named s1a)."""
    s, z, y, x, n = cube.split("_")
    found = sorted(nml_dir.glob(f"fibers_{s}*_{z}z_{y}y_{x}x_{n}_v*.nml"))
    if len(found) != 1:
        raise SystemExit(f"{cube}: expected one NML in {nml_dir}, found {[p.name for p in found]}")  # fmt: skip
    return registered(cube, found[0], "nml")


def scrollgt_on_path() -> None:
    if str(bs.SG / "src") not in sys.path:
        sys.path.insert(0, str(bs.SG / "src"))


def ground_truth(cube: str, nml: Path | None = None):
    """The NML in the cube's frame, keeping the fibers with more than one node inside it, as ScrollGT's targets are
    scored (scripts/seed_heading_confirmation.py's, which gives ScrollGT's rows exactly on two shipped cubes)."""
    scrollgt_on_path()
    from scrollgt.fibers.skeleton_io import Skeleton, origin_from_stem, parse_nml

    shape = (size_of(cube),) * 3
    skel = parse_nml(nml or nml_path(cube), origin_zyx=origin_from_stem(cube))
    if skel.scale_um and any(abs(s - 7.91) > 1e-6 for s in skel.scale_um):
        raise SystemExit(f"{cube}: NML scale {skel.scale_um} is not 7.91 um")
    kept = [f for f in skel.fibers if f.in_bounds_mask(shape).sum() > 1]
    return Skeleton(fibers=kept, scale_um=skel.scale_um, origin_zyx=skel.origin_zyx)


def cube_image(cube: str) -> np.ndarray:
    import tifffile

    img = tifffile.imread(registered(cube, D / f"{cube}_image.tif", "image"))
    if img.shape != (size_of(cube),) * 3 or img.dtype != np.uint8:
        raise SystemExit(f"{cube}: image {img.shape} {img.dtype}")
    return img


def untrimmed(traces, *_):
    """`main`: villa main's stitching, which trims nothing."""
    return traces


def blocks_of(cli, arm: str, ct: np.ndarray, field_of) -> list:
    """(low_xyz, high_xyz, origin, size, ct crop, field) per block, as `cli.generate` reads them."""
    n = ct.shape[0]
    shape_xyz = np.asarray(ct.shape[::-1])
    out = []
    for i, (origin, size) in enumerate(
        cli.zone_blocks([0, 0, 0], list(shape_xyz), n if arm == "one" else n // 2)
    ):
        low = np.maximum(np.asarray(origin) - cli.BLOCK_MARGIN, 0)
        high = np.minimum(
            np.asarray(origin) + np.asarray(size) + cli.BLOCK_MARGIN, shape_xyz
        )
        sl = tuple(
            slice(int(a), int(b)) for a, b in zip(low[::-1], high[::-1], strict=True)
        )
        out.append((low, high, origin, size, ct[sl], lambda i=i, sl=sl: field_of(arm, i, sl)))  # fmt: skip
    return out


def generate(args, cube: str, ct: np.ndarray, skel, fields: Path, work: Path, may_predict: bool) -> dict:  # fmt: skip
    """Every arm and variant of one cube, scored; fields are read from `fields` or predicted into `work`."""
    import torch

    trim_cut_ends, cut_end, patched = xd.load(
        args.pr, args.patched_stitch, args.patched_catalog
    )
    scrollgt_on_path()
    import afv_to_labels
    from scrollgt.fibers.eval_trace import score_tracing
    from vesuvius.afv_spline_generator import cli
    from vesuvius.afv_spline_generator.cleanup import ExteriorBlack
    from vesuvius.afv_spline_generator.extend.catalog import Catalog
    from vesuvius.afv_spline_generator.predict import predict_fibers

    n = ct.shape[0]
    shape_xyz = np.asarray(ct.shape[::-1])
    problems = bs.identity(args.pr, args.villa, args.main, args.patched_stitch)
    problems += xd.catalog_problems(args.villa, args.main, args.patched_catalog)
    folder, provenance = cli.resolve_model(cli.DEFAULT_MODEL)
    revision = provenance.get(
        "revision"
    )  # the revision villa reports, recorded as reported
    if revision != bs.REVISION:
        problems.append(f"model revision {revision} is not {bs.REVISION}")
    out = {
        "cube": cube,
        "size": n,
        "block": n // 2,
        "cut_end": cut_end,
        "identity_problems": problems,
        "rows": {},
    }
    work.mkdir(parents=True, exist_ok=True)
    if problems:  # the gate stops the run before any field is predicted
        (work / "result.json").write_text(json.dumps(out, indent=1))
        raise SystemExit(f"{cube}: gate failed: {problems}")
    timing: dict[str, float] = {}
    network: list = []
    device = torch.device(args.device)
    whole: list[np.ndarray] = []

    def predicted(name: str, sl) -> np.ndarray:
        for d in (fields, work):
            if (d / f"prob_{name}.npy").exists():
                return np.load(d / f"prob_{name}.npy")
        if not may_predict:
            raise SystemExit(
                f"{cube}: no cached field prob_{name}.npy, and this step predicts nothing"
            )
        if not network:
            network.extend(cli.load_network(folder, device))
        t = time.time()
        p = predict_fibers(network[0], ct[sl], network[1], device=device, mirror=False)
        timing[name] = round(time.time() - t, 1)
        np.save(work / f"prob_{name}.npy", p)
        return p

    def field_of(arm: str, i: int, sl) -> np.ndarray:
        if arm == "one":
            if not whole:
                whole.append(predicted("one", (slice(None),) * 3))
            return whole[0][sl]
        return predicted(f"real_{i}", sl)

    reference: tuple[list[np.ndarray], list[int]] | None = None
    for arm in ARMS:
        blocks = blocks_of(cli, arm, ct, field_of)
        for variant in VARIANTS:
            trim = untrimmed if variant == "main" else trim_cut_ends
            catalog = patched.Catalog if variant == "trim+dup" else Catalog
            black = ExteriorBlack(np.zeros(3, int), shape_xyz)
            traces = xd.stitch_blocks(
                blocks, trim, np.zeros(3, int), shape_xyz, black, catalog
            )
            fibers = [np.asarray(t["points"], np.float64) for t in traces]
            families = [int(t["family"]) for t in traces]
            if arm == "one" and variant == "main":
                reference = (fibers, families)
                np.savez(work / "one_main_fibers.npz", points=np.concatenate(fibers),
                         offsets=np.r_[0, np.cumsum([len(f) for f in fibers])], family=np.array(families))  # fmt: skip
            assert reference is not None
            if arm == "one" and variant != "main":
                # one block has no inner border and one source job: neither change may alter it
                same = families == reference[1] and len(fibers) == len(reference[0])
                same = same and all(
                    np.array_equal(a, b)
                    for a, b in zip(fibers, reference[0], strict=True)
                )
                if not same:
                    problems.append(
                        f"the one-block arm differs between main and {variant}"
                    )
                continue
            labels = afv_to_labels.rasterize(
                {
                    k: afv_to_labels.to_cube_zyx(v, (0, 0, 0))
                    for k, v in enumerate(fibers)
                },
                (n,) * 3,
            )
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
            out["rows"][f"{arm}/{variant}"] = row
            r2, r4 = row["tol2"], row["tol4"]
            print(f"{cube} {arm:4s} {variant:8s} written {row['written']:4d} dup {row['duplicated_share']:.3f} "
                  f"crossings {row['crossings']} | t2 {r2['erl_merge_penalized']} m{r2['merges']} | "
                  f"t4 {r4['erl_merge_penalized']} m{r4['merges']}", flush=True)  # fmt: skip
    out["patched_stitch_sha256"] = sha256_of(args.patched_stitch)
    out["patched_catalog_sha256"] = sha256_of(args.patched_catalog)
    out["timing_s"] = timing
    out["settings"] = {"threshold": bs.THRESHOLD, "margin": cli.BLOCK_MARGIN, "mirror": False, "extend": False,
                       "max_join_angle": bs.MAX_JOIN_ANGLE, "min_length": bs.MIN_LENGTH,
                       "black_distance": bs.BLACK_DISTANCE, "model": cli.DEFAULT_MODEL, "revision": revision,
                       "pr_head": bs.PR_HEAD, "villa_main": args.main, "device": args.device}  # fmt: skip
    return out


def run(args) -> None:
    c = args.cube
    if c not in CUBES:
        raise SystemExit(f"{c} is not one of the ten cubes")
    work = args.work / c
    out = generate(args, c, cube_image(c), ground_truth(c), work, work, True)
    out["data_sha256"] = dict(zip(("nml", "image"), DATA_SHA256[c], strict=True))
    (work / "result.json").write_text(json.dumps(out, indent=1))
    print(f"{c}: identity problems {out['identity_problems'] or 'none'}", flush=True)


def smoke(args) -> dict:
    """Finding 106's cube from its cached fields: the rows must be findings 106's and 108's. Predicts nothing."""
    import zarr

    scrollgt_on_path()
    from scrollgt.fibers.target import load_fiber_target

    ct = np.asarray(zarr.open(str(bs.CT / f"{SMOKE}.zarr"), mode="r")[:])
    skel, _, _ = load_fiber_target(bs.SG / "data" / f"fibers_{SMOKE}")
    out = generate(args, SMOKE, ct, skel, args.fields, args.work / SMOKE, False)
    f106 = json.loads(RECORD_106.read_text())["cubes"][SMOKE]["rows"]
    f108 = json.loads(RECORD_108.read_text())["cubes"][SMOKE]["rows"]
    want = {"one/main": f106["one/main"], "real/main": f106["real/main"], "real/trim": f106["real/patched"],
            "real/trim+dup": f108["trim+dup"]}  # fmt: skip
    check = {k: out["rows"][k] == v for k, v in want.items()}
    result = {"cube": SMOKE, "identity_problems": out["identity_problems"], "reproduces": check,
              "rows": out["rows"]}  # fmt: skip
    print(
        json.dumps(
            {"reproduces": check, "identity_problems": out["identity_problems"]}
        ),
        flush=True,
    )
    return result


def gain(rows: dict, a: str, b: str, tol: str) -> float:
    """ERLpen of real/b over real/a, minus 1."""
    return (
        rows[f"real/{b}"][tol]["erl_merge_penalized"]
        / rows[f"real/{a}"][tol]["erl_merge_penalized"]
        - 1
    )


def verdict(results: dict) -> dict:
    """The registered decision rule, over the ten cubes."""
    if sorted(results) != sorted(CUBES):
        return {"decision": "NO_VERDICT", "why": "not every cube was run"}
    bad = {c: r["identity_problems"] for c, r in results.items() if r["identity_problems"]}  # fmt: skip
    if bad:
        return {"decision": "NO_VERDICT", "why": bad}
    rows = [results[c]["rows"] for c in CUBES]
    both = [gain(r, "main", "trim+dup", "tol4") for r in rows]
    over_trim = [gain(r, "trim", "trim+dup", "tol4") for r in rows]
    merges = [sum(r[f"real/{v}"]["tol2"]["merges"] for r in rows) for v in ("main", "trim+dup")]  # fmt: skip
    dup = [statistics.median(r[f"real/{v}"]["duplicated_share"] for r in rows) for v in ("main", "trim+dup")]  # fmt: skip
    checks = {
        "P1_both_tol4_up": [sum(x > 0 for x in both), sum(x > 0 for x in both) >= P1_UP],
        "P2_median_gain_tol4": [round(statistics.median(both), 4), statistics.median(both) >= P2_GAIN],
        "P3_merges_tol2": [merges, merges[1] <= P3_MERGES * merges[0]],
        "P4_over_trim_tol4_up": [sum(x > 0 for x in over_trim), sum(x > 0 for x in over_trim) >= P4_UP],
        "P5_median_duplicated_share": [[round(d, 4) for d in dup], dup[1] <= P5_DUP * dup[0]],
    }  # fmt: skip
    held = {k: v[1] for k, v in checks.items()}
    if not (held["P1_both_tol4_up"] and held["P3_merges_tol2"]):
        decision = "NOT_CONFIRMED"
    elif not held["P4_over_trim_tol4_up"]:
        decision = "TRIM_ONLY"
    elif not (held["P2_median_gain_tol4"] and held["P5_median_duplicated_share"]):
        decision = "PARTIAL"
    else:
        decision = "CONFIRMED"
    return {"decision": decision, **checks}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "smoke"):
        p = sub.add_parser(name)
        if name == "run":
            p.add_argument("--cube", required=True)
        else:
            p.add_argument("--fields", type=Path, required=True)
            p.add_argument("--out", type=Path, required=True)
        p.add_argument("--work", type=Path, required=True)
        p.add_argument("--pr", type=Path, required=True)
        p.add_argument("--villa", type=Path, required=True)
        p.add_argument("--main", required=True)
        p.add_argument("--patched-stitch", type=Path, required=True)
        p.add_argument("--patched-catalog", type=Path, required=True)
        p.add_argument("--device", default="cpu")
    v = sub.add_parser("verdict")
    v.add_argument("--work", type=Path, required=True)
    v.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
    elif args.cmd == "smoke":
        args.out.write_text(json.dumps(smoke(args), indent=1) + "\n")
    else:
        if args.out.exists():
            raise SystemExit(f"{args.out} exists: the record is written once")
        results = {
            c: json.loads((args.work / c / "result.json").read_text()) for c in CUBES
        }
        record = {"verdict": verdict(results), "cubes": results}
        args.out.write_text(json.dumps(record, indent=1) + "\n")
        print(json.dumps(record["verdict"], indent=1))


if __name__ == "__main__":
    main()
