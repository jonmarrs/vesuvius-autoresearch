"""reports/neural_tracer_offref_location.md, bound to its record (reports/evidence/neural_tracer_offref_location_2026-11-05.json)
and to the script that wrote it."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "neural_tracer_offref_location", ROOT / "scripts/neural_tracer_offref_location.py"
)
ol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ol)

PATH = ROOT / "reports/evidence/neural_tracer_offref_location_2026-11-05.json"
E = json.loads(PATH.read_text())
RAW = (ROOT / "reports/neural_tracer_offref_location.md").read_text()
REPORT = " ".join(RAW.split())


def test_the_script_rewrites_the_record_from_its_per_cube_results(
    monkeypatch, tmp_path
):
    """All but the per-cube measurement, which needs the runs, the CT and ScrollGT: the summary, the gate against
    the screen's ScrollGT rows, the CT peaks and the settings."""
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(ol, "measure_cube", lambda cube: E["per_cube"][cube])
    out = tmp_path / PATH.name
    assert ol.main(["--out", str(out)]) == 0
    assert out.read_text() == PATH.read_text()


def test_the_title_and_settings_follow_from_the_record():
    s2, s4 = (E["summary"][t] for t in ("tol2", "tol4"))
    sh = s2["shares"]
    departures = (
        sum(v for k, v in sh.items() if k.startswith("tail:")) + sh["gap_switch"]
    )
    assert round(3 * (sh["gap_same"] + sh["whole_off"])) == 2 and round(3 * departures) == 1  # fmt: skip
    assert (
        "two-thirds of that length lies beside the fiber the trace follows or on fibers no reference passes, "
        "and a third is departure-shaped"
    ) in RAW.splitlines()[0]
    assert f"(the gate allows {E['proxy_tolerance']:g})" in REPORT
    assert f"shifted by up to {max(E['shifts_voxels']):g} voxels" in REPORT
    assert sh["gap_same"] > 1 / 3 and "Over a third of the off-reference length lies within a few voxels" in REPORT  # fmt: skip
    # The on-reference set only grows from tolerance 2 to 4, so what a tolerance-2 interior run still has off at
    # tolerance 4 lies in tolerance-4 interior runs: at least this share of it is within 4 voxels.
    same, s4_runs = sh["gap_same"] * s2["off_length"], (s4["shares"]["gap_same"] + s4["shares"]["gap_switch"]) * s4["off_length"]  # fmt: skip
    assert 1 - s4_runs / same > 0.5 and "so most of it is within 4 voxels" in REPORT
