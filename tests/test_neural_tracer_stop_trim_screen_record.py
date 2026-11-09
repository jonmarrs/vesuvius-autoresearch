"""reports/neural_tracer_stop_trim_screen.md, bound to its record (reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json)
and to the script that wrote it, and the pointers to it from finding 101 and the off-reference analysis."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "neural_tracer_stop_trim_screen", ROOT / "scripts/neural_tracer_stop_trim_screen.py"
)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

PATH = ROOT / "reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json"
E = json.loads(PATH.read_text())
RAW = (ROOT / "reports/neural_tracer_stop_trim_screen.md").read_text()
REPORT = " ".join(RAW.split())


def _text(path: str) -> str:
    return " ".join((ROOT / path).read_text().split())


def test_the_script_rewrites_the_record_from_its_per_cube_results(
    monkeypatch, tmp_path
):
    """All but the per-cube scoring, which needs the runs and ScrollGT: finding 104's baseline check, the summary
    and the settings."""
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(ts, "screen_cube", lambda cube: E["per_cube"][cube])
    out = tmp_path / PATH.name
    assert ts.main(["--out", str(out)]) == 0
    assert out.read_text() == PATH.read_text()


def test_k_0_is_finding_104_s_recorded_baseline_on_every_cube():
    recorded = json.loads((ROOT / "reports/neural_tracer_refit_retry.json").read_text())
    for t in ("2", "4"):
        for c in E["cubes"]:
            assert (
                E["per_cube"][c]["0"]["rows"][t] == recorded[f"baseline_rows_tol{t}"][c]
            )
    assert len(E["cubes"]) == 11 and "The eleven in-sample cubes." in REPORT
    assert (
        "reproduces finding 104's recorded baseline rows on all eleven, at both tolerances"
        in REPORT
    )


def test_the_report_s_settings_are_the_record_s():
    assert f"at least {E['edge_voxels']:g} voxels from a cube face" in REPORT
    assert f"`--min-length` ({E['min_points']} points)" in REPORT
    assert (
        f"its last point within {E['oracle_tolerance']:g} voxels of a hand-traced fiber"
        in REPORT
    )
    assert E["ks_voxels"] == [0.0, 10.0, 20.0, 40.0]  # the table's 10, 20 and 40 voxels


def test_the_lead_claims_follow_from_the_record():
    s, pc = E["summary"], E["per_cube"]
    for k in ("10", "20"):
        r = [pc[c][k]["rows"]["2"]["erl_merge_penalized"] / pc[c]["0"]["rows"]["2"]["erl_merge_penalized"] for c in pc]  # fmt: skip
        assert max(r) < 1
    assert "ERLpen fell on every cube at 10 and 20 voxels" in REPORT
    for k in ("10", "20", "40"):
        m = s[f"k{k}_tol2"]
        assert round(-m["coverage_change_median"] / m["precision_change_median"]) == 2
    assert "A fixed trim loses about twice the coverage it gains in precision" in REPORT
    oracle = s["koracle_tol2"]["precision_change_median"]
    assert f"Even the oracle buys a median {oracle:.3f} of precision" in REPORT
    assert oracle < 0.02 and "worth under 0.02 of median precision" in REPORT


def test_the_16_percent_and_finding_101_s_two_thirds_are_the_records():
    pc = E["per_cube"]
    off = [sum((1 - pc[c][k]["rows"]["2"]["precision"]) * pc[c][k]["rows"]["2"]["pred_length"] for c in pc) for k in ("0", "oracle")]  # fmt: skip
    pct = f"{100 * (1 - off[1] / off[0]):.0f}%"
    assert pct == "16%"
    assert f"even an oracle trim removes only {pct} of the off-reference length" in RAW.splitlines()[0]  # fmt: skip
    assert (
        "A fixed trim loses about twice the coverage it gains in precision, and even an oracle trim removes "
        f"only {pct} of the off-reference length."
    ) in _text("reports/neural_tracer_confidence_stops.md")
    assert f"stops removes only {pct} of its off-reference length" in _text(
        "reports/neural_tracer_offref_location.md"
    )
    d = json.loads((ROOT / "reports/neural_tracer_confidence_stops.json").read_text())
    stops, on = (
        sum(
            d["per_cube"][c]["tol2"]["settings"]["L20_edge6"]["confidence"][key]
            for c in ts.cs.HELD_OUT
        )
        for key in ("stops", "on_fiber")
    )
    assert round(3 * (1 - on / stops)) == 2
    assert "Finding 101 found that two-thirds of the tracer's interior confidence stops lie off" in REPORT  # fmt: skip
