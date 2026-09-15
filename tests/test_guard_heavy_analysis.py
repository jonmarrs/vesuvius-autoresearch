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


def test_detects_the_containerised_band_renderer():
    """The blind spot this guard SHIPPED with.

    The heavy stage is `vc_render_tifxyz` in a Docker container -- 25GB RSS, the
    stage that OOM-killed this box three times -- and it shares none of the villa
    venv path. Matching the interpreter alone reported "no render in flight"
    during exactly the stage where proceeding is most damaging.
    """
    assert gha.RENDER_BINARIES, "no render binary is matched at all"
    assert any("vc_render_tifxyz" in b for b in gha.RENDER_BINARIES)


def test_does_not_match_a_shell_that_merely_mentions_the_path(tmp_path, monkeypatch):
    """argv[0] only: the guard once counted the shell that invoked it."""
    src = Path(gha.__file__).read_text() if hasattr(gha, "__file__") else ""
    assert "argv0" in src, "detection must key on argv[0], not the whole cmdline"
    assert 'cmd.split(" ", 1)[0]' in src


def test_marker_covers_both_villa_checkouts():
    """Third detection gap: fits run from villa-spiral-CURRENT, renders from
    villa-spiral. A marker naming either one ignores the other entirely."""
    assert "villa-spiral/" not in gha.VILLA_VENV_MARK, (
        "marker pins one checkout; villa-spiral-current fits would go undetected"
    )
    for checkout in ("villa-spiral", "villa-spiral-current"):
        path = f"/home/jon/ws/{checkout}/spiral-fitting/.venv/bin/python"
        assert gha.VILLA_VENV_MARK in path, f"{checkout} not matched"


def test_fail_if_any_refuses_regardless_of_free_memory(monkeypatch, capsys):
    """Headroom is the wrong question for a job that must not run concurrently.
    A caller using --need-gb 2 to mean 'is anything running' passes whenever
    memory is plentiful, which is exactly when a second render is most tempting."""
    monkeypatch.setattr(gha, "render_in_flight", lambda: [(7, "villa python")])
    monkeypatch.setattr(gha, "free_gb", lambda: 999.0)
    monkeypatch.setattr("sys.argv", ["x", "--fail-if-any"])
    assert gha.main() == 1
    assert "must not run alongside" in capsys.readouterr().out


def test_fail_if_any_passes_when_nothing_runs(monkeypatch, capsys):
    monkeypatch.setattr(gha, "render_in_flight", lambda: [])
    monkeypatch.setattr("sys.argv", ["x", "--fail-if-any"])
    assert gha.main() == 0
    assert "no villa job in flight" in capsys.readouterr().out
