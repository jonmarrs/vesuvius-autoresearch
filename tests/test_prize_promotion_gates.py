import math

import numpy as np
import pytest
from train import (
    SKELETON_DISTANCE_AVAILABLE,
    ExperimentConfig,
    compute_skeleton_dist,
    evaluate_prize_gates,
)


def test_prize_gates_pass_with_submittable_window_and_topology_metrics():
    config = ExperimentConfig(
        patch_size=64,
        min_prize_centerline_dice=0.01,
        max_prize_skel_dist=2.0,
        max_prize_cc_diff=64.0,
    )

    gates = evaluate_prize_gates(
        config,
        val_bpb=0.2,
        avg_skel_dist=0.8,
        avg_centerline_dice=0.25,
        avg_cc_diff=3.0,
        num_skel_samples=4,
        num_centerline_samples=4,
        num_cc_samples=20,
    )

    assert gates["submittable"] is True
    assert gates["villa_metrics_ok"] is True
    assert gates["failures"] == []


def test_prize_gates_fail_when_dice_improves_but_topology_is_missing():
    config = ExperimentConfig(patch_size=64, min_prize_topology_samples=1)

    gates = evaluate_prize_gates(
        config,
        val_bpb=0.1,
        avg_skel_dist=1.0,
        avg_centerline_dice=0.0,
        avg_cc_diff=0.0,
        num_skel_samples=0,
        num_centerline_samples=0,
        num_cc_samples=0,
    )

    assert gates["submittable"] is False
    # skel_dist is no longer a gate (FINDINGS.md Phase 4b); the spatial signal that must
    # be present is centerline-dice, not skeleton-distance.
    assert any("centerline-dice samples" in failure for failure in gates["failures"])


def test_prize_gates_ignore_skeleton_distance_when_unavailable():
    # skel_dist is reported but NOT gated (it is uncorrelated with detection quality;
    # see FINDINGS.md Phase 4b). A NaN / sample-less skel_dist must not block a model
    # whose window and spatial topology signal (centerline_dice) are fine.
    config = ExperimentConfig(patch_size=64, min_prize_topology_samples=1)

    gates = evaluate_prize_gates(
        config,
        val_bpb=0.1,
        avg_skel_dist=float("nan"),
        avg_centerline_dice=0.25,
        avg_cc_diff=0.0,
        num_skel_samples=0,
        num_centerline_samples=4,
        num_cc_samples=20,
    )

    assert gates["submittable"] is True
    assert not any("skel_dist" in failure for failure in gates["failures"])
    assert not any("skeleton-distance" in failure for failure in gates["failures"])


def test_skeleton_distance_fallback_returns_nan_when_official_metric_is_missing():
    if SKELETON_DISTANCE_AVAILABLE:
        pytest.skip("official skeleton-distance metric is available")

    empty = np.zeros((1, 8, 8), dtype=bool)

    assert math.isnan(compute_skeleton_dist(empty, empty))


def test_local_gates_keep_the_registered_window_limit():
    config = ExperimentConfig(patch_size=128)

    gates = evaluate_prize_gates(
        config,
        val_bpb=0.2,
        avg_skel_dist=0.8,
        avg_centerline_dice=0.25,
        avg_cc_diff=3.0,
        num_skel_samples=4,
        num_centerline_samples=4,
        num_cc_samples=20,
    )

    assert gates["window_ok"] is False
    assert gates["submittable"] is False
    assert any(
        "exceeds the local evaluation limit" in failure for failure in gates["failures"]
    )


def test_a_pass_without_centerline_samples_records_it_unmeasured():
    """No samples averaged to 0.0, which history.tsv recorded as a score and
    the gates failed as "below gate" (no villa metric gives no samples)."""
    from train import mean_or_nan

    assert math.isnan(mean_or_nan([]))
    assert mean_or_nan([0.25, 0.75]) == 0.5
    gates = evaluate_prize_gates(
        ExperimentConfig(patch_size=64, min_prize_centerline_dice=0.01),
        val_bpb=0.2,
        avg_skel_dist=0.8,
        avg_centerline_dice=mean_or_nan([]),
        avg_cc_diff=3.0,
        num_skel_samples=4,
        num_centerline_samples=0,
        num_cc_samples=20,
    )
    assert gates["villa_metrics_ok"] is False
    assert "avg_centerline_dice is not finite" in gates["failures"]
    assert not any("below gate" in failure for failure in gates["failures"])
