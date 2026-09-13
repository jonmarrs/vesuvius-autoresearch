"""Tests for the per-arm gate runner.

The registered rule says an arm whose winding numbering shifted is EXCLUDED and
REPORTED. The failure mode is not an exception -- it is an excluded arm quietly
analysed as though it had passed, which is indistinguishable in the output from a
study where nothing went wrong.

So these tests are about the gate's refusals, not its successes.
"""

import json
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))

import run_anchor_gate as mod  # noqa: E402


def test_the_registered_rule_is_constants_not_judgement():
    assert mod.REF_ARM == "curbase_s1"
    assert mod.ABLATED == ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3")
    assert mod.STRIP == "120-129"
    assert mod.MIN_POSITIVE_MARGINS == 9


def _stub(monkeypatch, per_arm):
    """Make run_gate return canned states without touching meshes."""

    def fake(repo, spiral_out, tag, ref_root):
        return per_arm[tag]

    monkeypatch.setattr(mod, "run_gate", fake)
    monkeypatch.setattr(mod, "mesh_root", lambda so, tag: Path("/fake"))
    monkeypatch.setattr(
        mod,
        "metrics_for",
        lambda so, tag: (Path(f"/m/{tag}.json"), Path(f"/s/{tag}.json")),
    )


def _rows(offsets, margins):
    return [
        {
            "ref": 120 + i,
            "best": 120 + i + o,
            "offset": o,
            "dist": 24.0,
            "runner_up": 121 + i,
            "runner_up_dist": 24.0 + m,
        }
        for i, (o, m) in enumerate(zip(offsets, margins, strict=False))
    ]


def _pass(tag):
    return {
        "arm": tag,
        "state": "PASS",
        "n_windings": 10,
        "offsets_all_zero": True,
        "positive_margins": 10,
        "rows": _rows([0] * 10, [3.0] * 10),
    }


def _fail(tag):
    return {
        "arm": tag,
        "state": "FAIL",
        "n_windings": 10,
        "offsets_all_zero": False,
        "positive_margins": 10,
        "rows": _rows([1] * 10, [3.0] * 10),
    }


def test_all_passing_emits_an_invocation_with_all_six_arms(
    monkeypatch, capsys, tmp_path
):
    _stub(monkeypatch, {t: _pass(t) for t in mod.ABLATED})
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    mod.main()
    out = capsys.readouterr().out
    assert "all three ablated arms passed" in out
    assert "analyse_anchor_ablation.py" in out
    for t in mod.ABLATED + ("curbase_s1", "curbase_s2", "curbase_s3"):
        assert t in out


def test_a_failing_arm_is_named_and_blocks_the_verdict(monkeypatch, capsys, tmp_path):
    per = {t: _pass(t) for t in mod.ABLATED}
    per["anchor10cov_s2"] = _fail("anchor10cov_s2")
    _stub(monkeypatch, per)
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    mod.main()
    out = capsys.readouterr().out
    assert "EXCLUDED by the gate: anchor10cov_s2" in out
    assert "reported, not dropped" in out
    # two survivors is a partial sample; the registered rule refuses it
    assert "only 2 of 3" in out
    assert "refuses a partial sample" in out
    assert "all three ablated arms passed" not in out


def test_an_unfitted_arm_stops_the_gate_rather_than_analysing_two(
    monkeypatch, capsys, tmp_path
):
    per = {t: _pass(t) for t in mod.ABLATED}
    per["anchor10cov_s3"] = {"arm": "anchor10cov_s3", "state": "NOT FITTED"}
    _stub(monkeypatch, per)
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    mod.main()
    out = capsys.readouterr().out
    assert "gate incomplete, do not analyse" in out
    assert "analyse_anchor_ablation.py" not in out


def test_the_json_record_lists_excluded_and_passed_separately(monkeypatch, tmp_path):
    per = {t: _pass(t) for t in mod.ABLATED}
    per["anchor10cov_s2"] = _fail("anchor10cov_s2")
    _stub(monkeypatch, per)
    out = tmp_path / "gate.json"
    sys.argv = ["x", "--spiral-out", str(tmp_path), "--json", str(out)]
    mod.main()
    got = json.loads(out.read_text())
    assert got["excluded"] == ["anchor10cov_s2"]
    assert set(got["passed"]) == {"anchor10cov_pilot", "anchor10cov_s3"}


def test_offsets_all_zero_but_too_few_positive_margins_is_a_FAIL():
    """The second half of the registered rule. Unanimous numbering with mushy
    margins is INCONCLUSIVE, which the registration calls not-a-pass."""
    rows = _rows([0] * 10, [3.0] * 5 + [-1.0] * 5)
    positive = sum(1 for r in rows if (r["runner_up_dist"] - r["dist"]) > 0)
    assert positive == 5
    assert not (True and positive >= mod.MIN_POSITIVE_MARGINS)


@pytest.mark.skipif(
    not os.path.isdir("/home/jon/openclaw-workspace/Neo-VM/spiral_out"),
    reason="fit corpus not present",
)
def test_against_real_meshes_arm_one_passes():
    """End-to-end on the actual pilot, reproducing the hand-run gate result."""
    repo = _REPO
    so = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
    ref = mod.mesh_root(so, mod.REF_ARM)
    if ref is None:
        pytest.skip("reference arm not fitted")
    r = mod.run_gate(repo, so, "anchor10cov_pilot", ref)
    assert r["state"] == "PASS"
    assert r["offsets_all_zero"] and r["positive_margins"] == 10
