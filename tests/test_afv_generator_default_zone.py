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
    ],
)
def test_the_decision_rule(r, decision):
    assert dz.verdict(r)["decision"] == decision


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
