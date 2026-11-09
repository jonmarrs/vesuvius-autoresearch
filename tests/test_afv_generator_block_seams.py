"""scripts/afv_generator_block_seams.py: its measures on hand-made fibers, its identity gate on hand-made sources, and the
registered decision rule."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402


def along_x(x0, x1, y=48.0, z=48.0):
    x = np.arange(x0, x1 + 0.25, 0.5)
    return np.stack([x, np.full_like(x, y), np.full_like(x, z)], axis=1)


def test_duplicated_share_counts_length_beside_another_fiber_of_the_same_family():
    a, b = along_x(0, 100), along_x(50, 150, y=49.0)
    # x 50..100 of each lies 1 voxel from the other, and 1.5 voxels reach sqrt(1.5**2 - 1) = 1.12 voxels past it
    assert bs.duplicated_share([a, b], [0, 0]) == pytest.approx(
        (50 + 1.12) / 100, abs=0.005
    )
    assert bs.duplicated_share([a, b], [0, 1]) == 0.0  # other family
    assert (
        bs.duplicated_share([a, along_x(50, 150, y=51.0)], [0, 0]) == 0.0
    )  # 3 voxels apart


def test_a_crossing_is_whole_broken_or_lost():
    ref = [along_x(20, 236)]
    xs = bs.crossings(ref, [0], 256)
    assert len(xs) == 1  # the mid plane x = 128 only; y and z stay at 48
    assert bs.crossing_kinds(xs, ref, [0]) == {"whole": 1, "broken": 0, "lost": 0}
    halves = [along_x(20, 140), along_x(110, 236, y=48.5)]
    assert bs.crossing_kinds(xs, halves, [0, 0]) == {"whole": 0, "broken": 1, "lost": 0}
    assert bs.crossing_kinds(xs, [along_x(20, 100)], [0]) == {
        "whole": 0,
        "broken": 0,
        "lost": 1,
    }
    assert bs.crossing_kinds(xs, ref, [1]) == {"whole": 0, "broken": 0, "lost": 1}
    assert (
        bs.crossings([along_x(100, 150)], [0], 256) == []
    )  # under 40 voxels on one side


MAIN = """import numpy as np

FAMILIES = {"V": 0, "H": 1}


def _length(points):
    return 0.


class _Frozen:
    pass
"""
PATCHED = MAIN.replace(
    'FAMILIES = {"V": 0, "H": 1}\n',
    'FAMILIES = {"V": 0, "H": 1}\n# why\nCUT_END = 12.\n',
).replace(
    "class _Frozen:",
    "def trim_cut_ends(traces, low, high, shape, distance=CUT_END):\n    return list(traces)\n\n\nclass _Frozen:",
)


@pytest.fixture
def sources(tmp_path):
    """A villa repo whose commit holds MAIN as stitch.py and the other modules; a PR-head tree equal to it."""
    villa = tmp_path / "villa"
    pkg = villa / "vesuvius/src/vesuvius/fiber_spline_generator"
    pr = tmp_path / "pr"
    head = pr / "vesuvius/afv_spline_generator"
    for rel in bs.IDENTICAL:
        for root in (pkg, head):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(MAIN if rel.endswith("stitch.py") else f"# {rel}\n")
    subprocess.run(["git", "init", "-q", str(villa)], check=True)
    subprocess.run(["git", "-C", str(villa), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(villa),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-qm",
            "m",
        ],
        check=True,
    )
    patched = tmp_path / "stitch_patched.py"
    patched.write_text(PATCHED)
    return pr, villa, patched


def test_identity_passes_when_only_the_fix_is_added(sources):
    pr, villa, patched = sources
    assert bs.identity(pr, villa, "HEAD", patched) == []


def test_identity_catches_a_changed_module_and_a_patch_that_changes_more(sources):
    pr, villa, patched = sources
    (pr / "vesuvius/afv_spline_generator/extend/catalog.py").write_text("# changed\n")
    assert bs.identity(pr, villa, "HEAD", patched) == [
        "extend/catalog.py differs from villa HEAD"
    ]
    (pr / "vesuvius/afv_spline_generator/extend/catalog.py").write_text(
        "# extend/catalog.py\n"
    )
    patched.write_text(PATCHED.replace("return 0.", "return 1."))
    assert bs.identity(pr, villa, "HEAD", patched) == [
        "the patched stitch.py changes more than CUT_END and trim_cut_ends"
    ]
    patched.write_text(MAIN)
    assert "no CUT_END or trim_cut_ends" in bs.identity(pr, villa, "HEAD", patched)[0]


def result(
    erl4_main,
    erl4_fix,
    erl2_main=10.0,
    erl2_fix=10.5,
    merges_main=10,
    merges_fix=10,
    problems=(),
):
    def row(e2, e4, m):
        return {
            "tol2": {"erl_merge_penalized": e2, "merges": m},
            "tol4": {"erl_merge_penalized": e4, "merges": m},
        }

    return {"identity_problems": list(problems),
            "rows": {"one/main": row(12.0, 40.0, 8), "real/main": row(erl2_main, erl4_main, merges_main),
                     "real/patched": row(erl2_fix, erl4_fix, merges_fix)}}  # fmt: skip


def test_the_decision_rule():
    up = {
        c: result(30.0, 34.0) for c in bs.HELD_OUT
    }  # +13% at tol 4 on every cube, +5% at tol 2
    v = bs.verdict(up)
    assert v["decision"] == "SUPPORTED" and v["P1_gain_tol4_cubes_up"] == [8, True]
    assert (
        v["P2_median_gain_tol4"][1]
        and v["P3_merges_tol2"] == [80, 80, True]
        and v["P4_median_gain_tol2"][1]
    )
    assert v["defect_real_vs_one_tol4"][bs.HELD_OUT[0]] == 0.75
    # merges up more than 5% decides first
    assert (
        bs.verdict({c: result(30.0, 34.0, merges_fix=11) for c in bs.HELD_OUT})[
            "decision"
        ]
        == "COSTS_MERGES"
    )
    # a median gain under 10% at tol 4
    assert (
        bs.verdict({c: result(30.0, 32.0) for c in bs.HELD_OUT})["decision"]
        == "NOT_SUPPORTED"
    )
    # up on only 5 of 8
    mixed = {
        c: result(30.0, 36.0 if i < 5 else 29.0) for i, c in enumerate(bs.HELD_OUT)
    }
    assert bs.verdict(mixed)["P1_gain_tol4_cubes_up"] == [5, False]
    assert bs.verdict(mixed)["decision"] == "NOT_SUPPORTED"
    # no verdict: a missing cube, or an identity problem anywhere
    assert bs.verdict({c: up[c] for c in bs.HELD_OUT[:-1]})["decision"] == "NO_VERDICT"
    bad = dict(up, **{bs.HELD_OUT[3]: result(30.0, 34.0, problems=["x"])})
    assert bs.verdict(bad)["decision"] == "NO_VERDICT"


def test_a_crossing_s_kind_at_the_documented_bounds():
    """Whole: one fiber within 2 voxels of 95% of the window; broken: 80% covered together; 40 voxels on both sides."""
    ref = [along_x(20, 236)]
    xs = bs.crossings(ref, [0], 256)  # the window is x 87.5..167.5

    def kind(fiber):
        return max(bs.crossing_kinds(xs, [fiber], [0]).items(), key=lambda kv: kv[1])[0]

    assert kind(along_x(20, 162)) == "whole"  # 95.7% of the window
    assert kind(along_x(20, 160)) == "broken"  # 93.2%
    assert kind(along_x(20, 150)) == "broken"  # 80.7%
    assert kind(along_x(20, 145)) == "lost"  # 74.5%
    assert kind(along_x(20, 236, y=49.9)) == "whole"  # 1.9 voxels off
    assert (
        bs.crossings([along_x(60, 150)], [0], 256) == []
    )  # 68 voxels before the plane, 22 after


def test_the_decision_rule_at_its_registered_bounds():
    def verdict(per_cube):
        return bs.verdict(dict(zip(bs.HELD_OUT, per_cube, strict=True)))

    # P1: positive on at least 6 of 8 cubes, and a gain of exactly zero is not positive
    six = verdict([result(30.0, 36.0 if i < 6 else 29.0) for i in range(8)])
    assert six["P1_gain_tol4_cubes_up"] == [6, True] and six["decision"] == "SUPPORTED"
    assert verdict([result(30.0, 36.0 if i < 5 else 30.0) for i in range(8)])[
        "P1_gain_tol4_cubes_up"
    ] == [5, False]
    # P2: a median gain of at least 0.10 at tol 4
    assert verdict([result(20.0, 22.1)] * 8)["decision"] == "SUPPORTED"  # 0.105
    assert verdict([result(20.0, 21.9)] * 8)["decision"] == "NOT_SUPPORTED"  # 0.095
    # P3: summed merges at tol 2 rise by at most 5%, whatever tol 4's do
    main = [12] * 4 + [13] * 4  # 100

    def merges(fix):
        return verdict(
            [
                result(30.0, 34.0, merges_main=m, merges_fix=f)
                for m, f in zip(main, fix, strict=True)
            ]
        )

    at5 = merges([13] * 7 + [14])
    assert at5["P3_merges_tol2"] == [100, 105, True] and at5["decision"] == "SUPPORTED"
    assert merges([13] * 6 + [14] * 2)["decision"] == "COSTS_MERGES"  # +6%
    tol4 = [result(30.0, 34.0) for _ in range(8)]
    for r in tol4:
        r["rows"]["real/patched"]["tol4"]["merges"] = 20
    assert verdict(tol4)["decision"] == "SUPPORTED"
    # P4 (0.05 at tol 2) is reported and does not decide
    p4 = verdict([result(30.0, 34.0, erl2_main=20.0, erl2_fix=20.9)] * 8)  # 0.045
    assert p4["P4_median_gain_tol2"][1] is False and p4["decision"] == "SUPPORTED"


def test_the_verdict_reads_only_the_held_out_cubes_and_is_written_once(
    tmp_path, monkeypatch
):
    work, out = tmp_path / "work", tmp_path / "record.json"
    for c in [
        *bs.HELD_OUT,
        "s1_00497_01497_03997_256",
    ]:  # the in-sample cube beside them is not read
        (work / c).mkdir(parents=True)
        (work / c / "result.json").write_text(json.dumps(result(30.0, 34.0)))
    argv = ["x", "verdict", "--work", str(work), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    bs.main()
    first = out.read_bytes()
    assert json.loads(first)["verdict"]["decision"] == "SUPPORTED"
    (work / bs.HELD_OUT[0] / "result.json").write_text(json.dumps(result(30.0, 29.0)))
    with pytest.raises(SystemExit, match="written once"):
        bs.main()
    assert out.read_bytes() == first
