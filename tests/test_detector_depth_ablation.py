"""scripts/detector_depth_ablation.py: its windows are the loop's, its fills come
from the window it keeps."""

import json
from pathlib import Path

import numpy as np
import pytest
from conftest import restore_cuda_env

from scripts import detector_depth_ablation as mod
from scripts.detector_on_loop_sample import ZARR_SLICE_0_LAYER
from vesuvius_autoresearch.core.inference_constants import DEPTH_MARGIN
from vesuvius_autoresearch.detector.config import DetectorConfig

restore_cuda_env()  # do not leave the mask for other test modules

REPO = Path(__file__).resolve().parents[1]


def _loop_offsets():
    """The detector channels where the loop's 16-slice window can start.

    As VesuviusLabeledDataset draws validation reads: a band widened by the
    margin and clamped to the volume, a read of num_layers + 2 margins starting
    anywhere in it, and the model keeps the read's middle num_layers.
    """
    config = json.loads((REPO / "config.json").read_text())
    profile = json.loads((REPO / "reports" / "ink_depth_profile.json").read_text())
    depth = profile["fragments"]["PHercParis2Fr143"]["shape"][0]
    band_start, band_end = config["depth_band"]
    read = config["num_layers"] + 2 * DEPTH_MARGIN
    start = max(0, band_start - DEPTH_MARGIN)
    end = min(depth, band_end + DEPTH_MARGIN)
    channel_0 = DetectorConfig().start_idx - ZARR_SLICE_0_LAYER
    return [z0 + DEPTH_MARGIN - channel_0 for z0 in range(start, end - read + 1)]


def test_the_offsets_are_the_loops_lowest_middle_and_highest_window():
    offsets = _loop_offsets()
    low, high = min(offsets), max(offsets)
    assert (mod.OFFSETS[0], mod.OFFSETS[-1]) == (low, high) == (3, 10)
    assert mod.OFFSETS[1] in {(low + high) // 2, (low + high + 1) // 2}
    config = json.loads((REPO / "config.json").read_text())
    assert config["num_layers"] == mod.KEPT


@pytest.mark.parametrize("fill", mod.FILLS)
@pytest.mark.parametrize("offset", mod.OFFSETS)
def test_the_window_is_kept_and_the_fill_comes_from_it(offset, fill):
    channels = DetectorConfig().in_chans
    x = np.arange(2 * channels * 4, dtype=np.float32).reshape(2, channels, 2, 2)
    out = mod.windowed(x, offset, fill)
    assert out.shape == x.shape
    kept = slice(offset, offset + mod.KEPT)
    np.testing.assert_array_equal(out[:, kept], x[:, kept])
    for c in [*range(offset), *range(offset + mod.KEPT, channels)]:
        assert any(
            np.array_equal(out[:, c], x[:, k]) for k in range(*kept.indices(channels))
        ), f"channel {c} is not a copy of a kept channel"
    if fill == "edge" and offset > 0:
        np.testing.assert_array_equal(out[:, 0], x[:, offset])


def test_every_variant_is_scored_and_the_first_is_the_full_depth():
    names = [name for name, _, _ in mod.variants(DetectorConfig().in_chans)]
    assert names[0] == "full"
    assert len(names) == 1 + len(mod.FILLS) * len(mod.OFFSETS)


def test_the_draw_is_inside_the_mask_and_repeatable():
    mask = np.zeros((300, 300), bool)
    mask[40:260, 10:290] = True
    a, n = mod.random_windows(mask, 64, 32, 0, 10)
    b, _ = mod.random_windows(mask, 64, 32, 0, 10)
    assert a == b and len(a) == 10 and n >= 10
    for y, x in a:
        assert y % 32 == 0 and x % 32 == 0
        assert mask[y : y + 64, x : x + 64].all()


RESULT_PATH = REPO / "reports" / "detector_depth_ablation.json"
RESULT = json.loads(RESULT_PATH.read_text()) if RESULT_PATH.exists() else None
REPORT_PATH = REPO / "reports" / "detector_depth_ablation.md"


def _row(label, zarr, name):
    c, d = RESULT["cards"], RESULT["auc_drops"]
    if name == "full":
        return f"| {label} | {zarr} | {c['full']['roc_auc']:.4f} | 0 | 0 | {c['full']['ap_prevalence_lift']:.4f} |"
    offset = name.split("_")[1]
    return (
        f"| {label} | {zarr} | {c[name]['roc_auc']:.4f} | **{d[name]:.4f}** | "
        f"{d['edge_' + offset]:.4f} | {c[name]['ap_prevalence_lift']:.4f} |"
    )


def _quoted():
    d, c = RESULT["auc_drops"], RESULT["cards"]
    control = json.loads(
        (REPO / "reports" / "detector_random_window_control.json").read_text()
    )
    return {
        "commit": f"run at\n`{RESULT['git_commit'][:8]}`",
        "windows": f"**{RESULT['windows']}** random windows of Fr143 (seed {RESULT['seed']}",
        "pixels": f"**{RESULT['n_pixels']:,}** pixels, ink prevalence **{RESULT['ink_prevalence']:.4f}**",
        "full": _row("all 26", "1–26", "full"),
        "low": _row("3–18 (the loop's lowest window)", "4–19", "reflect_3"),
        "mid": _row("7–22 (a middle window)", "8–23", "reflect_7"),
        "high": _row("10–25 (the loop's highest window)", "11–26", "reflect_10"),
        "drops": f"The drops are {d['reflect_3']:.4f},\n{d['reflect_7']:.4f} and {d['reflect_10']:.4f}",
        "ratio": f"loses {d['reflect_3']:.4f}, {d['reflect_3'] / d['reflect_10']:.1f} times as much",
        "high text": f"(0–9) and loses\n{d['reflect_10']:.4f}",
        "above chance": f"loses {d['reflect_3']:.4f} of its {c['full']['roc_auc'] - 0.5:.4f} above chance",
        "control reproduced": f"{control['cards']['detector_single_window']['roc_auc']:.4f}",
    }


def test_the_pre_registered_reading_holds():
    if RESULT is None:
        pytest.skip("not run")
    primary = [RESULT["auc_drops"][f"reflect_{o}"] for o in mod.OFFSETS]
    assert not all(d <= 0.02 for d in primary)
    assert not all(d >= 0.05 for d in primary)
    assert RESULT["reading"] == "depends on the window's position"
    assert "it depends on the window's position" in REPORT_PATH.read_text()


def test_the_position_effect_holds_under_both_fills():
    if RESULT is None:
        pytest.skip("not run")
    d = RESULT["auc_drops"]
    for fill in mod.FILLS:
        assert d[f"{fill}_3"] > d[f"{fill}_7"] > d[f"{fill}_10"]


@pytest.mark.parametrize(
    "name",
    sorted(
        [
            "commit",
            "windows",
            "pixels",
            "full",
            "low",
            "mid",
            "high",
            "drops",
            "ratio",
            "high text",
            "above chance",
            "control reproduced",
        ]
    ),
)
def test_the_report_quotes_the_result(name):
    if RESULT is None:
        pytest.skip("not run")
    report = REPORT_PATH.read_text()
    text = _quoted()[name]
    assert text in report or " ".join(text.split()) in " ".join(report.split()), (
        f"{name}: {text!r} not in the report"
    )
