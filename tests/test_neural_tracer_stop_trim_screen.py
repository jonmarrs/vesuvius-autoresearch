"""The stop-trim screen trims only interior, unlinked confidence-stop ends, by exactly k voxels of arclength, and its
report states the screen's record."""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "neural_tracer_stop_trim_screen", ROOT / "scripts/neural_tracer_stop_trim_screen.py"
)
ts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ts)

SIZE = 256


def line(z0: float, z1: float) -> np.ndarray:
    """A straight fiber along z through the middle of the cube, one point per voxel."""
    z = np.arange(z0, z1 + 1, 1.0)
    return np.stack([z, np.full_like(z, 128.0), np.full_like(z, 128.0)], axis=1)


def arclength(q: np.ndarray) -> float:
    return float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())


def test_trim_end_removes_exactly_k_voxels_of_arclength_from_the_first_end():
    q = line(50, 150)
    t = ts.trim_end(q, 10.5)
    assert np.allclose(t[0], [60.5, 128, 128]) and np.allclose(t[-1], q[-1])
    assert arclength(t) == pytest.approx(arclength(q) - 10.5)
    assert ts.trim_end(q, 0.0) is q
    assert len(ts.trim_end(q, 100.0)) == 0 and len(ts.trim_end(q, 250.0)) == 0


@pytest.mark.parametrize(
    "reasons, links, z0, cut",
    [
        (("confidence", "confidence"), (-1, -1), 50, (20, 20)),
        (("confidence", "bounds"), (-1, -1), 50, (20, 0)),
        (("bounds", "confidence"), (-1, -1), 50, (0, 20)),
        (("owned_or_live", "bounds"), (-1, -1), 50, (0, 0)),
        (
            ("confidence", "confidence"),
            (7, -1),
            50,
            (0, 20),
        ),  # a linked end continues as another fiber
        (
            ("confidence", "confidence"),
            (-1, -1),
            3,
            (0, 20),
        ),  # an end within EDGE of a face is not a real stop
    ],
)
def test_only_interior_unlinked_confidence_ends_are_trimmed(reasons, links, z0, cut):
    """cut: voxels removed at (first, last) point; a stop's reasons and links are listed in that order."""
    q = line(z0, 150)
    out, ends, dropped = ts.trimmed({1: q}, {1: (reasons, links)}, SIZE, 20.0)
    assert (ends, dropped) == (sum(c > 0 for c in cut), 0)
    assert out[1][0][0] == pytest.approx(z0 + cut[0])
    assert out[1][-1][0] == pytest.approx(150 - cut[1])


def test_a_cut_on_a_vertex_repeats_no_point():
    t = ts.trim_end(line(50, 150), 20.0)
    assert t[0][0] == 70 and np.all(np.linalg.norm(np.diff(t, axis=0), axis=1) > 0)


def test_a_piece_trimmed_below_villa_s_min_length_is_dropped_and_k_0_changes_nothing():
    short = line(100, 100 + ts.MIN_POINTS + 10)
    meta = {1: (("confidence", "confidence"), (-1, -1))}
    assert ts.trimmed({1: short}, meta, SIZE, 20.0)[1:] == (2, 1)
    out, ends, dropped = ts.trimmed({1: short}, meta, SIZE, 0.0)
    assert np.array_equal(out[1], short) and (ends, dropped) == (2, 0)


def test_the_oracle_trims_each_end_back_to_its_last_on_reference_point():
    q = line(50, 150)
    meta = {1: (("confidence", "confidence"), (-1, -1))}
    out, ends, _ = ts.trimmed(
        {1: q}, meta, SIZE, "oracle", lambda p: (p[:, 0] >= 62) & (p[:, 0] <= 141)
    )
    assert ends == 2 and (out[1][0][0], out[1][-1][0]) == (62, 141)
    assert (
        ts.trimmed({1: q}, meta, SIZE, "oracle", lambda p: p[:, 0] < 0)[2] == 1
    )  # nothing on it: dropped


RECORD = json.loads(
    (
        ROOT / "reports/evidence/neural_tracer_stop_trim_screen_2026-11-05.json"
    ).read_text()
)
REPORT = " ".join(
    (ROOT / "reports/neural_tracer_stop_trim_screen.md").read_text().split()
)


def test_the_record_is_in_sample_only_and_reproduced_the_baseline():
    import neural_tracer_confidence_stops as cs

    assert RECORD["status"] == "OK" and RECORD["baseline_drift"] == []
    assert (
        RECORD["cubes"]
        == list(cs.IN_SAMPLE)
        == sorted(RECORD["per_cube"], key=RECORD["cubes"].index)
    )
    assert not set(RECORD["per_cube"]) & set(cs.HELD_OUT)


@pytest.mark.parametrize("k, label", [("10", "10 voxels"), ("20", "20 voxels"), ("40", "40 voxels"), ("oracle", "oracle")])  # fmt: skip
def test_each_table_row_is_the_record_s_tolerance_2_summary(k, label):
    s = RECORD["summary"][f"k{k}_tol2"]
    row = (f"| {label} | {s['precision_change_median']:+.4f} | {s['coverage_change_median']:+.4f} | "
           f"{s['erlpen_ratio_median']:.3f}× | {s['erlpen_rose_on']} of 11 | {s['merges'][0]} → {s['merges'][1]} |")  # fmt: skip
    assert row.replace("+-", "−").replace("-", "−") in REPORT.replace("-", "−")


def test_the_prose_figures_are_the_record_s():
    s, pc = RECORD["summary"], RECORD["per_cube"]
    merges = [
        1 - s[f"k{k}_tol2"]["merges"][1] / s[f"k{k}_tol2"]["merges"][0]
        for k in ("10", "40")
    ]
    assert f"Merges fell {100 * merges[0]:.1f}–{100 * merges[1]:.1f}%" in REPORT
    t4 = s["k20_tol4"]
    assert f"at 20 voxels precision {t4['precision_change_median']:+.4f}, coverage {t4['coverage_change_median']:+.4f}".replace("-", "−") in REPORT  # fmt: skip
    gain = sorted(
        pc[c]["oracle"]["rows"]["2"]["precision"] - pc[c]["0"]["rows"]["2"]["precision"]
        for c in pc
    )
    words = dict(
        enumerate(
            "none one two three four five six seven eight nine ten eleven".split()
        )
    )
    assert (
        f"(+{gain[0]:.3f} to +{gain[-1]:.3f}; above 0.03 on {words[sum(g > 0.03 for g in gain)]} cubes)"
        in REPORT
    )
    assert (
        f"for a median {-s['koracle_tol2']['coverage_change_median']:.4f} of coverage"
        in REPORT
    )
    removed = {}
    for t in ("2", "4"):
        off = [sum((1 - pc[c][k]["rows"][t]["precision"]) * pc[c][k]["rows"][t]["pred_length"] for c in pc) for k in ("0", "oracle")]  # fmt: skip
        removed[t] = 100 * (1 - off[1] / off[0])
    assert f"removes {removed['2']:.1f}% of the off-reference length at tolerance 2 ({removed['4']:.1f}% at tolerance 4)" in REPORT  # fmt: skip
    assert f"The other {100 - removed['2']:.0f}% lies elsewhere" in REPORT
    length = [
        sum(pc[c][k]["rows"]["2"]["pred_length"] for c in pc) for k in ("0", "oracle")
    ]
    assert (
        f"and {100 * (1 - length[1] / length[0]):.1f}% of all traced length" in REPORT
    )
