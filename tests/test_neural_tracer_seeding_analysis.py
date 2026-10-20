"""scripts/neural_tracer_seeding_analysis.py and the registration of
docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md."""

import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_seeding_analysis as sa  # noqa: E402

DOC = (
    ROOT / "docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md"
).read_text()
PEN = sa.PEN
R = 9.6 / 7.91


def test_the_predictions_and_decision_rule_are_the_proposals():
    """Registration may not change them: the sha256 of the two sections as proposed in #149 (239a94cb)."""
    s = DOC[
        DOC.index("## Predictions, fixed now") : DOC.index(
            "## What the result cannot do"
        )
    ]
    assert (
        hashlib.sha256(s.encode()).hexdigest()
        == "8f5c31c676d8f9075f50877f91abae0d4fd1c604820c31f199019ad6cffff6ff"
    )


def test_the_document_says_it_is_registered():
    text = " ".join(DOC.split())
    assert "**Status: REGISTERED" in text and "PROPOSED, not registered" not in text
    assert (
        "repro/fibers/run_neural_tracer_seeding_chain.sh" in text
        and "scripts/neural_tracer_seeding_analysis.py" in text
    )


def test_the_arms_are_the_proposals_scales():
    a, b = sa.ARMS["A"], sa.ARMS["B"]
    assert math.isclose(a["smoothing"], 1 / R) and math.isclose(b["smoothing"], R)
    for arm, f in ((a, 1 / R), (b, R)):
        s = arm["settings"]
        assert (s["plane_spacing"], s["fill_spacing"], s["fill_skip"]) == (
            64 * f,
            4 * f,
            4 * f,
        )
        assert (
            s["dot_radius"] == 2.0 and s["dedupe"] == 2.0 and s["min_length"] == 48
        )  # unchanged, as registered
    assert a["settings"]["base_um"] == 9.6 and b["settings"]["base_um"] == 7.91
    assert (a["ct"], a["presence"], b["ct"], b["presence"]) == (
        "ct_9p6",
        "presence_9p6",
        "ct",
        "presence",
    )
    only = {"plane_spacing", "fill_spacing", "fill_skip"}
    assert {k for k in a["settings"] if a["settings"][k] != sa.pa.SETTINGS[k]} == only
    assert {k for k in b["settings"] if b["settings"][k] != sa.f91.SETTINGS[k]} == only


def _record(arm, cube, **change):
    a = sa.ARMS[arm]
    n = a["grid"](cube)
    rec = {
        **a["settings"],
        "checkpoint_sha256": sa.f91.CHECKPOINT_SHA256,
        "box": {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]},
        "ct": f"/x/{a['ct']}/{cube}.zarr",
        "presence": f"/x/{a['presence']}/{cube}_presence.zarr/1",
        "tile_workers": 0,
    }
    rec.update(change)
    return rec


def _seeding(arm, **change):
    s = {
        "presence_smoothing_sigma": sa.ARMS[arm]["smoothing"],
        "hessian_sigma": 1.5,
        "villa_default": 1.0,
    }
    s.update(change)
    return s


CUBE = "s3_00994_00494_01994_512"


@pytest.mark.parametrize("arm", ["A", "B"])
def test_a_registered_run_has_no_identity_problems(arm):
    assert sa.identity_problems(arm, _record(arm, CUBE), _seeding(arm), CUBE) == []


@pytest.mark.parametrize(
    "arm, change, seeding, expect",
    [
        ("A", {"plane_spacing": 64.0}, {}, "plane_spacing"),
        ("B", {"fill_skip": 4.0}, {}, "fill_skip"),
        ("A", {"base_um": 7.91}, {}, "base_um"),
        ("B", {"checkpoint_sha256": "0"}, {}, "checkpoint_sha256"),
        ("A", {"ct": f"/x/ct/{CUBE}.zarr"}, {}, "ct="),
        ("B", {"presence": f"/x/presence_9p6/{CUBE}_presence.zarr/1"}, {}, "presence="),
        ("A", {"box": {"lo": [0.0, 0.0, 0.0], "hi": [256.0, 256.0, 256.0]}}, {}, "box"),
        ("A", {"tile_workers": 3}, {}, "tile_workers"),
        ("B", {}, {"presence_smoothing_sigma": 1.0}, "smoothing"),
        ("A", {}, {"hessian_sigma": 1.2}, "hessian"),
    ],
)
def test_a_run_that_differs_from_its_arm_is_named(arm, change, seeding, expect):
    problems = sa.identity_problems(
        arm, _record(arm, CUBE, **change), _seeding(arm, **seeding), CUBE
    )
    assert problems and any(expect in p for p in problems), problems


def test_a_run_without_its_seeding_record_is_named():
    assert any(
        "seeding.json" in p
        for p in sa.identity_problems("A", _record("A", CUBE), None, CUBE)
    )


def test_the_manipulation_check_compares_recorded_seeds_with_the_probe():
    probe = {
        CUBE: {
            "A": {"flags_smooth": {"dots": 9000}},
            "B": {"flags_smooth": {"dots": 5600}},
        }
    }
    assert sa.manipulation_problems("A", CUBE, 9000, probe) == []
    assert sa.manipulation_problems("B", CUBE, 5601, probe) == [
        "recorded 5601 seed dots, the probe counted 5600"
    ]


def _afv(path, fibers):
    """A minimal complete .afv with the tables afv_to_labels.read_afv reads."""
    con = sqlite3.connect(path)
    con.execute(f"PRAGMA application_id = {0x56434643}")
    con.executescript(
        "CREATE TABLE metadata (key TEXT, value TEXT); CREATE TABLE fibers (id INTEGER);"
        "CREATE TABLE blocks (id INTEGER, fiber_id INTEGER, first_segment INTEGER, points BLOB);"
        "INSERT INTO metadata VALUES ('complete', 'true');"
    )
    for fid, pts in fibers.items():
        con.execute("INSERT INTO fibers VALUES (?)", (fid,))
        con.execute(
            "INSERT INTO blocks VALUES (?, ?, 0, ?)",
            (fid, fid, np.asarray(pts, "<f8").tobytes()),
        )
    con.commit()
    con.close()
    return path


def test_the_smoke_is_identical_only_when_every_fiber_is(tmp_path):
    f = {1: [[0, 0, 0], [1, 2, 3]], 2: [[4, 4, 4], [5, 5, 5], [6, 6, 6]]}
    ref = _afv(tmp_path / "ref.afv", f)
    assert sa.afv_identical(_afv(tmp_path / "same.afv", f), ref)
    assert not sa.afv_identical(
        _afv(tmp_path / "moved.afv", {**f, 2: [[4, 4, 4], [5, 5, 5.5], [6, 6, 6]]}), ref
    )
    assert not sa.afv_identical(_afv(tmp_path / "fewer.afv", {1: f[1]}), ref)
    # The registered check is fiber count and points: the same fibers under other ids are the same run.
    assert sa.afv_identical(_afv(tmp_path / "renumbered.afv", {7: f[2], 9: f[1]}), ref)


def _smoke_run(tmp_path, fibers, record=None, seeding=None, write_seeding=True):
    """A smoke run directory as the chain's launcher writes it, at finding 91's settings and villa's smoothing."""
    run = tmp_path / "identity" / sa.SMOKE_CUBE
    run.mkdir(parents=True)
    n = sa.f91.grid_size(sa.SMOKE_CUBE)
    rec = {
        **sa.f91.SETTINGS,
        "checkpoint_sha256": sa.f91.CHECKPOINT_SHA256,
        "box": {"lo": [0.0, 0.0, 0.0], "hi": [n, n, n]},
        "ct": f"/x/ct/{sa.SMOKE_CUBE}.zarr",
        "presence": f"/x/presence/{sa.SMOKE_CUBE}_presence.zarr/1",
        "tile_workers": 0,
        **(record or {}),
    }
    (run / "run.json").write_text(json.dumps(rec))
    if write_seeding:
        seed = {
            "presence_smoothing_sigma": 1.0,
            "hessian_sigma": 1.5,
            "villa_default": 1.0,
        }
        (run / "seeding.json").write_text(json.dumps({**seed, **(seeding or {})}))
    _afv(run / "fibers.afv", fibers)
    return run


@pytest.mark.parametrize(
    "record, seeding, write_seeding, expect",
    [
        (None, None, False, "seeding.json"),  # villa's tool alone, not the launcher
        ({"tile_workers": 3}, None, True, "tile_workers"),
        (None, {"presence_smoothing_sigma": 1 / sa.R}, True, "smoothing"),
        ({"plane_spacing": 64 / sa.R}, None, True, "plane_spacing"),
        ({"ct": f"/x/ct_9p6/{sa.SMOKE_CUBE}.zarr"}, None, True, "ct="),
    ],
)
def test_the_smoke_must_be_the_launcher_at_villas_default(
    tmp_path, record, seeding, write_seeding, expect
):
    """Villa's tracer is deterministic, so its tool alone reproduces finding 91 too: the identical .afv shows nothing
    about the launcher unless the run's records show the launcher ran at the default."""
    f = {1: [[0, 0, 0], [1, 2, 3]], 2: [[4, 4, 4], [5, 5, 5]]}
    ref = _afv(tmp_path / "ref.afv", f)
    good = sa.smoke_check(_smoke_run(tmp_path / "good", f), ref)
    assert (
        good["ok"]
        and good["identical_to_finding_91"]
        and good["launcher_problems"] == []
    )
    bad = sa.smoke_check(
        _smoke_run(tmp_path / "bad", f, record, seeding, write_seeding), ref
    )
    assert bad["identical_to_finding_91"] and not bad["ok"]
    assert any(expect in p for p in bad["launcher_problems"]), bad
    other = sa.smoke_check(_smoke_run(tmp_path / "other", {1: f[1]}), ref)
    assert not other["ok"] and not other["identical_to_finding_91"]
    assert other["launcher_problems"] == []
    assert sa.smoke_check(tmp_path / "missing", ref) == {
        "cube": sa.SMOKE_CUBE,
        "identical_to_finding_91": False,
        "launcher_problems": ["no run.json"],
        "ok": False,
    }


def _rows(values):
    return {c: ({PEN: v} if v is not None else None) for c, v in values.items()}


ALL, S3 = sa.f91.ALL, sa.f91.S3
NATIVE = {c: {PEN: 10.0} for c in ALL}
COMP = {c: {"tracer": {PEN: 9.0}} for c in ALL}


def _verdict(a, b, comp=COMP):
    return sa.verdict(_rows(a), _rows(b), NATIVE, comp)


def test_p1_and_p3_hold_reads_as_the_seeding_scale():
    v = _verdict({c: 9.0 for c in ALL}, {c: 7.0 for c in ALL})
    assert v["predictions"] == {
        "P1_A_median_pen_ratio_at_least_0.85": True,
        "P2_A_leads_tracer_on_6_of_8_s3": False,  # 9.0 does not beat our tracer's 9.0
        "P3_B_median_pen_ratio_at_most_0.80": True,
    }
    assert v["median_pen_ratio_A"] == 0.9 and v["median_pen_ratio_B"] == 0.7
    assert v["conclusion"].startswith(
        "the seeding scale, fixed in grid voxels, explains most of finding 92's drop"
    )


@pytest.mark.parametrize(
    "a, b, start",
    [
        (
            8.0,
            7.0,
            "seeding density moves the score, but restoring it at 9.6 µm does not recover it",
        ),
        (8.0, 9.0, "the seeding scale is not the cause"),
        (9.0, 9.0, "inconsistent"),
    ],
)
def test_the_decision_rule_rows(a, b, start):
    assert _verdict({c: a for c in ALL}, {c: b for c in ALL})["conclusion"].startswith(
        start
    )


def test_the_thresholds_are_inclusive():
    v = _verdict({c: 8.5 for c in ALL}, {c: 8.0 for c in ALL})
    assert v["predictions"]["P1_A_median_pen_ratio_at_least_0.85"] is True
    assert v["predictions"]["P3_B_median_pen_ratio_at_most_0.80"] is True


def test_p2_counts_scroll3_cubes_ahead_of_our_tracer():
    a = {c: 9.0 for c in ALL} | {c: 9.5 for c in S3[:6]}
    assert (
        _verdict(a, {c: 7.0 for c in ALL})["predictions"][
            "P2_A_leads_tracer_on_6_of_8_s3"
        ]
        is True
    )
    a = {c: 9.0 for c in ALL} | {c: 9.5 for c in S3[:5]}
    v = _verdict(a, {c: 7.0 for c in ALL})
    assert v["predictions"]["P2_A_leads_tracer_on_6_of_8_s3"] is False and v[
        "s3_leading_tracer_A"
    ] == [5, 8]


def test_fewer_than_17_scored_cubes_leave_an_arm_unevaluated():
    a = {c: (9.0 if i < 16 else None) for i, c in enumerate(ALL)}
    v = _verdict(a, {c: 7.0 for c in ALL})
    assert v["predictions"]["P1_A_median_pen_ratio_at_least_0.85"] is None
    assert v["predictions"]["P2_A_leads_tracer_on_6_of_8_s3"] is None
    assert (
        v["predictions"]["P3_B_median_pen_ratio_at_most_0.80"] is True
        and v["conclusion"] is None
    )


@pytest.mark.parametrize(
    "smoke, identity, a, status",
    [
        (False, {}, 9.0, "SMOKE_FAILED"),
        (True, {"A": {CUBE: ["x"]}}, 9.0, "IDENTITY_FAILED"),
        (True, {}, None, "INCOMPLETE"),
        (True, {}, 9.0, "OK"),
    ],
)
def test_the_status(smoke, identity, a, status):
    got, reading = sa.outcome(
        smoke,
        identity,
        _rows({c: a for c in ALL}),
        _rows({c: 7.0 for c in ALL}),
        NATIVE,
        COMP,
    )
    assert got == status and (reading is None) == (
        status in ("SMOKE_FAILED", "IDENTITY_FAILED")
    )


def test_the_chains_smoke_gate_is_the_same_check(tmp_path, capsys):
    """The chain runs `smoke` before any arm: it must refuse villa's tool alone as score() does, not only at scoring."""
    f = {1: [[0, 0, 0], [1, 2, 3]]}
    ref = _afv(tmp_path / "ref.afv", f)
    ok = _smoke_run(tmp_path / "ok", f) / "fibers.afv"
    assert sa.main(["smoke", "--afv", str(ok), "--reference", str(ref)]) == 0
    plain = _smoke_run(tmp_path / "plain", f, write_seeding=False) / "fibers.afv"
    assert sa.main(["smoke", "--afv", str(plain), "--reference", str(ref)]) == 1
    assert (
        "not the launcher at villa's default: no seeding.json"
        in capsys.readouterr().out
    )
    moved = _smoke_run(tmp_path / "moved", {1: [[0, 0, 0], [1, 2, 4]]}) / "fibers.afv"
    assert sa.main(["smoke", "--afv", str(moved), "--reference", str(ref)]) == 1


@pytest.mark.parametrize("launcher", [True, False])
def test_score_fails_the_smoke_unless_the_launcher_ran_it(
    tmp_path, monkeypatch, launcher
):
    """score() end to end, ScrollGT stubbed, no arm traced: with the launcher's smoke it reads INCOMPLETE; with villa's
    tool alone (no seeding.json) it is SMOKE_FAILED, though the .afv is identical."""
    import types

    target = types.ModuleType("scrollgt.fibers.target")
    target.load_fiber_target = lambda path: (None, None, None)
    eval_trace = types.ModuleType("scrollgt.fibers.eval_trace")
    eval_trace.SCORING_VERSION = 3
    eval_trace.score_tracing = None  # nothing is scored: no arm wrote a fibers.afv
    for name, mod in (
        ("scrollgt", types.ModuleType("scrollgt")),
        ("scrollgt.fibers", types.ModuleType("scrollgt.fibers")),
        ("scrollgt.fibers.target", target),
        ("scrollgt.fibers.eval_trace", eval_trace),
    ):
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sa.f91, "SG", tmp_path / "sg")
    for c in ALL:
        d = tmp_path / "sg" / "data" / f"fibers_{c}"
        d.mkdir(parents=True)
        floors = {sa.f91.TRACER: {PEN: 9.0}, sa.f91.CC: {PEN: 8.0}}
        (d / "meta.json").write_text(json.dumps({"floors": floors}))
    f = {1: [[0, 0, 0], [1, 2, 3]]}
    native_work = tmp_path / "native"
    (native_work / sa.SMOKE_CUBE).mkdir(parents=True)
    _afv(native_work / sa.SMOKE_CUBE / "fibers.afv", f)
    work = tmp_path / "work"
    run = _smoke_run(tmp_path / "s", f, write_seeding=launcher)
    (work / "identity").mkdir(parents=True)
    run.rename(work / "identity" / sa.SMOKE_CUBE)
    inputs = {
        "native": {"neural_rows": {c: {PEN: 10.0} for c in ALL}},
        "pitch": {"pitch_rows": {}},
        "probe": {"cubes": {}},
    }
    for name, data in inputs.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(data))
    out = tmp_path / "out.json"
    argv = ["score", "--work", str(work), "--native-work", str(native_work)]
    argv += [f"--{n}={tmp_path / f'{n}.json'}" for n in inputs] + [f"--out={out}"]
    assert sa.main(argv) == 1
    d = json.loads(out.read_text())
    assert d["smoke"]["identical_to_finding_91"] is True
    assert d["smoke"]["ok"] is launcher
    assert d["status"] == ("INCOMPLETE" if launcher else "SMOKE_FAILED")
    assert d["failed_runs"] == {"A": ALL, "B": ALL}
