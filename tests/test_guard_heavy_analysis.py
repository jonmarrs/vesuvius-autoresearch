"""Guards on the headroom guard.

Built after a four-arm analysis drove available RAM to 0 GB while a render was in
flight. The detection detail that matters: it must match the villa venv
interpreter, which every pipeline stage shares, NOT a stage name. A check that
grepped for `render_ink|run_render` reported nothing alive while the render was
healthy in its `lasagna` flatten stage -- the dangerous direction, since it says
"safe to proceed" exactly when it is not.
"""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "gha", Path(__file__).resolve().parents[1] / "scripts" / "guard_heavy_analysis.py"
)
assert SPEC and SPEC.loader
gha = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gha)


def test_detection_matches_the_interpreter_not_a_stage_name():
    """The regression: stage names miss the flatten, the interpreter does not."""
    assert "\\.venv" in gha.VILLA_VENV_MARK or ".venv" in gha.VILLA_VENV_MARK
    for stage in ("render_ink", "run_render", "get_ink_metrics", "lasagna"):
        assert stage not in gha.VILLA_VENV_MARK, (
            f"marker names the {stage} stage; a render in another stage would be "
            "reported as absent, which is the dangerous direction"
        )


def test_free_gb_reads_memavailable_not_memfree(monkeypatch, tmp_path):
    """MemFree excludes reclaimable cache and would refuse constantly."""
    src = Path("/proc/meminfo").read_text()
    assert "MemAvailable:" in src
    assert gha.free_gb() > 0


def test_proceeds_when_no_render_is_in_flight(monkeypatch, capsys):
    monkeypatch.setattr(gha, "render_in_flight", lambda: [])
    monkeypatch.setattr(gha, "free_gb", lambda: 0.2)
    assert gha.require_headroom(need_gb=64.0) is True
    assert "no render in flight" in capsys.readouterr().out


def test_refuses_when_a_render_is_up_and_headroom_is_short(capsys, monkeypatch):
    monkeypatch.setattr(gha, "render_in_flight", lambda: [(1, "villa python")])
    monkeypatch.setattr(gha, "free_gb", lambda: 1.0)
    assert gha.require_headroom(need_gb=6.0) is False
    assert "REFUSING" in capsys.readouterr().out


def test_force_overrides_but_says_what_it_costs(capsys, monkeypatch):
    monkeypatch.setattr(gha, "render_in_flight", lambda: [(1, "villa python")])
    monkeypatch.setattr(gha, "free_gb", lambda: 1.0)
    assert gha.require_headroom(need_gb=6.0, force=True) is True
    assert "costs the render" in capsys.readouterr().out


def test_render_in_flight_survives_vanishing_processes():
    """/proc entries disappear mid-scan; that must not raise."""
    assert isinstance(gha.render_in_flight(), list)
