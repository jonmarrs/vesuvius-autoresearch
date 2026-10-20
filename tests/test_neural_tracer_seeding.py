"""scripts/neural_tracer_seeding.py: villa's volume tracer with its hard-coded seeding scales set per micrometre, and
scripts/neural_tracer_seed_probe.py's variants. villa itself is not imported here (it runs in its own environment)."""

import json
import math
import statistics
import sys
import types
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_seed_probe as probe  # noqa: E402
import neural_tracer_seeding as sd  # noqa: E402


def _fake_volume():
    """The parts of villa's tracing/volume.py the patch touches, with its _hessian_kernels reading module globals."""
    vol = types.SimpleNamespace(ndimage=ndimage, HESSIAN_SIGMA=1.5, HESSIAN_RADIUS=6)

    def _hessian_kernels():
        return np.full(2 * vol.HESSIAN_RADIUS + 1, vol.HESSIAN_SIGMA)

    vol._hessian_kernels = _hessian_kernels
    vol._KERNELS = _hessian_kernels()
    return vol


def test_the_presence_smoothing_runs_at_the_scaled_sigma():
    a = np.random.default_rng(0).random((9, 9, 9)).astype(np.float32)
    nd = sd.SmoothingScaled(ndimage, 0.8)
    assert np.array_equal(nd.gaussian_filter(a, 1.0), ndimage.gaussian_filter(a, 0.8))
    assert nd.maximum_filter is ndimage.maximum_filter  # everything else is scipy's


def test_any_other_smoothing_is_refused():
    """volume.py smooths once, at sigma 1.0; another call means villa changed and the patch no longer means one thing."""
    with pytest.raises(ValueError, match="sigma 2.0"):
        sd.SmoothingScaled(ndimage, 0.8).gaussian_filter(np.zeros((3, 3)), 2.0)


def test_the_patch_is_local_to_the_module_and_undone():
    vol, scipy_filter = _fake_volume(), ndimage.gaussian_filter
    with sd.seeding_scaled(vol, smoothing=0.8):
        assert isinstance(vol.ndimage, sd.SmoothingScaled) and vol.ndimage.scale == 0.8
        assert ndimage.gaussian_filter is scipy_filter  # scipy itself untouched
    assert vol.ndimage is ndimage


def test_the_hessian_scale_rebuilds_its_kernels_and_restores_them():
    vol = _fake_volume()
    before = vol._KERNELS
    with sd.seeding_scaled(vol, smoothing=1.0, hessian=1.5 * 1.2137):
        assert vol.HESSIAN_SIGMA == 1.5 * 1.2137
        assert (
            vol.HESSIAN_RADIUS == int(4 * 1.5 * 1.2137 + 0.5) == 7
        )  # scipy's truncate 4, as villa's comment says
        assert len(vol._KERNELS) == 15
    with sd.seeding_scaled(vol, smoothing=1.0, hessian=1.5 / 1.2137):
        assert (
            vol.HESSIAN_RADIUS == int(4 * 1.5 / 1.2137 + 0.5) == 5
        )  # 4.94 rounds up, as scipy's radius does
    assert (1.5, 6, before) == (vol.HESSIAN_SIGMA, vol.HESSIAN_RADIUS, vol._KERNELS)


def test_the_launcher_runs_seeding_in_process():
    """Spawned tile workers would import villa's module unpatched: --tile-workers 0, which villa counts speed-only."""
    s, h, rest = sd.split_argv(
        ["--smoothing", "0.824", "--presence", "p", "--out", "o"]
    )
    assert (s, h) == (0.824, None) and rest == [
        "--presence",
        "p",
        "--out",
        "o",
        "--tile-workers",
        "0",
    ]
    assert sd.split_argv(["--smoothing", "1", "--hessian", "1.2", "--out", "o"])[
        :2
    ] == (1.0, 1.2)
    assert sd.split_argv(["--smoothing", "1", "--tile-workers", "0", "--out", "o"])[
        2
    ] == [
        "--tile-workers",
        "0",
        "--out",
        "o",
    ]
    assert sd.split_argv(["--smoothing", "1", "--tile-workers=0", "--out", "o"])[2] == [
        "--tile-workers=0",
        "--out",
        "o",
    ]
    for bad in (
        ["--smoothing", "1", "--tile-workers", "3", "--out", "o"],
        ["--smoothing", "1", "--tile-workers=2"],
    ):
        with pytest.raises(SystemExit):
            sd.split_argv(bad)
    with pytest.raises(SystemExit):
        sd.split_argv(["--out", "o"])  # the scale is never implicit


def test_the_run_records_its_smoothing_and_refuses_another_on_resume(tmp_path):
    sd.record_seeding(tmp_path, 0.824)
    rec = json.loads((tmp_path / "seeding.json").read_text())
    assert rec["presence_smoothing_sigma"] == 0.824 and rec["villa_default"] == 1.0
    assert rec["hessian_sigma"] == rec["villa_default_hessian"] == 1.5
    sd.record_seeding(tmp_path, 0.824)  # a resume at the same scales
    with pytest.raises(SystemExit, match="0.824"):
        sd.record_seeding(tmp_path, 1.0)
    with pytest.raises(SystemExit):
        sd.record_seeding(tmp_path, 0.824, hessian=1.2)


def test_the_probe_variants_scale_seeding_one_way_per_arm():
    r = 9.6 / 7.91
    run = {"plane_spacing": 64.0, "fill_spacing": 4.0}
    for arm, f in (("A", 1 / r), ("B", r)):
        v = probe.variants(arm, run, r)
        assert v["run"] == {
            "plane_spacing": 64.0,
            "fill_spacing": 4.0,
            "smoothing": 1.0,
            "hessian": None,
        }
        assert math.isclose(v["flags"]["plane_spacing"], 64 * f) and math.isclose(
            v["flags"]["fill_spacing"], 4 * f
        )
        assert v["flags"]["smoothing"] == 1.0 and v["flags"]["hessian"] is None
        assert (
            math.isclose(v["flags_smooth"]["smoothing"], f)
            and v["flags_smooth"]["hessian"] is None
        )
        assert math.isclose(v["flags_smooth_hessian"]["hessian"], 1.5 * f)


P = json.loads((ROOT / "reports/neural_tracer_seed_probe.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_pitch.md").read_text().split())
NAMES = ("run", "flags", "flags_smooth", "flags_smooth_hessian")


def _ratios(arm, name):
    return [r[arm][name]["dots"] / r["native_dots"] for r in P["cubes"].values()]


def _med(arm, name):
    return statistics.median(_ratios(arm, name))


def test_the_probe_reproduces_both_runs_recorded_seed_dots_on_every_cube():
    funnel = json.loads((ROOT / "reports/neural_tracer_pitch_funnel.json").read_text())[
        "cubes"
    ]
    assert sorted(P["cubes"]) == sorted(funnel) and len(P["cubes"]) == 21
    for c, r in P["cubes"].items():
        assert (r["native_dots"], r["pitch_dots"]) == (
            funnel[c]["native"]["dots"],
            funnel[c]["pitch"]["dots"],
        )
        assert (
            r["A"]["run"]["dots"] == r["pitch_dots"]
            and r["B"]["run"]["dots"] == r["native_dots"]
        )
    assert (
        "it reproduces the seed dots that run recorded, on all 21 cubes of both runs"
        in REPORT
    )
    assert P["ratio"] == probe.R


def test_the_seed_table_quotes_the_medians():
    labels = (
        "the run's own settings",
        "`--plane-spacing` and `--fill-spacing` scaled",
        "and the presence smoothing, sigma 1 grid voxel in code",
        "and the Hessian, sigma 1.5 grid voxels in code",
    )
    for label, name in zip(labels, NAMES, strict=True):
        a, b = _med("A", name), _med("B", name)
        cell_b = "1" if name == "run" else f"{b:.2f}"
        assert f"| {label} | {a:.2f} | {cell_b} |" in REPORT, label
    assert _med("B", "run") == 1


def test_the_flags_barely_move_it_and_the_smoothing_does():
    fill = statistics.median(
        r["B"]["run"]["fill_dots"] / r["B"]["run"]["dots"] for r in P["cubes"].values()
    )
    assert (
        f"raises the 9.6 µm run's seeds from {_med('A', 'run'):.2f} to {_med('A', 'flags'):.2f} of native"
        in REPORT
        and f"{round(100 * fill)}% of native seed dots are fill-in ones" in REPORT
    )
    a, b = _ratios("A", "flags_smooth"), _ratios("B", "flags_smooth")
    assert (
        f"raises the 9.6 µm seeds to {_med('A', 'flags_smooth'):.2f} of native ({min(a):.2f}–{max(a):.2f} per cube)"
        in REPORT
        and f"lowers the native seeds to {_med('B', 'flags_smooth'):.2f} ({min(b):.2f}–{max(b):.2f}), near the 9.6 µm "
        f"run's {_med('A', 'run'):.2f}"
        in REPORT
    )
    moved = max(
        abs(r[arm]["flags_smooth_hessian"]["dots"] - r[arm]["flags_smooth"]["dots"])
        / r["native_dots"]
        for r in P["cubes"].values()
        for arm in "AB"
    )
    assert (
        moved < 0.03 and "changes no cube's count by more than 0.03 of native" in REPORT
    )


def test_the_probe_records_the_settings_it_counted():
    r = 9.6 / 7.91
    for c, row in P["cubes"].items():
        for arm in "AB":
            own = row[arm]["run"]
            for name, v in probe.variants(arm, own, r).items():
                got = {k: row[arm][name][k] for k in v}
                assert got == json.loads(json.dumps(v)), (c, arm, name)


PREREG = " ".join(
    (ROOT / "docs/preregistration/2026-10-19_neural_tracer_seeding_scale.md")
    .read_text()
    .split()
)


def test_the_proposal_is_not_a_registration():
    assert "**Status: PROPOSED, not registered, nothing run.**" in PREREG
    assert (
        "registration is the commit that adds the chain and the analysis script"
        in PREREG
    )


def test_the_proposals_arms_are_the_probes_scales():
    r = probe.R
    assert f"r = 9.6 / 7.91 = {r:.4f}" in PREREG
    for row in (
        f"| `--plane-spacing` (64) | 64 / r = {64 / r:.2f} | 64 × r = {64 * r:.2f} |",
        f"| `--fill-spacing` (4) | 4 / r = {4 / r:.2f} | 4 × r = {4 * r:.2f} |",
        f"| `--fill-skip` (4) | 4 / r = {4 / r:.2f} | 4 × r = {4 * r:.2f} |",
        f"| presence smoothing (1, in code) | 1 / r = {1 / r:.3f} | r = {r:.3f} |",
        f"| expected seed dots, median of native (probe) | {_med('A', 'flags_smooth'):.2f} "
        f"| {_med('B', 'flags_smooth'):.2f} |",
    ):
        assert row in PREREG, row
    one = next(iter(P["cubes"].values()))
    for arm, f in (("A", 1 / r), ("B", r)):
        v = one[arm]["flags_smooth"]
        assert math.isclose(v["plane_spacing"], 64 * f) and math.isclose(
            v["fill_spacing"], 4 * f
        )
        assert (
            math.isclose(v["smoothing"], f) and v["hessian"] is None
        )  # the arm leaves the Hessian at villa's


def test_the_proposals_motivation_quotes_the_exploration():
    s = json.loads((ROOT / "reports/neural_tracer_pitch_funnel.json").read_text())[
        "summary"
    ]
    pct = [round(100 * x) for x in s["no_heading_share"]]
    assert (
        f"started {s['traces']:.2f} times as many traces from {s['dots']:.2f} times as many seed dots"
        in PREREG
        and f"restore the 9.6 µm seeds to {_med('A', 'flags_smooth'):.2f} of native"
        in PREREG
        and f"cut the native seeds to {_med('B', 'flags_smooth'):.2f}" in PREREG
        and f"move the 9.6 µm seeds only from {_med('A', 'run'):.2f} to {_med('A', 'flags'):.2f}"
        in PREREG
        and f"({pct[1]}% against {pct[0]}%)" in PREREG
    )
