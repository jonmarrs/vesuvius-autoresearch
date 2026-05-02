from train import ExperimentConfig, evaluate_prize_gates


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
    assert any("skeleton-distance samples" in failure for failure in gates["failures"])
    assert any("centerline-dice samples" in failure for failure in gates["failures"])


def test_prize_gates_fail_when_window_exceeds_official_guidance():
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
    assert any("exceeds official prize guidance" in failure for failure in gates["failures"])
