"""scripts/diagnose_topology_postproc.py measures what the loop measures: best_model.pt with its own recipe and
complete weights, the loop's validation protocol, and the loop's topology threshold as its baseline. Its prediction
cache is used only for the checkpoint and validation sample it was made from."""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diagnose_topology_postproc as dtp  # noqa: E402

SIZE, LAYERS = 8, 4


def test_despeckle_removes_components_under_the_minimum():
    mask = np.zeros((16, 16), bool)
    mask[0:2, 0:2] = True  # 4 pixels
    mask[8:13, 8:13] = True  # 25 pixels
    assert dtp.despeckle(mask, 1) is mask
    kept = dtp.despeckle(mask, 16)
    assert kept.sum() == 25 and not kept[0:2, 0:2].any()
    assert not dtp.despeckle(np.zeros((4, 4), bool), 16).any()


def _patches(n):
    """n ink-containing [1, 1, H, W] patches: a bar of ink, predicted with a 1-pixel speck beside it."""
    probs, targets = [], []
    for _ in range(n):
        target = torch.zeros(1, 1, SIZE, SIZE)
        target[0, 0, 3:5, 1:7] = 1
        prob = target * 0.9
        prob[0, 0, 0, 0] = 0.9
        probs.append(prob)
        targets.append(target)
    return probs, targets


def test_topo_metrics_samples_as_the_loop_and_despeckles_first(monkeypatch):
    seen = {"skel": [], "cc": []}

    def skel(gt, pred):
        seen["skel"].append(pred.copy())
        return float("nan") if len(seen["skel"]) == 2 else 1.0

    def cc(gt, pred):
        seen["cc"].append(pred.copy())
        return 0

    monkeypatch.setattr(dtp, "compute_skeleton_dist", skel)
    monkeypatch.setattr(
        dtp, "compute_centerline_dice", lambda g, p, **k: {"centerline_dice": 0.5}
    )
    monkeypatch.setattr(dtp, "compute_cc_diff", cc)
    probs, targets = _patches(25)
    m = dtp.topo_metrics(probs, targets, 0.5, 4)
    # cc_diff on every patch, skel_dist and centerline_dice on patches 0, 10 and 20.
    assert len(seen["cc"]) == 25 and len(seen["skel"]) == 3
    # The speck is removed before any metric sees the prediction.
    assert not any(p[..., 0, 0].any() for p in seen["skel"] + seen["cc"])
    # A skel_dist that is not finite is counted, not averaged in or raised.
    assert m["n_skel"] == 2 and m["n_undefined"] == 1 and m["skel_dist"] == 1.0
    assert m["centerline_dice"] == 0.5 and m["dice"] == pytest.approx(1.0)


class Model(torch.nn.Module):
    def forward(self, x):
        return torch.zeros(len(x), 1, SIZE, SIZE)


SETTINGS = {
    "architecture": "resenc_unet",
    "patch_size": SIZE,
    "num_layers": LAYERS,
    "base_feat": 16,
    "num_blocks": 16,
    "num_heads": 8,
    "dropout": 0.0,
    "use_ridges": False,
    "multi_task_heads": False,
    "ridge_sigma": 2.0,
}


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    """main() in an empty directory, with the checkpoint load, the protocol's dataset and sample, the inputs'
    fingerprint and the topology metrics stubbed. Records what each stub was given."""
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / "best_model.pt"
    checkpoint.write_bytes(b"weights v1")
    calls = {"load": [], "collect": [], "dataset": []}
    state = {"inputs": "inputs-a", "complete": True, "stored": {"use_lasagna": True}}

    def load(path, device):
        calls["load"].append(path)
        return (
            Model(),
            dict(SETTINGS),
            {"config": dict(SETTINGS, **state["stored"]), "avg_skel_dist": 3.0},
        )

    def dataset(config):
        calls["dataset"].append(
            (config.patch_size, config.num_layers, config.use_lasagna)
        )
        return object()

    def collect(
        model, ds, num_layers, device, batch_size, amp_enabled, probabilities, protocol
    ):
        calls["collect"].append(protocol)
        # The checkpoint's own input check and ink probabilities, as reevaluate_best_model.py.
        out = probabilities(model, torch.rand(1, 1, num_layers, SIZE, SIZE))
        assert out.shape == (1, 1, SIZE, SIZE)
        probs, targets = _patches(3)
        empty = torch.zeros(1, 1, SIZE, SIZE)
        return (
            probs + [empty],
            targets + [empty],
            {"complete": state["complete"], "batch_errors": 1},
        )

    monkeypatch.setattr(dtp, "load_tool_checkpoint", load)
    monkeypatch.setattr(dtp, "build_validation_dataset", dataset)
    monkeypatch.setattr(dtp, "collect_validation_predictions", collect)
    monkeypatch.setattr(
        dtp, "validation_inputs_fingerprint", lambda uri, band: state["inputs"]
    )
    monkeypatch.setattr(dtp, "select_topology_threshold", lambda p, t: (0.3, 0.6))
    monkeypatch.setattr(dtp, "compute_skeleton_dist", lambda g, p: 1.5)
    monkeypatch.setattr(
        dtp, "compute_centerline_dice", lambda g, p, **k: {"centerline_dice": 0.5}
    )
    cache = tmp_path / "cache.pt"

    def main(*extra):
        assert (
            dtp.main(["--checkpoint", str(checkpoint), "--cache", str(cache), *extra])
            == 0
        )
        return capsys.readouterr().out

    return main, calls, state, checkpoint, cache


def test_it_scores_the_checkpoint_with_its_own_recipe_on_the_protocol(run):
    main, calls, state, checkpoint, cache = run
    out = main()
    assert calls["load"] == [str(checkpoint)]
    # The dataset is built for the checkpoint's geometry and recorded inputs, not config.json's defaults.
    assert calls["dataset"] == [(SIZE, LAYERS, True)]
    assert calls["collect"] == [
        dtp.validation_protocol(dtp.ExperimentConfig().depth_band)
    ]
    assert "scored patches: 4, ink-containing: 3" in out
    baseline = [line for line in out.splitlines() if "the loop's measurement" in line]
    assert len(baseline) == 1 and baseline[0].split()[:2] == ["0.300", "1"]
    assert (
        "Baseline (topology threshold 0.300, no post-processing): skel_dist=1.500, "
        "gate=2.0; stored avg_skel_dist=3.0"
    ) in out


def test_unwarped_scores_a_lasagna_checkpoint_without_the_warp(run):
    main, calls, state, checkpoint, cache = run
    main("--unwarped")
    assert calls["dataset"] == [(SIZE, LAYERS, False)]


def test_the_cache_is_used_only_for_its_checkpoint_and_inputs(run):
    main, calls, state, checkpoint, cache = run
    main()
    assert cache.exists() and len(calls["collect"]) == 1
    assert "loaded cached predictions: 4 patches" in main()
    assert len(calls["collect"]) == 1
    checkpoint.write_bytes(b"weights v2")  # a promotion
    assert "another checkpoint or validation sample" in main()
    assert len(calls["collect"]) == 2
    state["inputs"] = "inputs-b"  # other validation labels
    main()
    assert len(calls["collect"]) == 3
    cache.write_bytes(b"not a cache")
    assert "ignoring unreadable prediction cache" in main()
    assert len(calls["collect"]) == 4


def test_an_incomplete_sample_is_neither_measured_nor_cached(run):
    main, calls, state, checkpoint, cache = run
    state["complete"] = False
    with pytest.raises(SystemExit, match="sample is incomplete"):
        main()
    assert not cache.exists()
