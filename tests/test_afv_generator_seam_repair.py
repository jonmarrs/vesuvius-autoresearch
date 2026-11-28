"""Finding 140's runner: which blocks meet, the registered verdict lines, and the summary's arithmetic."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "afv_generator_seam_repair", ROOT / "scripts/afv_generator_seam_repair.py"
)
assert _spec and _spec.loader
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)
REG = " ".join(
    (ROOT / "docs/preregistration/2026-11-27_afv_generator_seam_repair.md")
    .read_text()
    .split()
)


def test_blocks_meet_only_their_neighbours():
    # A 2 x 1 x 2 grid of 256-blocks with the CLI's 32-voxel margin, x fastest.
    boxes = []
    for z in (0, 256):
        for x in (0, 256):
            lo = np.maximum(np.array([x, 0, z]) - 32, 0)
            boxes.append(
                (
                    lo,
                    np.minimum(np.array([x, 256, z]) + 256 + 32, 512),
                    None,
                    None,
                    None,
                    None,
                )
            )
    assert sr.meeting(boxes) == [[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]]
    far = [
        (np.array([0, 0, 0]), np.array([100, 100, 100])),
        (np.array([200, 0, 0]), np.array([300, 100, 100])),
    ]
    assert sr.meeting([(*b, None, None, None, None) for b in far]) == [[], []]


def _row(erl4, erl2=1.0, merges=10, cov=0.5, dup=0.1, lost=5):
    return {
        "tol4": {"erl_merge_penalized": erl4, "coverage": cov, "merges": merges},
        "tol2": {"erl_merge_penalized": erl2, "coverage": cov, "merges": merges},
        "duplicated_share": dup,
        "crossings": {"whole": 1, "broken": 1, "lost": lost},
    }


def _results(gains, lost_repaired=20):
    out = {}
    for i, g in enumerate(gains):
        out[f"c{i}"] = {
            "rows": {
                "main": _row(10.0),
                "trim": _row(11.0, cov=0.45),
                "repaired": _row(
                    10.0 * (1 + g), cov=0.48, lost=lost_repaired // len(gains)
                ),
            }
        }
    return out


def test_the_verdict_lines_are_the_registrations():
    assert (sr.UP_LINE, sr.KEEP_MEDIAN, sr.LOSE_MEDIAN, sr.LOST_LINE) == (
        7,
        0.06,
        0.03,
        190,
    )
    assert (
        "ERL at tolerance 4 up over main on at least 7 of 8, median gain at least +6%, and lost crossings at most 190"
        in REG
    )
    assert "median gain under +3%, or up on 5 or fewer" in REG
    keeps = sr.summary(_results([0.1] * 7 + [-0.01]))
    assert (
        keeps["up_tol4"] == 7
        and keeps["median_gain_tol4"] == 0.1
        and sr.verdict(keeps) == "REPAIR_KEEPS_THE_GAIN"
    )
    too_many_lost = sr.summary(_results([0.1] * 8, lost_repaired=8 * 25))
    assert (
        too_many_lost["lost_crossings"]["repaired"] == 200
        and sr.verdict(too_many_lost) == "REPAIR_PARTLY"
    )
    assert sr.verdict(sr.summary(_results([0.02] * 8))) == "REPAIR_LOSES_THE_GAIN"
    assert (
        sr.verdict(sr.summary(_results([0.1] * 5 + [-0.1] * 3)))
        == "REPAIR_LOSES_THE_GAIN"
    )


def test_the_zone_addendum_gates_on_finding_107s_own_trim():
    import afv_generator_default_zone as dz

    assert (
        "Addendum 1 (2026-11-27, after the eighteen cubes, before the 1024³ zone runs)"
        in REG
    )
    assert "must equal finding 107's recorded rows" in REG
    # finding 107's zone trim is the zone form finding 109 and this finding's Scrolls 1 and 5 used
    assert dz.PATCHED_STITCH_SHA256.startswith("362b78b12b2abf1b")
    assert (dz.ZONE, dz.BLOCK, dz.MARGIN) == (1024, 512, 32)


def test_the_summary_compares_each_arm_with_main():
    s = sr.summary(_results([0.1] * 8))
    assert s["lost_crossings"] == {"main": 40, "trim": 40, "repaired": 16}
    assert s["coverage_tol4_median_change"] == {"trim": -0.1, "repaired": -0.04}
    assert s["merges_tol2"] == {"main": 80, "trim": 80, "repaired": 80}


GEN = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen")


def test_addendum_2_is_registered_with_its_files_and_lines():
    assert "Addendum 2 (2026-11-28, before any run with villa #2434)" in REG
    patch = ROOT / "repro/fibers/villa_2434_on_pr1934_afv_spline_generator.patch"
    assert (
        sr.sha(patch) == sr.PATCH_2434_SHA256
        and f"`{sr.PATCH_2434_SHA256[:8]}…`" in REG
    )
    for name, digest in sr.PACKAGE_2434_SHA256.items():
        assert f"`{digest[:8]}…` (`{name.split('/')[-1]}`)" in REG
        assert f"src/vesuvius/afv_spline_generator/{name}" in patch.read_text()
    assert f"`{sr.REPAIRED_HEAD_SHA256[:8]}…`" in REG and f"(`{sr.GATE_CUBE}`)" in REG
    assert sorted(sr.SETS["scroll3"][0])[0] == sr.GATE_CUBE
    assert (sr.UP_LINE, sr.KEEP_MEDIAN, sr.LOSE_MEDIAN, sr.LOST_MARGIN) == (
        7,
        0.06,
        0.03,
        18,
    )
    assert (
        sr.LOST_LINE == 172 + sr.LOST_MARGIN
    )  # finding 140's line, main's 172 plus the margin
    assert ("ERL at tolerance 4 up over main on at least 7 of 8, median gain at least +6%, and lost crossings at "
            "most main's plus 18") in REG  # fmt: skip


def _results_2434(gains, lost_main=5, lost_repaired=5):
    out = {}
    for i, g in enumerate(gains):
        out[f"c{i}"] = {"rows": {"main": _row(10.0, lost=lost_main),
                                 "repaired": _row(10.0 * (1 + g), cov=0.48, lost=lost_repaired)}}  # fmt: skip
    return out


def test_the_addendum_2_verdict_takes_the_lost_line_from_main():
    f140 = {c: {"rows": {"main": _row(10.0)}} for c in (f"c{i}" for i in range(8))}
    holds = sr.summary2434(
        _results_2434([0.1] * 7 + [-0.01], lost_main=30, lost_repaired=32), f140
    )
    assert (
        holds["lost_crossings"] == {"main": 240, "repaired": 256}
        and holds["up_tol4"] == 7
    )
    assert holds["main_change_from_2434_tol4_median"] == 0.0
    assert sr.verdict2434(holds) == "GAIN_HOLDS_AFTER_2434"  # 256 <= 240 + 18
    over = sr.summary2434(
        _results_2434([0.1] * 8, lost_main=30, lost_repaired=33), f140
    )
    assert sr.verdict2434(over) == "GAIN_PARTLY_AFTER_2434"  # 264 > 258
    assert (
        sr.verdict2434(sr.summary2434(_results_2434([0.02] * 8), f140))
        == "GAIN_LOST_AFTER_2434"
    )
    assert (
        sr.verdict2434(sr.summary2434(_results_2434([0.1] * 5 + [-0.1] * 3), f140))
        == "GAIN_LOST_AFTER_2434"
    )


def _package(root, files):
    pkg = root / "vesuvius" / "afv_spline_generator"
    for name, text in files.items():
        (pkg / name).parent.mkdir(parents=True, exist_ok=True)
        (pkg / name).write_text(text)
    return root


def test_the_2434_package_gate_names_every_file_that_is_not_1934s_or_2434s(
    tmp_path, monkeypatch
):
    old = {"cli.py": "cli", "cleanup.py": "c0", "extend/catalog.py": "k0", "extend/expander.py": "e0",
           "extend/stitch.py": "s0", "extend/overlap.py": "o"}  # fmt: skip
    new = {
        **old,
        "cleanup.py": "c1",
        "extend/catalog.py": "k1",
        "extend/expander.py": "e1",
        "extend/stitch.py": "s1",
    }
    a, b = _package(tmp_path / "old", old), _package(tmp_path / "new", new)
    digests = {
        n: sr.sha(b / "vesuvius/afv_spline_generator" / n)
        for n in sr.PACKAGE_2434_SHA256
    }
    monkeypatch.setattr(sr, "PACKAGE_2434_SHA256", digests)
    assert sr.package_problems(a, b) == []
    _package(b, {"extend/overlap.py": "changed", "extra.py": "x"})
    (b / "vesuvius/afv_spline_generator/cli.py").unlink()
    problems = sr.package_problems(a, b)
    assert any(p.startswith("extend/overlap.py sha256") for p in problems)
    assert (
        "extra.py is not in #1934's package" in problems
        and "cli.py missing from the #2434 package" in problems
    )
    _package(b, {"extend/catalog.py": "k0"})  # #1934's catalogue, without #2434
    assert any(
        p.startswith("extend/catalog.py sha256") for p in sr.package_problems(a, b)
    )


def test_the_reproduction_gate_needs_finding_140s_own_rows_and_files(tmp_path):
    import json

    f140 = json.loads((ROOT / "reports/afv_generator_seam_repair.json").read_text())
    assert sr.gate_problems(tmp_path, f140) == [f"{tmp_path}/scroll3/{sr.GATE_CUBE}/result.json missing: the gate cube has not run"]  # fmt: skip
    recorded = f140["cubes"]["scroll3"][sr.GATE_CUBE]
    path = tmp_path / "scroll3" / sr.GATE_CUBE / "result.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(recorded))
    assert sr.gate_problems(tmp_path, f140) == []
    changed = json.loads(json.dumps(recorded))
    changed["rows"]["repaired"]["written"] += 1
    changed["sha256"]["repaired_stitch"] = sr.REPAIRED_HEAD_SHA256
    path.write_text(json.dumps(changed))
    assert sr.gate_problems(tmp_path, f140) == ["gate: repaired does not reproduce finding 140's row",
                                                "gate: not the files finding 140 ran"]  # fmt: skip


@pytest.mark.skipif(
    not (GEN / "pr1934_2434").exists(), reason="the generator's local package copies"
)
def test_the_local_2434_package_passes_its_gate():
    assert (
        sr.package_problems(
            GEN / "pr1934/vesuvius/src", GEN / "pr1934_2434/vesuvius/src"
        )
        == []
    )
