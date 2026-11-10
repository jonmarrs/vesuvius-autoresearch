"""scripts/afv_generator_default_zone.py (finding 107's run): the cube it picks, the zone it lays out, the share it
counts inside the cube and the registered decision rule."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import statistics
import subprocess
import sys
import types
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_default_zone as dz  # noqa: E402

PR_CLI = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/pr1934/vesuvius/src/vesuvius/afv_spline_generator/cli.py")  # fmt: skip
ZONE_WT = Path("/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-afv-seam-zone")
AMENDED = (
    dz.ROOT / "repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch"
)
REGISTRATION = dz.ROOT / "docs/preregistration/2026-11-08_afv_generator_default_zone.md"
EVIDENCE = dz.ROOT / "reports/evidence/afv_generator_seam_diag_2026-11-07.json"


def module(path: Path, name: str):
    if not path.exists():
        pytest.skip(f"{path} is not on this machine")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_cube_is_the_lower_middle_gain_and_the_registration_quotes_its_record():
    record = json.loads(dz.RECORD_106.read_text())
    assert dz.lower_middle_cube(record) == dz.CUBE and dz.CUBE.endswith(f"_{dz.SIZE}")
    g = {c: bs.gain(record["cubes"][c]["rows"], "real", "tol4") for c in bs.HELD_OUT}
    lo, hi = sorted(g.values())[3:5]
    assert g[dz.CUBE] == lo < hi and statistics.median(g.values()) == pytest.approx(
        (lo + hi) / 2
    )
    text = " ".join(REGISTRATION.read_text().split())
    r = record["cubes"][dz.CUBE]["rows"]
    m, p = r["real/main"], r["real/patched"]
    assert (f"`{dz.CUBE}`, it rose +{100 * g[dz.CUBE]:.1f}% at τ = 4 and +{100 * bs.gain(r, 'real', 'tol2'):.1f}% at "
            f"τ = 2, with merges at τ = 2 {m['tol2']['merges']} → {p['tol2']['merges']} and a duplicated share "
            f"{m['duplicated_share']:.3f} → {p['duplicated_share']:.3f}. Its whole face crossings fell "
            f"{m['crossings']['whole']} → {p['crossings']['whole']}, the most of the eight") in text  # fmt: skip
    fell = {c: record["cubes"][c]["rows"]["real/main"]["crossings"]["whole"] - record["cubes"][c]["rows"]["real/patched"]["crossings"]["whole"] for c in bs.HELD_OUT}  # fmt: skip
    assert max(fell, key=fell.get) == dz.CUBE
    ev = json.loads(EVIDENCE.read_text())["cubes"][dz.CUBE]["real"]
    assert (
        f"lost {ev['worse_by_join']['chained only in main']} joins and gained "
        f"{ev['better_by_join']['chained only with the trim']}"
    ) in text
    assert (f"(0.128): `{dz.CUBE}` ({lo:.3f}; the other is {hi:.3f})" in text
            and f"not the best ({max(g.values()):.3f})" in text)  # fmt: skip


def test_the_zone_is_villas_default_block_around_the_cube():
    assert (dz.BLOCK, dz.MARGIN, dz.ZONE, dz.PAD, dz.SIDE) == (512, 32, 1024, 288, 1088)


def test_the_blocks_are_read_as_cli_reads_them_and_their_faces_cross_the_cube_at_256():
    """Needs the #1934 head's own zone_blocks (not shipped with the repo), taken from its cli.py's syntax tree."""
    if not PR_CLI.exists():
        pytest.skip(f"{PR_CLI} is not on this machine")
    tree = ast.parse(PR_CLI.read_text())
    (fn,) = [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "zone_blocks"
    ]
    namespace: dict = {"Sequence": Sequence}
    exec(compile(ast.Module([fn], []), str(PR_CLI), "exec"), namespace)
    cli = types.SimpleNamespace(zone_blocks=namespace["zone_blocks"])
    shape = np.full(3, dz.SIDE)
    crops = dz.block_crops(cli, shape)
    assert len(crops) == 8
    assert {tuple(o) for o, *_ in crops} == {
        (x, y, z) for z in (32, 544) for y in (32, 544) for x in (32, 544)
    }
    for o, s, low, high in crops:
        assert s == [512] * 3
        assert (
            np.array_equal(high - low, [576] * 3)
            and set(low) <= {0, 512}
            and set(high) <= {576, 1088}
        )
    low, high = dz.read_box(shape)
    assert np.array_equal(low, [0] * 3) and np.array_equal(high, [dz.SIDE] * 3)
    # the inner faces, in the cube's own coordinates, are where finding 106's blocks of 256 met
    assert {o[0] - dz.PAD for o, *_ in crops if o[0] > dz.MARGIN} == {dz.SIZE // 2}


def test_the_padded_scan_lies_inside_scroll_3s_scan():
    cc = module(dz.CONTEXT_CT, "context_ct_for_zone_test")
    lo, hi = cc.padded_bounds(dz.CUBE, dz.PAD)
    assert all(
        0 <= a < b <= s
        for a, b, s in zip(lo, hi, cc.TIFF_VOLUMES["s3"]["shape"], strict=True)
    )
    assert tuple(b - a for a, b in zip(lo, hi, strict=True)) == (dz.SIDE,) * 3


def test_the_slab_fetch_writes_the_voxels_the_whole_region_fetch_gives(tmp_path):
    """Amendment 1: the fetch converts SLAB slices at a time into a memory-mapped .npy, from the same cache files."""
    cc = module(dz.CONTEXT_CT, "context_ct_for_slab_test")
    lo, hi = (5, 7, 9), (16, 20, 15)  # 11 slices: 3 slabs of 4, the last short
    rng = np.random.default_rng(0)
    volume = {"shape": (40, 40, 40), "url": "unused", "digits": 5}
    cache = tmp_path / "cache"
    cache.mkdir()
    for z in range(lo[0], hi[0]):
        # the full uint16 range, so the clip at 255 and the /257 rounding are both exercised
        win = rng.integers(
            0, 65536, (hi[1] - lo[1], hi[2] - lo[2]), dtype=np.uint64
        ).astype("<u2")
        np.save(cache / f"{z}_{lo[1]}_{lo[2]}_{hi[1]}_{hi[2]}.npy", win)

    def no_network(*a, **k):
        raise AssertionError("every slice is cached")

    whole = cc.to_uint8(cc.read_tiff_region(volume, lo, hi, cache, no_network))
    calls = []
    real = cc.read_tiff_region

    def counted(v, a, b, c, get_ranges=no_network):
        calls.append((a, b))
        return real(v, a, b, c, no_network)

    cc.read_tiff_region = counted
    out = dz.write_uint8_scan(cc, volume, lo, hi, cache, tmp_path / "scan.npy", slab=4)
    assert [a[0] for a, _ in calls] == [5, 9, 13] and [b[0] for _, b in calls] == [
        9,
        13,
        16,
    ]
    del out
    got = np.load(tmp_path / "scan.npy")
    assert got.dtype == np.uint8 and got.shape == whole.shape
    np.testing.assert_array_equal(got, whole)
    assert (
        len(np.unique(whole)) > 200
    )  # the comparison is not trivially all zeros or all 255


def line(a, b):
    return np.array([a, b], float)


def test_the_cube_share_counts_only_samples_inside_and_their_neighbours_anywhere():
    a, b = line([0, 0, 0], [100, 0, 0]), line([40, 1, 0], [100, 1, 0])
    far = line([0, 30, 0], [100, 30, 0])  # another family beside nothing
    fibers, fams = [a, b, far], [0, 0, 1]
    # x < 50: a's 100 samples, 22 of them within 1.5 voxels of b (x >= 38.88); b's 20, all beside a; far's 100, none
    assert dz.duplicated_share_in(
        fibers, fams, [0, -5, -5], [50, 5, 5]
    ) == pytest.approx(42 / 120)
    assert dz.duplicated_share_in(
        fibers, fams, [0, -5, -5], [50, 40, 5]
    ) == pytest.approx(42 / 220)
    # b's copy lies outside x < 39: a's samples there have no neighbour
    assert dz.duplicated_share_in(fibers, fams, [0, -5, -5], [38, 5, 5]) == 0.0
    whole = [-1e9] * 3, [1e9] * 3
    assert dz.duplicated_share_in(fibers, fams, *whole) == pytest.approx(
        bs.duplicated_share(fibers, fams)
    )


def result(main_dup, patched_dup, erl4, merges2, problems=()):
    def row(dup, e, m):
        return {
            "zone": {"duplicated_share": dup},
            "cube": {"tol4": {"erl_merge_penalized": e}, "tol2": {"merges": m}},
        }

    return {"identity_problems": list(problems),
            "rows": {"main": row(main_dup, erl4[0], merges2[0]), "patched": row(patched_dup, erl4[1], merges2[1])}}  # fmt: skip


@pytest.mark.parametrize(
    "r, decision",
    [
        (result(0.20, 0.08, (40.0, 45.0), (50, 52)), "BITES_AT_DEFAULTS"),
        (
            result(0.20, 0.08, (40.0, 45.0), (50, 52), ["a module differs"]),
            "NO_VERDICT",
        ),
        (result(0.04, 0.01, (40.0, 45.0), (50, 50)), "NO_DOUBLING_AT_DEFAULTS"),
        (result(0.20, 0.08, (40.0, 40.0), (50, 50)), "COSTS_AT_DEFAULTS"),
        (result(0.20, 0.08, (40.0, 45.0), (50, 53)), "COSTS_AT_DEFAULTS"),
        (result(0.20, 0.13, (40.0, 45.0), (50, 50)), "PARTIAL"),
        (result(0.20, 0.12, (40.0, 41.0), (40, 42)), "BITES_AT_DEFAULTS"),
        # P1 is "at least 0.05": a share of exactly 0.05 holds
        (result(0.05, 0.02, (40.0, 45.0), (50, 50)), "BITES_AT_DEFAULTS"),
        # the table's rows in order: a P3 miss outranks a P2 miss, a P1 miss outranks both, a gate failure all
        (result(0.20, 0.13, (40.0, 40.0), (50, 50)), "COSTS_AT_DEFAULTS"),
        (result(0.04, 0.03, (40.0, 39.0), (50, 60)), "NO_DOUBLING_AT_DEFAULTS"),
        (
            result(0.04, 0.03, (40.0, 39.0), (50, 60), ["a module differs"]),
            "NO_VERDICT",
        ),
    ],
)
def test_the_decision_rule(r, decision):
    assert dz.verdict(r)["decision"] == decision


def test_the_verdict_step_writes_the_record_once(tmp_path, monkeypatch):
    work, out = tmp_path / "work", tmp_path / "record.json"
    work.mkdir()
    r = result(0.20, 0.08, (40.0, 45.0), (50, 52))
    (work / "result.json").write_text(json.dumps(r))
    argv = ["afv_generator_default_zone.py", "verdict", "--work", str(work), "--out", str(out)]  # fmt: skip
    monkeypatch.setattr(sys, "argv", argv)
    dz.main()
    first = out.read_text()
    assert first == json.dumps({"verdict": dz.verdict(r), "result": r}, indent=1) + "\n"
    (work / "result.json").write_text(json.dumps(result(0.04, 0.01, (40.0, 45.0), (50, 50))))  # fmt: skip
    with pytest.raises(SystemExit, match="written once"):
        dz.main()
    assert out.read_text() == first


def test_the_cube_share_counts_a_neighbour_outside_the_cube():
    """A sample inside counts as duplicated when its same-family neighbour lies outside [lo, hi)."""
    a, b = line([0, 0, 0], [100, 0, 0]), line([40, 1, 0], [100, 1, 0])
    # x < 40: a's 80 samples; those at x 39.0 and 39.5 lie within 1.5 voxels of b's first samples, all at x >= 40
    assert dz.duplicated_share_in([a, b], [0, 0], [0, -5, -5], [40, 5, 5]) == pytest.approx(2 / 80)  # fmt: skip


def uint8_standin(raw):
    """A voxel-by-voxel uint16 -> uint8 conversion standing in for ScrollGT's to_uint8."""
    return np.clip(np.rint(raw / 257.0), 0, 255).astype(np.uint8)


def test_the_slab_fetch_reads_16_slices_at_a_time_without_scrollgt(tmp_path):
    """Amendment 1's write_uint8_scan, with a stand-in for ScrollGT's context_ct (the test above needs ScrollGT)."""
    data = np.random.default_rng(1).integers(0, 65536, (40, 9, 11), dtype=np.uint64).astype("<u2")  # fmt: skip
    lo, hi = (3, 1, 2), (36, 6, 9)  # 33 slices: two slabs of 16 and one of 1
    calls = []

    def read_tiff_region(volume, a, b, cache):
        calls.append((tuple(a), tuple(b)))
        return volume["data"][a[0] : b[0], a[1] : b[1], a[2] : b[2]]

    cc = types.SimpleNamespace(read_tiff_region=read_tiff_region, to_uint8=uint8_standin)  # fmt: skip
    out = dz.write_uint8_scan(
        cc, {"data": data}, lo, hi, tmp_path, tmp_path / "scan.npy"
    )
    del out
    assert calls == [((3, 1, 2), (19, 6, 9)), ((19, 1, 2), (35, 6, 9)), ((35, 1, 2), (36, 6, 9))]  # fmt: skip
    np.testing.assert_array_equal(np.load(tmp_path / "scan.npy"), uint8_standin(data[3:36, 1:6, 2:9]))  # fmt: skip


CONTEXT_STANDIN = """
import numpy as np

DATA = np.load({data!r})
TIFF_VOLUMES = {{"s3": {{"shape": DATA.shape}}}}


def padded_bounds(cube, pad):
    return (1, 2, 3), (1 + {side}, 2 + {side}, 3 + {side})


def read_tiff_region(volume, lo, hi, cache):
    return DATA[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]


def to_uint8(raw):
    return np.clip(np.rint(raw / 257.0), 0, 255).astype(np.uint8)


def core(a, pad):
    return a[pad:-pad, pad:-pad, pad:-pad]
"""


@pytest.mark.parametrize("core_matches", [True, False])
def test_the_fetch_renames_the_scan_into_place_only_once_its_core_is_the_cubes(
    tmp_path, monkeypatch, core_matches
):
    """Amendment 1: "the file is renamed into place only after it passes" the core check."""
    size, pad = 4, 3
    side = size + 2 * pad
    data = np.random.default_rng(2).integers(0, 65536, (16, 16, 16), dtype=np.uint64).astype("<u2")  # fmt: skip
    np.save(tmp_path / "data.npy", data)
    standin = tmp_path / "context_ct.py"
    standin.write_text(
        CONTEXT_STANDIN.format(data=str(tmp_path / "data.npy"), side=side)
    )
    padded = uint8_standin(data[1 : 1 + side, 2 : 2 + side, 3 : 3 + side])
    own = padded[pad:-pad, pad:-pad, pad:-pad].copy()
    if not core_matches:
        own[0, 0, 0] ^= 1
    monkeypatch.setitem(sys.modules, "zarr", types.SimpleNamespace(open=lambda path, mode: own))  # fmt: skip
    for name, value in (("SIZE", size), ("PAD", pad), ("SIDE", side), ("CONTEXT_CT", standin)):  # fmt: skip
        monkeypatch.setattr(dz, name, value)
    out = tmp_path / "context.npy"
    args = types.SimpleNamespace(out=out, cache=tmp_path / "cache")
    if core_matches:
        dz.fetch(args)
        np.testing.assert_array_equal(np.load(out), padded)
        assert not (tmp_path / "context.part.npy").exists()
    else:
        with pytest.raises(SystemExit, match="core is not the cube's own CT"):
            dz.fetch(args)
        assert not out.exists()


# run() with stand-ins for torch, zarr, ScrollGT and the generator, on a zone shrunk to SIZE 8, ZONE 16, BLOCK 8, MARGIN 2
SMALL = {"SIZE": 8, "ZONE": 16, "BLOCK": 8, "MARGIN": 2, "PAD": 6, "SIDE": 20}
FIBERS_XYZ = {  # block 0's splines, absolute x, y, z; the cube is [6, 14) on each axis
    "inside": ("V", line([7, 8, 8], [13, 8, 8])),
    # 1 voxel beside "inside": the trim stand-in drops it
    "copy": ("V", line([7, 9, 8], [13, 9, 8])),
    "below": ("H", line([0.5, 1, 1], [5.5, 1, 1])),
    "beyond": ("H", line([15, 8, 12], [19, 8, 12])),  # inside the cube in y and z only
}


def run_small(tmp_path, monkeypatch, seen, fail=None):
    """dz.run on the shrunk zone, the stand-ins recording into SEEN; FAIL names a gate check to break."""
    for name, value in SMALL.items():
        monkeypatch.setattr(dz, name, value)
    s, p = SMALL["SIZE"], SMALL["PAD"]
    ctx = np.random.default_rng(3).integers(0, 256, (SMALL["SIDE"],) * 3).astype(np.uint8)  # fmt: skip
    own = ctx[p : p + s, p : p + s, p : p + s].copy()
    if fail == "core":
        own[0, 0, 0] ^= 1
    np.save(tmp_path / "context.npy", ctx)
    stitch = tmp_path / "stitch.py"
    stitch.write_text("# the patched stitch.py\n")
    sha = hashlib.sha256(stitch.read_bytes()).hexdigest()
    monkeypatch.setattr(dz, "PATCHED_STITCH_SHA256", "0" * 64 if fail == "sha" else sha)

    def trim(traces, low, high, reach_low, reach_high):
        seen.trim.append([tuple(int(v) for v in x) for x in (low, high, reach_low, reach_high)])  # fmt: skip
        return [(f, q) for f, q in traces if not np.allclose(q[:, 1], 9)]

    monkeypatch.setattr(bs, "load", lambda pr, patched: (trim, 16.0))
    monkeypatch.setattr(bs, "identity", lambda *a: ["a module differs"] if fail == "identity" else [])  # fmt: skip
    calls = iter(range(1000))

    def extract_splines(prob, threshold):
        if next(calls) % 8:
            return []
        # block 0 reads from 0, so its local z, y, x are absolute
        return [(f, q[:, ::-1].copy()) for f, q in FIBERS_XYZ.values()]

    class Stitcher:
        def __init__(self, scratch):
            self.fibers = []

        def add_block(self, name, low_xyz, size_xyz, traces, core):
            self.fibers += [{"points": q[:, ::-1] + low_xyz, "family": "VH".index(f)} for f, q in traces]  # fmt: skip

        def stitched(self):
            return self.fibers

        def close(self):
            pass

    class ExteriorBlack:
        def __init__(self, low, high):
            seen.black.append((tuple(int(v) for v in low), tuple(int(v) for v in high)))

        def add(self, ct, low):
            pass

    def score_tracing(skel, labels, tolerance):
        seen.labels.append(labels.copy())
        seen.tolerances.append(tolerance)
        return types.SimpleNamespace(as_row=lambda: {"erl_merge_penalized": 1.0, "merges": 0})  # fmt: skip

    def zone_blocks(origin, size, block):  # the #1934 head's, as the smoke copies it
        axes = [[(o + a, min(block, n - a)) for a in range(0, n, block)] for o, n in zip(origin, size, strict=True)]  # fmt: skip
        blocks = [([x, y, z], [sx, sy, sz]) for z, sz in axes[2] for y, sy in axes[1] for x, sx in axes[0]]  # fmt: skip
        return blocks[:7] if fail == "crops" else blocks

    revision = "0" * 40 if fail == "revision" else bs.REVISION
    cli = types.SimpleNamespace(
        zone_blocks=zone_blocks, BLOCK_MARGIN=SMALL["MARGIN"], DEFAULT_MODEL="model",
        resolve_model=lambda model: ("folder", {"revision": revision}),
        load_network=lambda folder, device: seen.networks.append(folder) or ("network", 64),
    )  # fmt: skip

    def predict_fibers(network, ct, patch, device, mirror):
        seen.predicted.append(ct.shape)
        return np.zeros(ct.shape, np.uint8)

    modules = {
        "torch": types.SimpleNamespace(device=lambda d: d),
        "zarr": types.SimpleNamespace(open=lambda path, mode: own),
        "scrollgt": types.ModuleType("scrollgt"),
        "scrollgt.fibers": types.ModuleType("scrollgt.fibers"),
        "scrollgt.fibers.eval_trace": types.SimpleNamespace(score_tracing=score_tracing),
        "scrollgt.fibers.target": types.SimpleNamespace(load_fiber_target=lambda path: ("skeleton", None, None)),
        "vesuvius": types.ModuleType("vesuvius"),
        "vesuvius.afv_spline_generator": types.SimpleNamespace(cli=cli),
        "vesuvius.afv_spline_generator.cli": cli,
        "vesuvius.afv_spline_generator.cleanup": types.SimpleNamespace(
            ExteriorBlack=ExteriorBlack, clean=lambda traces, *a: traces),
        "vesuvius.afv_spline_generator.extend": types.ModuleType("vesuvius.afv_spline_generator.extend"),
        "vesuvius.afv_spline_generator.extend.stitch": types.SimpleNamespace(Stitcher=Stitcher),
        "vesuvius.afv_spline_generator.predict": types.SimpleNamespace(predict_fibers=predict_fibers),
        "vesuvius.afv_spline_generator.splines": types.SimpleNamespace(
            extract_splines=extract_splines, threshold_to_u8=lambda t: t),
    }  # fmt: skip
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    args = types.SimpleNamespace(context=tmp_path / "context.npy", work=tmp_path / "work", pr=tmp_path,
                                 villa=tmp_path, main="7e6b82164", patched_stitch=stitch, device="cpu")  # fmt: skip
    dz.run(args)
    return json.loads((args.work / "result.json").read_text())


def watched():
    return types.SimpleNamespace(trim=[], black=[], predicted=[], networks=[], labels=[], tolerances=[])  # fmt: skip


@pytest.mark.parametrize("fail", ["identity", "sha", "core", "crops", "revision"])
def test_a_failed_gate_check_stops_the_run_before_any_field_is_predicted(
    tmp_path, monkeypatch, fail
):
    """The registration: run "checks all three before it predicts a field, and stops if one fails"."""
    seen = watched()
    with pytest.raises(SystemExit, match="gate failed"):
        run_small(tmp_path, monkeypatch, seen, fail)
    assert seen.networks == [] and seen.predicted == []
    assert not list((tmp_path / "work").glob("prob_block_*"))
    assert not (tmp_path / "work" / "result.json").exists()


def test_the_run_scores_main_and_the_trim_as_registered(tmp_path, monkeypatch):
    """The trim runs on `patched` only, with the zone's read box; the zone's share counts every sample and the cube's
    only the samples inside the cube; the written fibers are scored in the cube's frame."""
    seen = watched()
    out = run_small(tmp_path, monkeypatch, seen)
    assert out["identity_problems"] == [] and len(seen.predicted) == 8
    assert all(shape == (12, 12, 12) for shape in seen.predicted)  # BLOCK + 2 MARGIN
    # one trim call per block, in the patched variant only, the read box the whole array (zone ± margin)
    assert len(seen.trim) == 8 and seen.black == [((0, 0, 0), (20, 20, 20))] * 2
    assert all(t[2:] == [(0, 0, 0), (20, 20, 20)] for t in seen.trim)
    assert seen.trim[0][:2] == [(0, 0, 0), (12, 12, 12)]  # block 0's crop, z, y, x
    m, p = out["rows"]["main"], out["rows"]["patched"]
    every = [q for _, q in FIBERS_XYZ.values()]
    families = ["VH".index(f) for f, _ in FIBERS_XYZ.values()]
    assert m["zone"] == {
        "written": 4,
        "length": 21.0,
        "duplicated_share": round(26 / 46, 4),
    }
    assert bs.duplicated_share(every, families) == pytest.approx(26 / 46)
    assert p["zone"] == {"written": 3, "length": 15.0, "duplicated_share": 0.0}
    # inside the cube: "inside" and "copy", 13 samples each, all beside each other; "below" and "beyond" are outside
    assert (m["cube"]["written_inside"], m["cube"]["duplicated_share"]) == (2, 1.0)
    assert (p["cube"]["written_inside"], p["cube"]["duplicated_share"]) == (1, 0.0)
    assert seen.tolerances == [2.0, 4.0, 2.0, 4.0]
    main_labels = seen.labels[0]
    assert main_labels.shape == (8, 8, 8) and np.count_nonzero(main_labels) == 14
    # "inside" and "copy" at cube-local z 2, y 2 and 3, x 1 to 7
    assert np.all(main_labels[2, 2:4, 1:8] > 0)


def test_the_patched_stitch_is_the_amended_patch_on_villa_7e6b82164():
    stitch = ZONE_WT / "vesuvius/src/vesuvius/fiber_spline_generator/extend/stitch.py"
    if not stitch.exists():
        pytest.skip("the patched villa worktree is not on this machine")
    assert hashlib.sha256(stitch.read_bytes()).hexdigest() == dz.PATCHED_STITCH_SHA256
    diff = subprocess.run(["git", "-C", str(ZONE_WT), "diff", "7e6b82164", "HEAD"], capture_output=True, check=True).stdout  # fmt: skip
    assert diff == AMENDED.read_bytes()


def test_the_registrations_smoke_is_its_evidence_against_finding_106s_arm_same():
    smoke = json.loads(
        (
            dz.ROOT
            / "reports/evidence/afv_generator_default_zone_smoke_2026-11-08.json"
        ).read_text()
    )
    assert (
        smoke["cube"] == dz.CUBE
        and smoke["identity_problems"] == []
        and smoke["cut_end"] == 16.0
    )
    assert smoke["patched_stitch_sha256"] == dz.PATCHED_STITCH_SHA256
    rec = json.loads(dz.RECORD_106.read_text())["cubes"][dz.CUBE]["rows"]
    s = {v: smoke["rows"][v] for v in bs.VARIANTS}
    r = {v: rec[f"same/{v}"] for v in bs.VARIANTS}
    text = " ".join(REGISTRATION.read_text().split())

    def gain(m, p):
        return f"{100 * (p / m - 1):+.1f}%"

    e4 = {k: [x[v]["tol4"]["erl_merge_penalized"] for v in bs.VARIANTS] for k, x in (("s", {v: s[v]["cube"] for v in s}), ("r", r))}  # fmt: skip
    assert (f"fibers written {s['main']['zone']['written']} and {s['patched']['zone']['written']} (finding 106: "
            f"{r['main']['written']} and {r['patched']['written']}), ERLpen at τ = 4 {e4['s'][0]} → {e4['s'][1]} "
            f"({e4['r'][0]} → {e4['r'][1]}), a gain of {gain(*e4['s'])} in both, merges at τ = 2 "
            f"{s['main']['cube']['tol2']['merges']} → {s['patched']['cube']['tol2']['merges']} "
            f"({r['main']['tol2']['merges']} → {r['patched']['tol2']['merges']})") in text  # fmt: skip
    assert gain(*e4["s"]) == gain(*e4["r"])


def test_the_launcher_parses():
    """bash reads a script as it runs it: a quoting error would stop the run only once it reached that line."""
    launcher = dz.ROOT / "repro/fibers/run_afv_generator_default_zone.sh"
    assert (
        subprocess.run(["bash", "-n", str(launcher)], capture_output=True).returncode
        == 0
    )
