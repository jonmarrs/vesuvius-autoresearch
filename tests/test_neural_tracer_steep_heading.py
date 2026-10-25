"""scripts/neural_tracer_heading_arm.py, scripts/neural_tracer_steep_heading.py and their chain: the registered design
of docs/preregistration/2026-10-25_neural_tracer_steep_heading.md."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import types
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_ct_context as cc  # noqa: E402
import neural_tracer_ct_context_512 as c5  # noqa: E402
import neural_tracer_heading_arm as arm  # noqa: E402
import neural_tracer_heading_residual as hr  # noqa: E402
import neural_tracer_steep_heading as sh  # noqa: E402

CHAIN = _REPO / "repro/fibers/run_neural_tracer_steep_heading_chain.sh"
F97_CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_chain.sh"
F98_CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_512_chain.sh"
REG = _REPO / "docs/preregistration/2026-10-25_neural_tracer_steep_heading.md"
TRACERS = Path(os.environ.get("VILLA_ROOT", _REPO / "villa")) / (
    "vesuvius/src/vesuvius/neural_tracing/tracers"
)
COV, PREC, PEN = sh.COV, sh.PREC, sh.PEN


def _villa(rel: str) -> str:
    if not TRACERS.exists() and "VILLA_ROOT" not in os.environ:
        pytest.skip("Villa tracer sources absent; set VILLA_ROOT to check them")
    return (TRACERS / rel).read_text()


def _function(source: str, name: str) -> str:
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)  # fmt: skip
    segment = ast.get_source_segment(source, node)
    assert segment is not None, name
    return segment


class _Err(ValueError):
    pass


def _villas_own(normals: dict):
    """villa's `_seed_heading`, `seed_headings` and `sheet_heading`, executed from villa's source, with its CT reads
    replaced by a table of sheet normals by position."""
    volume, ct = _villa("fibers/tracing/volume.py"), _villa("fibers/frames/ct.py")
    ns: dict = {"np": np, "SeedHeadingError": _Err, "_WORKER_VOL": "vol"}
    for src, name in ((ct, "fiber_family"), (ct, "sheet_heading"), (volume, "_seed_heading"), (volume, "seed_headings")):  # fmt: skip
        exec(_function(src, name), ns)

    def ct_normal(vol, xyz):
        n = normals[tuple(np.asarray(xyz).tolist())]
        if n is None:
            raise _Err("CT seed context crosses the volume boundary")
        return n

    ns["ct_seed_heading"] = lambda vol, xyz, family: ns["sheet_heading"](
        ct_normal(vol, xyz), family
    )
    return ns, ct_normal


def _dots(seed=0, n=400):
    """Dots with random sheet normals and presence directions, a few with no CT axis and a few degenerate."""
    rng = np.random.default_rng(seed)
    xyz = np.arange(3 * n, dtype=float).reshape(n, 3)
    normals = {}
    direction = rng.normal(size=(n, 3))
    direction /= np.linalg.norm(direction, axis=1, keepdims=True)
    for i, p in enumerate(xyz):
        v = rng.normal(size=3)
        normals[tuple(p.tolist())] = None if i % 97 == 0 else v / np.linalg.norm(v)
    normals[tuple(xyz[5].tolist())] = np.array(
        [0.0, 0.0, 1.0]
    )  # an H axis villa calls ambiguous
    family = np.array(["H" if i % 3 else "V" for i in range(n)])
    return {
        "xyz": xyz,
        "family": family,
        "direction": direction,
        "score": np.arange(n),
    }, normals


class _Pool:
    def __init__(self):
        self.chunks = []

    def map(self, fn, tasks, chunksize):
        self.chunks.append(chunksize)
        return map(fn, tasks)


def test_the_villa_arm_is_villas_seed_heading():
    dots, normals = _dots()
    ns, ct_normal = _villas_own(normals)

    def ours(task):  # arm_heading with the same CT reads
        xyz, family, direction, a = task
        try:
            n = ct_normal("vol", xyz)
            h = ns["sheet_heading"](n, family)
        except _Err:
            return None, "error"
        return arm.choose(h, n, direction, a)

    villa_pool, our_pool, tally = _Pool(), _Pool(), Counter()
    want, want_keep = ns["seed_headings"]("vol", dict(dots), villa_pool)
    got, got_keep = arm.patched_seed_headings("villa", tally, ours)(
        "vol", dict(dots), our_pool
    )
    assert np.array_equal(want_keep, got_keep) and set(want) == set(got)
    assert all(np.array_equal(want[k], got[k]) for k in want)
    assert villa_pool.chunks == our_pool.chunks == [max(1, len(dots["xyz"]) // 32)]
    assert (
        tally["agree"] == want_keep.sum()
        and tally["skipped"] > 50
        and tally["error"] > 0
    )
    assert sum(tally.values()) == len(dots["xyz"])


def test_every_arm_heads_an_agreeing_dot_as_villa_does():
    dots, normals = _dots(seed=1)
    ns, _ = _villas_own(normals)
    for a in arm.ARMS:
        for x, f, d in zip(
            dots["xyz"], dots["family"], dots["direction"], strict=False
        ):
            v = ns["_seed_heading"]((x, f, d))
            if v is None:
                continue
            n = normals[tuple(x.tolist())]
            h, kind = arm.choose(ns["sheet_heading"](n, f), n, d, a)
            assert kind == "agree" and np.array_equal(h, v)


def _disagreeing(normal, family="H"):
    """villa's H axis for `normal`, and a presence direction 60 degrees from it, in the sheet."""
    z = np.array([0.0, 0.0, 1.0])
    h = np.cross(z, normal) / np.linalg.norm(np.cross(z, normal))
    other = np.cross(normal, h)
    return h, np.cos(np.radians(60)) * h + np.sin(np.radians(60)) * other


def test_keep_traces_villas_own_axis_signed_along_the_presence():
    n = np.array([0.0, 0.6, 0.8])
    h, d = _disagreeing(n)
    for sign in (1, -1):
        got, kind = arm.choose(h, n, sign * d, "keep")
        assert kind == "rescued" and np.array_equal(got, sign * h)
    assert arm.choose(h, n, d, "villa") == (None, "skipped")


def test_sheet_traces_the_presence_direction_in_the_sheet():
    n = np.array([0.0, 0.6, 0.8])
    h, d = _disagreeing(n)
    tilt = (
        np.cos(np.radians(20)) * d + np.sin(np.radians(20)) * n
    )  # 20 degrees out of the sheet
    got, kind = arm.choose(h, n, tilt, "sheet")
    assert kind == "rescued" and abs(np.linalg.norm(got) - 1) < 1e-12
    assert abs(got @ n) < 1e-12 and got @ tilt > 0 and np.allclose(got, d)
    far = np.cos(np.radians(60)) * d + np.sin(np.radians(60)) * n
    assert arm.choose(h, n, far, "sheet")[1] == "rescued_far"  # counted, still traced
    assert arm.choose(h, n, n, "sheet") == (None, "degenerate")
    # the floor is villa's own: sheet_heading's 1e-3
    assert arm.DEGENERATE == 1e-3 and "if size < 1e-3:" in _function(
        _villa("fibers/frames/ct.py"), "sheet_heading"
    )


def test_the_35_degree_line_is_villas():
    n = np.array([0.0, 0.6, 0.8])
    h, _ = _disagreeing(n)
    other = np.cross(n, h)
    for degrees, kind in (
        (34.9, "agree"),
        (35.1, "skipped"),
        (145.1, "agree"),
        (144.9, "skipped"),
    ):
        r = np.radians(degrees)
        assert arm.choose(h, n, np.cos(r) * h + np.sin(r) * other, "villa")[1] == kind
    assert np.cos(np.radians(35)) == arm.AGREE_COS
    with pytest.raises(ValueError, match="unknown arm"):
        arm.choose(h, n, h, "flip")


def test_the_launcher_needs_one_arm():
    assert arm.split_argv(["--arm", "sheet", "--out", "o", "--box", "1"]) == (
        "sheet",
        ["--out", "o", "--box", "1"],
    )
    assert arm.split_argv(["--arm=keep", "--out", "o"]) == ("keep", ["--out", "o"])
    for bad in (
        ["--out", "o"],
        ["--arm", "flip"],
        ["--arm", "keep", "--arm=sheet"],
        ["--ar", "keep"],
    ):
        with pytest.raises(SystemExit):
            arm.split_argv(bad)


def test_a_resume_needs_the_same_arm(tmp_path):
    out = tmp_path / "run"
    assert arm.record_arm(out, "sheet")["arm"] == "sheet"
    assert arm.record_arm(out, "sheet")["arm"] == "sheet"
    with pytest.raises(SystemExit, match="another arm"):
        arm.record_arm(out, "keep")
    other = tmp_path / "plain"
    other.mkdir()
    (other / "run.json").write_text("{}")
    with pytest.raises(SystemExit, match="without this launcher"):
        arm.record_arm(other, "villa")


def test_main_runs_villas_main_patched_and_records_the_arm(tmp_path, monkeypatch):
    """main() swaps villa's seed_headings and seed-heading policy for the run, then puts them back."""
    seen = {}

    def villa_main(rest):
        seen["rest"], seen["policy"] = rest, fake.SEED_HEADING_POLICY
        dots, _ = _dots(seed=2, n=64)

        fake.seed_headings("vol", dots, _Pool())
        seen["arms"] = set(heads)
        return 0

    heads: list = []

    def fn(task):  # stands in for the workers' arm_heading
        heads.append(task[3])
        return arm.choose(
            np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), task[2], task[3]
        )

    monkeypatch.setattr(arm, "arm_heading", fn)

    original = lambda *a: None  # noqa: E731
    fake = types.SimpleNamespace(
        main=villa_main,
        seed_headings=original,
        SEED_HEADING_POLICY="ct_sheet_hv_sigma2_8_v2",
    )
    pkg = "vesuvius.neural_tracing.tracers.fibers.tracing"
    for i, part in enumerate(pkg.split(".")):
        name = ".".join(pkg.split(".")[: i + 1])
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules[pkg].volume = fake
    monkeypatch.setitem(sys.modules, pkg + ".volume", fake)
    out = tmp_path / "run"
    assert arm.main(["--arm", "sheet", "--out", str(out), "--box", "0,0,0,1,1,1"]) == 0
    assert seen["rest"] == ["--out", str(out), "--box", "0,0,0,1,1,1"] and seen[
        "arms"
    ] == {"sheet"}
    assert seen["policy"] == "ct_sheet_hv_sigma2_8_v2+presence_in_sheet_v1"
    assert (
        fake.seed_headings is original
        and fake.SEED_HEADING_POLICY == "ct_sheet_hv_sigma2_8_v2"
    )
    rec = json.loads((out / "heading_arm.json").read_text())
    assert (
        rec["arm"] == "sheet"
        and sum(rec["offered"].values()) == 64
        and set(rec["offered"]) == set(arm.KINDS)
    )


def test_villa_is_as_the_registration_says():
    """The reachability the registration rests on, in villa's source at the pin."""
    volume = _villa("fibers/tracing/volume.py")
    assert (
        "batch, keep = seed_headings(self.vol, batch, self.tracer.axis_pool)" in volume
    )
    assert (
        "heads = list(pool.map(_seed_heading, tasks, chunksize=max(1, len(tasks)//32)))"
        in volume
    )
    assert (
        "mp_context=multiprocessing.get_context('spawn')" in volume
        and "_WORKER_VOL = CTVolume(" in volume
    )
    assert "seed_heading_policy=SEED_HEADING_POLICY" in volume
    # traced both ways from the heading; the owned test reads the presence direction
    assert "np.concatenate([batch['heading'], -batch['heading']])" in volume
    assert (
        "self.owned.owner(dots['xyz'][part][m], dots['direction'][part][m], r)"
        in volume
    )
    ct = _villa("fibers/frames/ct.py")
    assert "return sheet_heading(ct_normal(vol, pos_xyz), family)" in ct
    # training seeds take the CT axis whatever its angle to the tangent: no 35-degree test
    for rel in ("fibers/data/seeds.py", "fibers/data/targets.py"):
        text = _villa(rel)
        assert "oriented_seed_heading(" in text and "radians" not in text, rel
    assert "return -axis if np.dot(axis, direction) < 0 else axis" in ct


def test_the_cubes_are_findings_97_and_98s():
    assert len(sh.HELD) == 10 and len(sh.IN_SAMPLE) == 11
    assert sorted(sh.ALL_CUBES) == sorted(cc.ALL_CUBES + c5.ALL_CUBES)
    assert sorted(sh.HELD_S5) == sorted(hr.HELD_256) and sh.S3 == c5.S3_CUBES
    assert sh.SMOKE in sh.HELD_S5
    base2, _, rec = sh.baseline()
    assert set(base2) == set(rec) == set(sh.ALL_CUBES)
    assert all(rec[c]["no_heading"] > 0 for c in sh.HELD)


def test_the_box_is_findings_97_and_98s():
    assert sh.box("s5_13497_01497_02497_256") == "64,64,64,192,192,192"
    assert sh.box("s3_00994_00494_01994_512") == "64,64,64,320,320,320"
    text = CHAIN.read_text()
    assert "box=64,64,64,192,192,192" in text and "box=64,64,64,320,320,320" in text
    assert (
        '"64,64,64,192,192,192"' in F97_CHAIN.read_text()
        and '"64,64,64,320,320,320"' in F98_CHAIN.read_text()
    )


def _flags(text: str, after: str) -> set[str]:
    cmd = text.split(after, 1)[1].split(">", 1)[0]
    return set(re.findall(r"--[a-z-]+", cmd))


def test_the_trace_is_findings_97_and_98s_command():
    ours = CHAIN.read_text()
    for theirs in (F97_CHAIN.read_text(), F98_CHAIN.read_text()):
        ckpt = re.compile(r'^CKPT="([^"]+)"$', re.M)
        assert ckpt.search(ours).group(1) == ckpt.search(theirs).group(1)
        assert _flags(ours, '"$W/neural_tracer_heading_arm.py"') - {"--arm"} == _flags(
            theirs, "tracers.fibers.tracing.volume"
        )
    assert (
        "--ct-level 0 --ct-grid-scale 1 --grid-scale 2" in ours
        and "--base-um 7.91" in ours
    )
    # their inputs, not new ones
    assert "base=$T/ct_context_run" in ours and "base=$T/ct_context_512_run" in ours
    assert (
        '--ct "$base/ct/$3.zarr"' in ours
        and '--presence "$base/presence/${3}_presence.zarr/1"' in ours
    )
    assert '--afv-template "$G/run/$3.afv"' in ours


def _cubes(text: str, name: str) -> list[str]:
    return re.search(rf'^{name}="(.*?)"', text, re.S | re.M).group(1).split()


def test_the_smoke_gates_the_arms_and_held_out_runs_first():
    text = CHAIN.read_text()
    assert _cubes(text, "HELD") == sh.HELD and _cubes(text, "IN_SAMPLE") == sh.IN_SAMPLE
    assert (
        f"SMOKE={sh.SMOKE}" in text and 'trace villa "$W/smoke/$SMOKE" "$SMOKE"' in text
    )
    assert (
        text.index("trace villa")
        < text.index('steep_heading.py" smoke')
        < text.index("for SET in HELD IN_SAMPLE")
    )
    assert "exit 4" in text.split('say "SMOKE_OK"')[0]
    assert "for ARM in sheet keep; do" in text and tuple(sh.ARMS) == ("sheet", "keep")
    assert (
        'W="${W:-$T/steep_heading_run}"' in text
        and sh.BASE_RUNS[256] == sh.T / "ct_context_run"
    )
    assert (
        "tracers\\.fibers\\.tracing\\.volume|neural_tracer_heading_arm|" in text
    )  # an arm run is a GPU job


def _local_imports(script: str, seen: set[str]) -> set[str]:
    for node in ast.walk(ast.parse((_REPO / "scripts" / f"{script}.py").read_text())):
        for name in (
            [a.name for a in node.names] if isinstance(node, ast.Import) else []
        ):
            if (_REPO / "scripts" / f"{name}.py").exists() and name not in seen:
                seen.add(name)
                _local_imports(name, seen)
    return seen


def test_the_chain_freezes_every_script_it_runs():
    frozen = (
        re.search(r"for f in (.*?); do", CHAIN.read_text(), re.S)
        .group(1)
        .replace("\\\n", " ")
        .split()
    )
    want = _local_imports(
        "neural_tracer_steep_heading",
        {"neural_tracer_steep_heading", "neural_tracer_heading_arm"},
    )
    assert set(frozen) == {f"{s}.py" for s in want}
    text = CHAIN.read_text()
    assert text.index('export PYTHONPATH="$REPO/src') < text.index(
        '"$PY" "$LOOPDIR/scripts/loop_control.py"'
    )


def _row(cov, prec=0.5, pen=10.0):
    return {COV: cov, PREC: prec, PEN: pen}


def _case(sheet_s5=1.3, sheet_s3=1.1, keep=1.05, prec=0.0, inside=1.0, skipped=0.0):
    base = {c: _row(0.5) for c in sh.ALL_CUBES}
    base_rec = {c: {"no_heading_share": 0.2} for c in sh.ALL_CUBES}
    rows, records = {}, {}
    for a, f in (("sheet", None), ("keep", keep)):
        rows[a] = {}
        for c in sh.ALL_CUBES:
            g = (sheet_s5 if c in sh.HELD_S5 else sheet_s3) if f is None else f
            g = inside if c in sh.IN_SAMPLE else g
            rows[a][c] = _row(0.5 * g, 0.5 + prec)
        records[a] = {c: {"no_heading_share": skipped} for c in sh.ALL_CUBES}
    return rows, base, records, base_rec


def test_the_decision_rule():
    v = sh.verdict(*_case())
    assert (
        all(v[f"prediction_P{i}"] for i in range(1, 6))
        and sh.status(True, v, []) == "OK"
    )
    assert v["reading"] == ("a seed heading that follows the sheet recovers coverage on the held-out cubes, keeping "
                            "its precision; the heading matters: villa's own axis, kept, recovers less")  # fmt: skip
    v = sh.verdict(*_case(keep=1.5))
    assert not v["prediction_P4"] and v["reading"].endswith(
        "what loses the coverage is the 35° skip, not the heading"
    )
    v = sh.verdict(*_case(prec=-0.031))
    assert not v["prediction_P3"] and ", at a cost in precision;" in v["reading"]
    assert sh.verdict(*_case(prec=-0.0299))["prediction_P3"]  # at most 0.03 below
    v = sh.verdict(*_case(sheet_s5=1.14))
    assert not v["prediction_P1"] and v["prediction_P2"]
    assert (
        "on Scroll 3, not as registered on the two held-out Scroll-5 cubes"
        in v["reading"]
    )
    assert sh.verdict(*_case(sheet_s5=1.15))["prediction_P1"]
    v = sh.verdict(*_case(sheet_s3=1.04, keep=1.0))
    assert v["prediction_P1"] and not v["prediction_P2"]
    assert (
        "on the two held-out Scroll-5 cubes, not as registered on Scroll 3"
        in v["reading"]
    )
    v = sh.verdict(*_case(sheet_s5=1.1, sheet_s3=1.0, keep=1.0))
    assert v["reading"].startswith(
        "tracing the skipped dots adds less coverage than registered"
    )
    v = sh.verdict(*_case(inside=1.06))
    assert not v["prediction_P5"] and v["prediction_P1"]  # P5 apart from the reading
    assert sh.verdict(*_case(inside=0.95))["prediction_P5"]


def test_p2_needs_six_rises_and_the_median():
    rows, base, records, base_rec = _case()
    for c in sh.S3[:3]:
        rows["sheet"][c] = _row(0.5 * 0.99)
    assert not sh.verdict(rows, base, records, base_rec)["prediction_P2"]  # 5 of 8 rise
    rows["sheet"][sh.S3[0]] = _row(0.5 * 1.2)
    assert sh.verdict(rows, base, records, base_rec)[
        "prediction_P2"
    ]  # 6 of 8, median 1.1
    for c, f in zip(
        sh.S3, (1.01,) * 6 + (1.3, 1.3), strict=False
    ):  # all rise, mean 1.08, median 1.01
        rows["sheet"][c] = _row(0.5 * f)
    assert not sh.verdict(rows, base, records, base_rec)["prediction_P2"]


def test_p4_counts_the_held_out_cubes():
    rows, base, records, base_rec = _case(sheet_s5=1.3, sheet_s3=1.1, keep=1.2)
    assert (
        sh.verdict(rows, base, records, base_rec)["prediction_P4"] is False
    )  # above keep on 2 of 10
    for c in sh.S3[:5]:
        rows["keep"][c] = _row(0.5 * 1.0)
    assert sh.verdict(rows, base, records, base_rec)["prediction_P4"]  # 7 of 10


def test_the_manipulation_check_and_the_status():
    v = sh.verdict(*_case(skipped=0.04))  # a fifth of the baseline's 0.2
    assert v["manipulation_ok"] == {"sheet": True, "keep": True}
    v = sh.verdict(*_case(skipped=0.041))
    assert v["reading"] is None and sh.status(True, v, []) == "MANIPULATION_FAILED"
    assert sh.status(False, sh.verdict(*_case()), []) == "SMOKE_FAILED"
    rows, base, records, base_rec = _case()
    del rows["keep"][sh.S3[0]]
    v = sh.verdict(rows, base, records, base_rec)
    assert v["prediction_P1"] is None and sh.status(True, v, ["keep/x"]) == "INCOMPLETE"


def test_run_record_reads_the_last_line_of_each_tile_and_the_tally(tmp_path):
    lines = [
        {"tile": "a", "dots": 9, "no_heading": 5},
        {"tile": "a", "dots": 10, "no_heading": 1, "traced": 7},
    ]
    (tmp_path / "tiles.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n"
    )
    (tmp_path / "heading_arm.json").write_text(
        json.dumps({"arm": "keep", "offered": {"agree": 3}})
    )
    r = sh.run_record(tmp_path)
    assert (r["dots"], r["no_heading"], r["traced"], r["tiles"]) == (10, 1, 7, 1)
    assert (
        r["no_heading_share"] == 0.1
        and r["arm"] == "keep"
        and r["offered"] == {"agree": 3}
    )


def test_no_ratio_over_zero():
    with pytest.raises(ValueError, match="baseline coverage of 0"):
        sh.factors({"c": _row(0.1)}, {"c": _row(0.0)}, ["c"])


def test_the_registered_thresholds_are_the_documents():
    doc = " ".join(REG.read_text().split())
    assert sh.P1_FACTOR == 1.15 and "Coverage factor at least 1.15 on both." in doc
    assert (sh.P2_RISE_AT_LEAST, sh.P2_MEDIAN) == (6, 1.05)
    assert (
        "Coverage rises on at least 6 of the 8 cubes, with a median factor of at least 1.05."
        in doc
    )
    assert (sh.P3_DROP, sh.P3_AT_LEAST) == (0.03, 8)
    assert (
        "On at least 8 of the 10 held-out cubes, its precision is at most 0.03 below the baseline's"
        in doc
    )
    assert (
        sh.P4_AT_LEAST == 7
        and "Sheet's coverage is above keep's on at least 7 of the 10 held-out cubes."
        in doc
    )
    assert (
        sh.P5_BAND == (0.95, 1.05)
        and "coverage factors lie in 0.95–1.05 on all 11 in-sample cubes" in doc
    )
    assert (
        sh.M2_SHARE == 0.2
        and "each arm skips at most a fifth of the baseline's share of dots" in doc
    )
    assert (
        arm.FAR_OUT_OF_SHEET == 45.0
        and "more than 45° out of the sheet are counted, never acted on" in doc
    )
    readings = " | ".join(sh.verdict(*_case(**kw))["reading"] for kw in (
        {}, {"keep": 1.5}, {"prec": -0.04}, {"sheet_s5": 1.1}, {"sheet_s3": 1.0, "keep": 1.0},
        {"sheet_s5": 1.1, "sheet_s3": 1.0, "keep": 1.0, "prec": -0.04}))  # fmt: skip
    for text in ("a seed heading that follows the sheet recovers coverage on the held-out cubes",
                 "recovers coverage on the two held-out Scroll-5 cubes, not as registered on Scroll 3",
                 "recovers coverage on Scroll 3, not as registered on the two held-out Scroll-5 cubes",
                 ", keeping its precision", ", at a cost in precision",
                 "the heading matters: villa's own axis, kept, recovers less",
                 "but villa's own axis, kept, recovers about as much: what loses the coverage is the 35° skip, not "
                 "the heading",
                 "tracing the skipped dots adds less coverage than registered: on the held-out cubes the skip is not "
                 "the main limit on coverage", ", and the added traces cost precision"):  # fmt: skip
        assert text in doc and text in readings, text
    assert (
        "+presence_in_sheet_v1" in arm.POLICY_SUFFIX["sheet"]
        and arm.POLICY_SUFFIX["keep"] == "+keep_ct_axis_v1"
    )


def test_the_registrations_figures_are_the_evidence():
    doc = " ".join(REG.read_text().split())
    base2, _, rec = sh.baseline()
    offered = {c: rec[c]["dots"] - rec[c]["owned_dots"] for c in sh.ALL_CUBES}
    a, b = sh.HELD_S5
    assert (
        f"it skipped {rec[a]['no_heading']} of {offered[a]} and {rec[b]['no_heading']} of {offered[b]}"
        in doc
    )
    s3 = [rec[c]["no_heading"] / offered[c] for c in sh.S3]
    n3 = [rec[c]["no_heading"] for c in sh.S3]
    assert (
        f"and {min(n3)}–{max(n3)} on Scroll 3 ({min(s3):.2f}–{max(s3):.2f} of those offered)"
        in doc
    )
    up = {
        c: (rec[c]["traced"] + rec[c]["no_heading"]) / rec[c]["traced"] for c in sh.HELD
    }
    assert (
        f"traces would rise {up[a]:.2f}× and {up[b]:.2f}× on the two Scroll-5 cubes"
        in doc
    )
    assert (
        f"{min(up[c] for c in sh.S3):.2f}–{max(up[c] for c in sh.S3):.2f}× on Scroll 3"
        in doc
    )
    inside = [rec[c]["no_heading"] for c in sh.IN_SAMPLE]
    share = max(rec[c]["no_heading"] / offered[c] for c in sh.IN_SAMPLE)
    assert (
        f"Those cubes' runs skipped {min(inside)}–{max(inside)} dots, at most {share:.3f} of the dots offered."
        in doc
    )
    assert (
        f"{rec[a]['no_heading'] / rec[a]['dots']:.3f} and {rec[b]['no_heading'] / rec[b]['dots']:.3f}"
        in doc
    )


def test_p5_holds_each_arm_and_the_manipulation_check_reads_the_held_out_cubes():
    rows, base, records, base_rec = _case()
    rows["keep"][sh.IN_SAMPLE[0]] = _row(0.5 * 1.06)
    assert sh.verdict(rows, base, records, base_rec)["prediction_P5"] is False
    rows, base, records, base_rec = _case()
    for a in sh.ARMS:
        for c in sh.IN_SAMPLE:
            records[a][c] = {
                "no_heading_share": 0.5
            }  # in sample the baseline barely skips: not a check there
    assert sh.verdict(rows, base, records, base_rec)["manipulation_ok"] == {
        "sheet": True,
        "keep": True,
    }
    records["keep"][sh.S3[-1]] = {"no_heading_share": 0.1}
    assert sh.verdict(rows, base, records, base_rec)["manipulation_ok"] == {
        "sheet": True,
        "keep": False,
    }
