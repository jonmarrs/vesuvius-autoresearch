"""Guards on the unattended analysis runner.

Running the registered analysis with nobody in the loop does not weaken the
pre-registration; it strengthens it. The decision rule, the validity gate and the
retirement of the A-vs-B comparison all live in committed code, so no human sits
between seeing a number and deciding what it means. These tests keep that true.
"""

from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "repro"
    / "spiral_render"
    / "run_consensus_analysis_when_ready.sh"
)


def _code(src: str) -> str:
    return "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))


def test_script_exists_and_is_executable():
    assert SCRIPT.exists() and SCRIPT.stat().st_mode & 0o111


def test_waits_on_the_artifacts_it_will_consume():
    """Not on a process, and not on a completion message: fit_spiral.py once wrote
    its 'done' json a minute before its meshes and a driver woke early on it."""
    code = _code(SCRIPT.read_text())
    assert "ink_metric/metrics.json" in code
    assert "pgrep" not in code and "pkill" not in code


def test_refuses_rather_than_reporting_a_partial_sample():
    src = SCRIPT.read_text()
    assert "Analysis NOT run" in src
    assert "partial" in src


def test_runs_the_registered_control_before_the_analysis():
    code = _code(SCRIPT.read_text())
    assert "check_strip_nonblank.py" in code
    assert code.index("check_strip_nonblank.py") < code.index(
        "analyse_consensus_retest.py"
    )


def test_waits_for_the_box_to_be_clear():
    """Loading nine arms beside a render drove MemAvailable to 0G once already."""
    assert "--fail-if-any" in _code(SCRIPT.read_text())


def test_writes_the_verdict_to_a_json_artifact():
    assert "consensus_retest_verdict.json" in SCRIPT.read_text()
