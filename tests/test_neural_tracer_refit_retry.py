"""scripts/neural_tracer_refit_arm.py, scripts/neural_tracer_refit_retry.py and their chain: the proposed pilot's design
(docs/preregistration/2026-11-02_neural_tracer_refit_retry.md), in villa's source at the pin and in our own scripts."""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import re
import statistics
import sys
import types
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_refit_arm as arm  # noqa: E402

TRACERS = Path(os.environ.get("VILLA_ROOT", _REPO / "villa")) / (
    "vesuvius/src/vesuvius/neural_tracing/tracers"
)


def _villa(rel: str) -> str:
    if not TRACERS.exists() and "VILLA_ROOT" not in os.environ:
        pytest.skip("Villa tracer sources absent; set VILLA_ROOT to check them")
    return (TRACERS / rel).read_text()


@dataclasses.dataclass
class _Params:
    """Stands in for villa's TraceParams: a dataclass with the field, off by default."""

    n_commit: int = 8
    confidence: float = 0.5
    forward_chunk: int = 128
    refit_retry: bool = False


def test_the_launcher_needs_one_arm():
    assert arm.split_argv(["--arm", "refit", "--out", "o", "--box", "1"]) == (
        "refit",
        ["--out", "o", "--box", "1"],
    )
    assert arm.split_argv(["--arm=villa", "--out", "o"]) == ("villa", ["--out", "o"])
    for bad in (
        ["--out", "o"],
        ["--arm", "retry"],
        ["--arm", "refit", "--arm=villa"],
        ["--ar", "refit"],
    ):
        with pytest.raises(SystemExit):
            arm.split_argv(bad)


def test_a_resume_needs_the_same_arm(tmp_path):
    out = tmp_path / "run"
    rec = arm.record_arm(out, "refit")
    assert rec["arm"] == "refit" and rec["refit_retry"] is True
    assert arm.record_arm(out, "refit")["arm"] == "refit"
    with pytest.raises(SystemExit, match="another arm"):
        arm.record_arm(out, "villa")
    other = tmp_path / "plain"
    other.mkdir()
    (other / "run.json").write_text("{}")
    with pytest.raises(SystemExit, match="without this launcher"):
        arm.record_arm(other, "villa")


@pytest.mark.parametrize("name, want", [("villa", False), ("refit", True)])
def test_the_arm_sets_only_the_retry(name, want):
    tracer = types.SimpleNamespace(p=_Params(forward_chunk=64))
    built = (tracer, "vol", "spec", "policy")
    seen: dict = {}
    wrapped = arm.wrapped_build_tracer(name, lambda args: built, seen)
    t, *rest = wrapped("args")
    assert t is tracer and rest == ["vol", "spec", "policy"]
    assert t.p == _Params(forward_chunk=64, refit_retry=want)
    assert seen == {"refit_retry": want}


def test_main_runs_villas_main_wrapped_and_records_the_setting_in_effect(
    tmp_path, monkeypatch
):
    """main() wraps villa's build_tracer for the run, then puts it back; the record holds what the tracer held."""
    seen = {}
    tracer = types.SimpleNamespace(p=_Params())

    def original(args):
        return tracer, "vol", "spec", "policy"

    def villa_main(rest):
        seen["rest"] = rest
        seen["built"] = fake.build_tracer(types.SimpleNamespace())[0].p.refit_retry
        return 0

    fake = types.SimpleNamespace(main=villa_main, build_tracer=original)
    pkg = "vesuvius.neural_tracing.tracers.fibers.tracing"
    for i, _ in enumerate(pkg.split(".")):
        name = ".".join(pkg.split(".")[: i + 1])
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules[pkg].volume = fake
    monkeypatch.setitem(sys.modules, pkg + ".volume", fake)
    out = tmp_path / "run"
    assert arm.main(["--arm", "refit", "--out", str(out), "--box", "0,0,0,1,1,1"]) == 0
    assert seen == {"rest": ["--out", str(out), "--box", "0,0,0,1,1,1"], "built": True}
    assert fake.build_tracer is original
    rec = json.loads((out / "refit_arm.json").read_text())
    assert rec == {
        "arm": "refit",
        "refit_retry": True,
        "launcher": "scripts/neural_tracer_refit_arm.py",
        "in_effect": True,
    }


def test_villa_is_as_the_registration_says():
    """The reachability the registration rests on, in villa's source at the pin."""
    trace = _villa("fibers/tracing/trace.py")
    assert "refit_retry: bool = False" in trace
    # the retry acts at a would-be confidence stop, once per stop: reset after every advance
    assert (
        "if would_stop and pp.refit_retry and not retried[i] and not recovery_blocked:"
        in trace
    )
    assert "refit = predicted_axis(pos[j]+points[j] @ fr[j].T, pos[j], self.refit_window)" in trace  # fmt: skip
    assert "retried[i], predicted[i] = True, True" in trace
    assert trace.count("retried[i] = False") == 1
    # the tracer holds its rollout parameters as `p` and reads them at each trace() call
    assert (
        "self.n_history, self.p, self.device = n_history, params or TraceParams(), str(device)"
        in trace
    )
    assert "pp = self.p" in trace
    # the two sentences the registration quotes from trace.py's comments
    comments = " ".join(
        s.strip()[1:].strip() for s in trace.splitlines() if s.strip().startswith("#")
    )
    assert (
        "a decision that would stop on confidence first retries once at the same head with its crop refit to its "
        "own prediction (frames.learned.predicted_axis over the gate horizon); only a second stop then ends the "
        "trace" in comments
    )  # fmt: skip
    assert "fp32 keeps batch-composition rounding differences from growing into flipped decisions" in comments  # fmt: skip
    volume = _villa("fibers/tracing/volume.py")
    # the volume tracer never sets it, and its main builds the tracer by the module-global name
    assert "refit" not in volume
    assert "tracer, vol, spec, policy = build_tracer(args)" in volume
    assert "params = TraceParams.from_policy(policy, max_len=args.max_len" in volume
    assert "tracer.trace(" in volume
    # villa calls a forward-chunk change speed-only: the floor arm's perturbation
    assert "ap.add_argument('--forward-chunk', type=int, default=128)" in volume
    assert re.search(r"speed_only = \([^)]*'forward_chunk'", volume)
    # the single-seed CLI is where villa exposes it
    assert '"--refit-retry"' in _villa("fibers/tracing/inference.py")


def _local_imports(script: str, seen: set[str]) -> set[str]:
    for node in ast.walk(ast.parse((_REPO / "scripts" / f"{script}.py").read_text())):
        for name in (
            [a.name for a in node.names] if isinstance(node, ast.Import) else []
        ):
            if (_REPO / "scripts" / f"{name}.py").exists() and name not in seen:
                seen.add(name)
                _local_imports(name, seen)
    return seen


# The scorer and the chain. Imported here: the launcher's tests above need nothing but the launcher.
import neural_tracer_ct_context as cc  # noqa: E402
import neural_tracer_ct_context_512 as c5  # noqa: E402
import neural_tracer_refit_retry as rr  # noqa: E402
import neural_tracer_steep_heading as sh  # noqa: E402

CHAIN = _REPO / "repro/fibers/run_neural_tracer_refit_retry_chain.sh"
F97_CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_chain.sh"
F98_CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_512_chain.sh"
REG = _REPO / "docs/preregistration/2026-11-02_neural_tracer_refit_retry.md"
PEN, COV, PREC, MERGES = rr.PEN, rr.COV, rr.PREC, rr.MERGES


def _row(pen=10.0, cov=0.5, prec=0.5, merges=3):
    return {PEN: pen, COV: cov, PREC: prec, MERGES: merges}


def _case(gain=0.2, floor=0.0, prec=0.0, merges=0, floor_merges=0, inside=0.0):
    """Every held-out cube's ERLpen moved by `gain` (refit) and `floor`; precision by `prec`; merges by `merges`."""
    base = {c: _row() for c in rr.ALL_CUBES}
    rows = {
        "refit": {
            c: _row(10 * (1 + (gain if c in rr.HELD else inside)), prec=0.5 + prec,
                    merges=3 + (merges if c == rr.HELD[0] else 0))
            for c in rr.ALL_CUBES
        },
        "floor": {
            c: _row(10 * (1 + floor), merges=3 + (floor_merges if c == rr.HELD[0] else 0))
            for c in rr.HELD
        },
    }  # fmt: skip
    records = {a: {c: {"in_effect": rr.IN_EFFECT[a]} for c in rr.ARM_CUBES[a]} for a in rr.ARMS}  # fmt: skip
    records["smoke"] = {rr.SMOKE: {"in_effect": False}}
    return rows, base, records


def test_the_cubes_and_arms_are_findings_100s():
    assert (rr.HELD, rr.IN_SAMPLE, rr.ALL_CUBES, rr.SMOKE) == (sh.HELD, sh.IN_SAMPLE, sh.ALL_CUBES, sh.SMOKE)  # fmt: skip
    assert len(rr.HELD) == 10 and len(rr.IN_SAMPLE) == 11 and rr.SMOKE in rr.HELD
    assert rr.ARMS == ("refit", "floor")
    assert rr.ARM_CUBES == {"refit": rr.ALL_CUBES, "floor": rr.HELD}
    assert rr.IN_EFFECT == {"refit": True, "floor": False}
    assert rr.BASE_RUNS == sh.BASE_RUNS


def test_the_decision_rule():
    v = rr.verdict(*_case())
    assert (v["prediction_P1"], v["prediction_P2"], v["prediction_P3"]) == (
        True,
        True,
        True,
    )
    assert rr.status(True, v, []) == "OK"
    assert v["reading"].startswith(
        "villa's refit retry raises held-out ERLpen by a median 0.200"
    )
    assert "propose a registered test on cubes outside these 21" in v["reading"]
    assert rr.verdict(*_case(gain=0.0999))["prediction_P1"] is False
    assert rr.verdict(*_case(gain=0.10))["prediction_P1"]
    v = rr.verdict(*_case(merges=1))
    assert not v["prediction_P2"] and v["prediction_P1"]
    assert "with more merges" in v["reading"] and "stops a candidate" in v["reading"]
    v = rr.verdict(*_case(prec=-0.031))
    assert not v["prediction_P3"] and "at a cost in precision" in v["reading"]
    assert rr.verdict(*_case(prec=-0.0299))["prediction_P3"]
    v = rr.verdict(*_case(gain=0.05))
    assert not v["prediction_P1"] and "under the 0.10 bar" in v["reading"]
    assert "close it as a continuation rule" in v["reading"]
    v = rr.verdict(*_case(gain=0.05, merges=2, prec=-0.05))
    assert v["reading"].endswith("; it also adds merges and costs precision")


def test_p2_allows_only_the_floors_change_in_merges():
    # the floor arm moved the held-out merges by 2: the refit arm may move them by as much, not more
    assert rr.verdict(*_case(merges=2, floor_merges=-2))["prediction_P2"]
    assert not rr.verdict(*_case(merges=3, floor_merges=2))["prediction_P2"]
    assert rr.verdict(*_case(merges=-4))["prediction_P2"]


def test_p3_counts_eight_of_the_ten():
    rows, base, records = _case()
    for c in rr.HELD[:2]:
        rows["refit"][c][PREC] = 0.5 - 0.04
    assert rr.verdict(rows, base, records)["prediction_P3"]
    rows["refit"][rr.HELD[2]][PREC] = 0.5 - 0.04
    assert not rr.verdict(rows, base, records)["prediction_P3"]


def test_the_failure_branches_emit_no_reading():
    v = rr.verdict(*_case(floor=0.03))
    assert v["floor_ok"] is False and v["reading"] is None
    assert rr.status(True, v, []) == "FLOOR_TOO_LARGE"
    assert rr.verdict(*_case(floor=-0.0299))["floor_ok"]
    rows, base, records = _case()
    records["refit"][rr.IN_SAMPLE[0]]["in_effect"] = False
    v = rr.verdict(rows, base, records)
    assert v["manipulation_ok"] is False and v["reading"] is None
    assert rr.status(True, v, []) == "MANIPULATION_FAILED"
    rows, base, records = _case()
    records["floor"][rr.HELD[0]]["in_effect"] = (
        None  # a floor run not through the launcher
    )
    assert rr.status(True, rr.verdict(rows, base, records), []) == "MANIPULATION_FAILED"
    assert rr.status(False, rr.verdict(*_case()), []) == "SMOKE_FAILED"
    assert (
        rr.status(None, rr.verdict(*_case()), []) == "INCOMPLETE"
    )  # no smoke on record


def test_failed_and_incomplete_studies_emit_no_reading():
    """verdict() reads the runs whatever the smoke says; the scored outcome keeps a reading only when it is OK."""
    for smoke, failed, want in ((False, [], "SMOKE_FAILED"), (None, [], "INCOMPLETE"),
                                (True, [f"floor/{rr.HELD[0]}"], "INCOMPLETE")):  # fmt: skip
        v = rr.verdict(*_case())
        assert v["reading"] is not None
        assert rr.outcome(smoke, v, failed) == want and v["reading"] is None
    v = rr.verdict(*_case())
    assert rr.outcome(True, v, []) == "OK" and v["reading"].startswith("villa's refit")


def test_a_baseline_that_does_not_rescore_to_its_rows_voids_the_comparison():
    """Registered 2026-11-03: findings 97 and 98's rows name no ScrollGT commit, so score re-scores their runs."""
    v = rr.verdict(*_case())
    assert rr.outcome(True, v, [], baseline_ok=False) == "BASELINE_DRIFT"
    assert v["reading"] is None
    assert rr.status(False, rr.verdict(*_case()), [], False) == "SMOKE_FAILED"
    v = rr.verdict(*_case())
    assert rr.outcome(True, v, [], baseline_ok=True) == "OK" and v["reading"]


def test_a_rescored_row_must_give_every_recorded_field_exactly():
    recorded = {"coverage": 0.3333, "erl_merge_penalized": 11.41, "merges": 3}
    assert rr.rows_match(recorded, {**recorded, "extra": 1.0})
    assert not rr.rows_match(recorded, {**recorded, "coverage": 0.3334})
    assert not rr.rows_match(recorded, {"coverage": 0.3333, "merges": 3})
    assert rr.rows_match({"t": [1, 2]}, {"t": (1, 2)})  # as JSON records it


def test_score_never_replaces_a_result(tmp_path, monkeypatch):
    def reached(*a):
        raise AssertionError("score went on past an existing result")

    monkeypatch.setattr(rr.sh, "baseline", reached)
    out = tmp_path / "result.json"
    out.write_text("{}")
    with pytest.raises(SystemExit, match="never replaces"):
        rr.cmd_score(tmp_path, out)
    assert out.read_text() == "{}"


@pytest.mark.parametrize(
    "coverage_now, want", [(0.5, "INCOMPLETE"), (0.4, "BASELINE_DRIFT")]
)
def test_score_rescores_the_baseline_and_voids_on_a_difference(tmp_path, monkeypatch, coverage_now, want):  # fmt: skip
    """No arm run is on record, so a baseline that reproduces leaves the study INCOMPLETE; one that does not is
    BASELINE_DRIFT, whatever else is missing."""
    row = {"coverage": 0.5, "precision": 0.5, "erl_merge_penalized": 10.0, "merges": 3}
    scored = types.SimpleNamespace(as_row=lambda: dict(row, coverage=coverage_now))
    monkeypatch.setitem(sys.modules, "scrollgt.fibers.eval_trace",
                        types.SimpleNamespace(SCORING_VERSION=3, score_tracing=lambda s, lab, tolerance: scored))  # fmt: skip
    monkeypatch.setitem(sys.modules, "scrollgt.fibers.target",
                        types.SimpleNamespace(load_fiber_target=lambda p: (None, None, None)))  # fmt: skip
    rows = {c: row for c in rr.ALL_CUBES}
    monkeypatch.setattr(rr.sh, "baseline", lambda: (rows, rows, {}))
    monkeypatch.setattr(rr.cc, "labels_in_cube", lambda *a: None)
    monkeypatch.setattr(rr, "ceiling_gains", lambda: {c: 0.3 for c in rr.ALL_CUBES})
    monkeypatch.setattr(rr, "run_record", lambda run: {})
    out = tmp_path / "result.json"
    assert rr.cmd_score(tmp_path, out) == 1
    got = json.loads(out.read_text())
    assert got["status"] == want
    assert all(got["baseline_reproduced"].values()) is (want == "INCOMPLETE")
    assert set(got["baseline_reproduced"]) == set(rr.ALL_CUBES)


def test_a_baseline_that_drifts_only_at_tolerance_4_voids_the_comparison(tmp_path, monkeypatch):  # fmt: skip
    """The registration requires every baseline row to reproduce at both tolerances. Dropping the tolerance-4
    comparison passed every other test."""
    row2 = {"coverage": 0.5, "precision": 0.5, "erl_merge_penalized": 10.0, "merges": 3}
    row4 = dict(row2, coverage=0.6)

    def score_tracing(skel, lab, tolerance):
        now = row2 if tolerance == 2.0 else dict(row4, coverage=0.61)
        return types.SimpleNamespace(as_row=lambda now=now: dict(now))

    monkeypatch.setitem(sys.modules, "scrollgt.fibers.eval_trace",
                        types.SimpleNamespace(SCORING_VERSION=3, score_tracing=score_tracing))  # fmt: skip
    monkeypatch.setitem(sys.modules, "scrollgt.fibers.target",
                        types.SimpleNamespace(load_fiber_target=lambda p: (None, None, None)))  # fmt: skip
    base2, base4 = ({c: dict(r) for c in rr.ALL_CUBES} for r in (row2, row4))
    monkeypatch.setattr(rr.sh, "baseline", lambda: (base2, base4, {}))
    monkeypatch.setattr(rr.cc, "labels_in_cube", lambda *a: None)
    monkeypatch.setattr(rr, "ceiling_gains", lambda: {c: 0.3 for c in rr.ALL_CUBES})
    monkeypatch.setattr(rr, "run_record", lambda run: {})
    out = tmp_path / "result.json"
    assert rr.cmd_score(tmp_path, out) == 1
    got = json.loads(out.read_text())
    assert got["status"] == "BASELINE_DRIFT"
    assert not any(got["baseline_reproduced"].values())


def test_the_smoke_must_record_the_retry_off():
    """The manipulation check covers the smoke: it runs through the launcher's villa arm."""
    for in_effect, want in ((False, "OK"), (True, "MANIPULATION_FAILED"), (None, "MANIPULATION_FAILED")):  # fmt: skip
        rows, base, records = _case()
        records["smoke"] = {rr.SMOKE: {"in_effect": in_effect}}
        v = rr.verdict(rows, base, records)
        assert v["manipulation"]["smoke"] == {rr.SMOKE: in_effect is False}
        assert rr.outcome(True, v, []) == want
        assert (v["reading"] is None) == (want != "OK")
    rows, base, records = _case()
    del records["smoke"]  # a score that never read the smoke's record
    v = rr.verdict(rows, base, records)
    assert rr.outcome(True, v, []) == "MANIPULATION_FAILED"


@pytest.mark.parametrize("in_effect, rc", [(False, 0), (True, 1), (None, 1)])
def test_the_smoke_command_records_the_launchers_setting(tmp_path, monkeypatch, in_effect, rc):  # fmt: skip
    run = tmp_path / "smoke" / rr.SMOKE
    run.mkdir(parents=True)
    if in_effect is not None:
        (run / "refit_arm.json").write_text(json.dumps({"arm": "villa", "in_effect": in_effect}))  # fmt: skip
    monkeypatch.setattr(rr.cc, "f96_afv_identical", lambda a, b: True)
    assert rr.main(["smoke", "--work", str(tmp_path)]) == rc
    assert json.loads((tmp_path / "smoke.json").read_text())["in_effect"] == in_effect
    assert rr.smoke_record(tmp_path) == (True, {"in_effect": in_effect})
    assert rr.smoke_record(tmp_path / "none") == (None, {})


def test_thresholds_hold_at_rounded_rows_exactly_on_them():
    """ScrollGT rounds the rows; a figure exactly at a threshold must not fall on the wrong side by float error."""
    rows, base, records = _case()
    for c in rr.HELD:  # a gain of 0.10: 5.72 / 5.2 - 1 = 0.09999999999999987
        base[c][PEN], rows["refit"][c][PEN] = 5.2, 5.72
    assert rr.verdict(rows, base, records)["prediction_P1"]
    rows, base, records = _case()
    for c in rr.HELD[:3]:  # 0.03 lower: 0.50 - 0.53 = -0.030000000000000027
        base[c][PREC], rows["refit"][c][PREC] = 0.53, 0.50
    assert rr.verdict(rows, base, records)["prediction_P3"]
    rows, base, records = _case()
    for c in rr.HELD:  # the floor moved by 0.03: 5.82 / 6.0 - 1 = -0.029999999999999916
        base[c][PEN], rows["floor"][c][PEN] = 6.0, 5.82
    v = rr.verdict(rows, base, records)
    assert v["floor_ok"] is False and rr.status(True, v, []) == "FLOOR_TOO_LARGE"


def test_the_floor_is_the_median_absolute_change():
    v = rr.verdict(*_case(floor=-0.05))
    assert v["floor_median_abs"] == pytest.approx(0.05)
    assert v["floor_ok"] is False and rr.status(True, v, []) == "FLOOR_TOO_LARGE"


def test_partial_samples_are_refused():
    for arm_, cube in (("refit", rr.IN_SAMPLE[-1]), ("floor", rr.HELD[-1])):
        rows, base, records = _case()
        del rows[arm_][cube]
        v = rr.verdict(rows, base, records)
        assert v["prediction_P1"] is None and v["reading"] is None
        assert rr.status(True, v, [f"{arm_}/{cube}"]) == "INCOMPLETE"


def test_the_descriptive_figures():
    rows, base, records = _case(gain=0.2, inside=0.05)
    ceiling = {c: 0.4 for c in rr.ALL_CUBES}
    v = rr.verdict(rows, base, records, ceiling)
    assert v["median_gain_in_sample"] == pytest.approx(0.05)
    assert v["share_of_ceiling"] == {c: pytest.approx(0.5) for c in rr.HELD}
    assert v["merges_held"] == {"base": 30, "refit": 30, "floor": 30}
    assert v["coverage_factor"][rr.HELD[0]] == 1.0


def test_run_record_reads_the_last_line_of_each_tile_and_the_arm(tmp_path):
    lines = [
        {"tile": "a", "dots": 9, "stop_confidence": 5, "seconds": 1.0},
        {"tile": "a", "dots": 10, "traced": 7, "stop_confidence": 4, "stop_bounds": 2, "seconds": 3.0},
        {"tile": "b", "dots": 1, "stop_owned_or_live": 1, "seconds": 0.5},
    ]  # fmt: skip
    (tmp_path / "tiles.jsonl").write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n"
    )
    r = rr.run_record(tmp_path)
    assert (r["dots"], r["traced"], r["stop_confidence"], r["stop_bounds"], r["stop_owned_or_live"]) == (11, 7, 4, 2, 1)  # fmt: skip
    assert r["tiles"] == 2 and r["seconds"] == 3.5 and "in_effect" not in r
    (tmp_path / "refit_arm.json").write_text(
        json.dumps({"arm": "refit", "in_effect": True})
    )
    r = rr.run_record(tmp_path)
    assert (r["arm"], r["in_effect"]) == ("refit", True)


def test_the_thresholds_are_the_registrations():
    text = " ".join(REG.read_text().split())
    assert (
        rr.GAIN_BAR == 0.10 and "median held-out ERLpen gain of at least 0.10" in text
    )
    assert rr.FLOOR_MAX == 0.03 and "below 0.03" in text
    assert (rr.P3_DROP, rr.P3_AT_LEAST) == (0.03, 8)
    assert (
        "at most 0.03 below the baseline's, or above it, on at least 8 of the 10"
        in text
    )
    assert (
        rr.FLOOR_CHUNK == 64
        and "--forward-chunk 64" in text
        and "--forward-chunk 64" in CHAIN.read_text()
    )
    for status in (
        "SMOKE_FAILED",
        "MANIPULATION_FAILED",
        "INCOMPLETE",
        "FLOOR_TOO_LARGE",
    ):
        assert status in text, status


def _flags(text: str, after: str) -> set[str]:
    cmd = text.split(after, 1)[1].split(">", 1)[0]
    return set(re.findall(r"--[a-z-]+", cmd))


def test_the_trace_is_findings_97_and_98s_command():
    ours = CHAIN.read_text()
    for theirs in (F97_CHAIN.read_text(), F98_CHAIN.read_text()):
        ckpt = re.compile(r'^CKPT="([^"]+)"$', re.M)
        assert ckpt.search(ours).group(1) == ckpt.search(theirs).group(1)
        assert _flags(ours, '"$W/neural_tracer_refit_arm.py"') - {"--arm"} == _flags(
            theirs, "tracers.fibers.tracing.volume"
        )
    assert "base=$T/ct_context_run" in ours and "base=$T/ct_context_512_run" in ours
    assert "box=64,64,64,192,192,192" in ours and "box=64,64,64,320,320,320" in ours
    assert '--out "$2" "${@:4}"' in ours


def _cubes(text: str, name: str) -> list[str]:
    return re.search(rf'^{name}="(.*?)"', text, re.S | re.M).group(1).split()


def test_the_smoke_gates_the_arms_and_held_out_runs_first():
    text = CHAIN.read_text()
    assert _cubes(text, "HELD") == rr.HELD and _cubes(text, "IN_SAMPLE") == rr.IN_SAMPLE
    assert (
        f"SMOKE={rr.SMOKE}" in text and 'trace villa "$W/smoke/$SMOKE" "$SMOKE"' in text
    )
    assert (
        text.index("trace villa")
        < text.index('refit_retry.py" smoke')
        < text.index("run_arm refit HELD")
    )
    assert "exit 4" in text.split('say "SMOKE_OK"')[0]
    # refit on the held-out cubes, then the floor on them, then refit in sample
    order = [
        text.index(s)
        for s in ("run_arm refit HELD", "run_arm floor HELD", "run_arm refit IN_SAMPLE")
    ]
    assert order == sorted(order)
    assert 'floor) trace villa "$out" "$C" --forward-chunk 64' in text
    assert 'W="${W:-$T/refit_retry_run}"' in text
    assert (
        "tracers\\.fibers\\.tracing\\.volume|neural_tracer_heading_arm|neural_tracer_refit_arm|"
        in text
    )


def test_the_chain_freezes_every_script_it_runs():
    frozen = (
        re.search(r"for f in (.*?); do", CHAIN.read_text(), re.S)
        .group(1)
        .replace("\\\n", " ")
        .split()
    )
    want = _local_imports(
        "neural_tracer_refit_retry",
        {"neural_tracer_refit_retry", "neural_tracer_refit_arm"},
    )
    assert set(frozen) == {f"{s}.py" for s in want}
    text = CHAIN.read_text()
    assert text.index('export PYTHONPATH="$REPO/src') < text.index(
        '"$PY" "$LOOPDIR/scripts/loop_control.py"'
    )


def test_the_baseline_and_the_ceiling_exist():
    base2, _, rec = sh.baseline()
    assert set(base2) == set(rec) == set(rr.ALL_CUBES)
    assert all(base2[c][PEN] > 0 for c in rr.ALL_CUBES)
    ceiling = rr.ceiling_gains()
    assert set(ceiling) == set(rr.ALL_CUBES)
    f102 = json.loads(rr.CEILING.read_text())["verdict"]
    assert statistics.median(ceiling[c] for c in rr.HELD) == pytest.approx(
        f102["median_U"]
    )
    assert cc.TOLS == (2.0, 4.0) and rr.HELD[2:] == c5.S3_CUBES


def test_the_bars_are_inclusive_as_registered(monkeypatch):
    """ "At least 0.10" and "not below 0.03": exact values, which no ratio of floats produces, by a patched gain."""

    def exact(refit, floor):
        return lambda rows, base, cubes, key=PEN: {
            c: refit if cubes == rr.ALL_CUBES else floor for c in cubes
        }

    monkeypatch.setattr(rr, "gains", exact(0.10, 0.0))
    assert rr.verdict(*_case())["prediction_P1"] is True
    monkeypatch.setattr(rr, "gains", exact(0.2, 0.03))
    v = rr.verdict(*_case())
    assert v["floor_ok"] is False and rr.status(True, v, []) == "FLOOR_TOO_LARGE"


def test_p1_is_the_median_not_the_mean():
    rows, base, records = _case()
    for i, c in enumerate(rr.HELD):
        rows["refit"][c][PEN] = 10 * (1.5 if i < 4 else 1.0)  # mean gain 0.2, median 0
    v = rr.verdict(rows, base, records)
    assert v["median_gain_held"] == 0 and v["prediction_P1"] is False


UNSHIPPED = _REPO / "reports/evidence/fiber_skeletons_unshipped_2026-11-02.json"


def test_the_confirmation_cubes_are_the_recorded_ten():
    """The registration's confirmation set: Dataset004's cubes ScrollGT does not ship, as the evidence records them."""
    ev = json.loads(UNSHIPPED.read_text())
    un, txt = ev["unshipped"], REG.read_text()
    flat = " ".join(txt.split())
    assert ev["releases"]["Dataset004_sk-fibers-binary-20250728"]["nml_files"] == 31
    assert ev["scrollgt"]["fiber_cubes"] == 21 and len(un) == 10
    assert not set(un) & set(rr.ALL_CUBES)
    for c, r in un.items():
        assert (
            f"| {c} | {r['first_release'][:10]} | {r['fibers_scored']} | {r['nodes_in_bounds']:,} |"
            in txt
        )
    n2 = sum(r["first_release"].startswith("Dataset002") for r in un.values())
    assert (n2, len(un) - n2) == (7, 3)
    assert "holds 31 hand-traced cubes; ScrollGT ships 21" in flat
    assert "The presence model trained on seven of them" in flat
    assert (
        "The other three first appear in Dataset003 (14 + 7), which does not match it"
        in flat
    )
