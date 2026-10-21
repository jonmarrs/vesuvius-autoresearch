"""scripts/diagnose_topology_postproc.py measures what the loop measures: best_model.pt with its own recipe and
complete weights, the loop's validation protocol in fp32, and the loop's topology threshold as its baseline. Its
prediction cache is used only for the checkpoint and validation sample it was made from."""

import hashlib
import io
import os
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
    """n ink-containing [1, 1, H, W] patches, patch i a 2 x (1 + i % 7) bar of ink, so its ink area names it; each
    predicted with a 1-pixel speck beside it."""
    probs, targets = [], []
    for i in range(n):
        target = torch.zeros(1, 1, SIZE, SIZE)
        target[0, 0, 3:5, 1 : 2 + i % 7] = 1
        prob = target * 0.9
        prob[0, 0, 0, 0] = 0.9
        probs.append(prob)
        targets.append(target)
    return probs, targets


def test_topo_metrics_samples_as_the_loop_and_despeckles_first(monkeypatch):
    seen = {"skel": [], "cc": []}

    def skel(gt, pred, **kwargs):
        assert kwargs == {
            "output_folder": dtp.HIST_DIR
        }  # not the loop's histogram folder
        seen["skel"].append((int(gt.sum()), pred.copy()))
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
    m = dtp.topo_metrics(probs, targets, 0.5, 2)  # removes the speck, keeps every bar
    # cc_diff on every patch; skel_dist and centerline_dice on patches 0, 10 and 20, whose ink areas are 2, 8, 14.
    assert len(seen["cc"]) == 25
    assert [area for area, _ in seen["skel"]] == [2, 8, 14]
    # The speck is removed before any metric sees the prediction.
    preds = [p for _, p in seen["skel"]] + seen["cc"]
    assert not any(p[..., 0, 0].any() for p in preds)
    # A skel_dist that is not finite is counted, not averaged in or raised.
    assert m["n_skel"] == 2 and m["n_undefined"] == 1 and m["skel_dist"] == 1.0
    assert m["centerline_dice"] == 0.5 and m["dice"] == pytest.approx(1.0)


def test_it_refuses_without_villas_metrics(monkeypatch):
    """train.py's stand-ins report NaN for skel_dist and centerline_dice, and scipy's count for cc_diff."""
    monkeypatch.setattr(dtp.train, "SKELETON_DISTANCE_AVAILABLE", True)
    monkeypatch.setattr(dtp.train, "CENTERLINE_DICE_IMPORT_ERROR", None)
    monkeypatch.setattr(dtp.train, "compute_cc_official", object(), raising=False)
    dtp.require_villa_metrics()
    for name, value, said in (
        ("SKELETON_DISTANCE_AVAILABLE", False, "skeleton distance"),
        ("CENTERLINE_DICE_IMPORT_ERROR", "no module", "centerline dice"),
    ):
        with monkeypatch.context() as m:
            m.setattr(dtp.train, name, value)
            with pytest.raises(SystemExit, match=said):
                dtp.require_villa_metrics()
    monkeypatch.delattr(dtp.train, "compute_cc_official")
    with pytest.raises(SystemExit, match="connected components"):
        dtp.require_villa_metrics()


class Model(torch.nn.Module):
    def forward(self, x):
        return torch.zeros(len(x), 1, SIZE, SIZE)


# A recipe that differs from ExperimentConfig's defaults in every setting the model takes.
SETTINGS = {
    "architecture": "resenc_unet",
    "patch_size": SIZE,
    "num_layers": LAYERS,
    "base_feat": 16,
    "num_blocks": 6,
    "num_heads": 4,
    "dropout": 0.1,
    "use_ridges": True,
    "multi_task_heads": True,
    "ridge_sigma": 3.0,
}


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    """main() in an empty directory, with the checkpoint load, the protocol's dataset and sample, the inputs'
    fingerprint and the topology metrics stubbed. Records what each stub was given."""
    monkeypatch.chdir(tmp_path)
    checkpoint = tmp_path / "best_model.pt"
    checkpoint.write_bytes(b"weights v1")
    calls = {
        "villa": [],
        "load": [],
        "collect": [],
        "dataset": [],
        "threshold": [],
        "topo": [],
    }
    state = {
        "inputs": "inputs-a",
        "protocol": "protocol-a",
        "complete": True,
        "diag_inputs": None,
        "chk": {"use_lasagna": True},
    }

    def load(source, device):
        # The bytes that were hashed, not a path the loop could replace meanwhile.
        assert not isinstance(source, (str, os.PathLike))
        calls["load"].append(source.read())
        stored = {"config": dict(SETTINGS, use_lasagna=state["chk"]["use_lasagna"])}
        stored.update({k: v for k, v in state["chk"].items() if k != "use_lasagna"})
        return Model(), dict(SETTINGS), stored

    def dataset(config):
        calls["dataset"].append(
            {key: getattr(config, key) for key in [*SETTINGS, "use_lasagna"]}
        )
        return object()

    def collect(model, ds, num_layers, device, batch_size, amp_enabled, probabilities, protocol):  # fmt: skip
        calls["collect"].append({"protocol": protocol, "amp": amp_enabled})
        # The checkpoint's own input check: its two channels pass, one does not.
        out = probabilities(model, torch.rand(1, 2, num_layers, SIZE, SIZE))
        assert out.shape == (1, 1, SIZE, SIZE)
        with pytest.raises(ValueError, match="input must be"):
            probabilities(model, torch.rand(1, 1, num_layers, SIZE, SIZE))
        probs, targets = _patches(3)
        empty = torch.zeros(1, 1, SIZE, SIZE)
        diag = {
            "complete": state["complete"],
            "batch_errors": 1,
            "inputs_sha256": state["diag_inputs"],
        }
        return probs + [empty], targets + [empty], diag

    def threshold(p, t):
        calls["threshold"].append(len(p))
        return 0.3, 0.6

    real_topo = dtp.topo_metrics

    def topo(probs, targets, thr, ms):
        calls["topo"].append(len(probs))
        return real_topo(probs, targets, thr, ms)

    monkeypatch.setattr(dtp, "require_villa_metrics", lambda: calls["villa"].append(1))
    monkeypatch.setattr(dtp, "load_tool_checkpoint", load)
    monkeypatch.setattr(dtp, "build_validation_dataset", dataset)
    monkeypatch.setattr(dtp, "collect_validation_predictions", collect)
    monkeypatch.setattr(dtp, "validation_protocol", lambda band: state["protocol"])
    monkeypatch.setattr(
        dtp, "validation_inputs_fingerprint", lambda uri, band: state["inputs"]
    )
    monkeypatch.setattr(dtp, "select_topology_threshold", threshold)
    monkeypatch.setattr(dtp, "topo_metrics", topo)
    monkeypatch.setattr(dtp, "compute_skeleton_dist", lambda g, p, **k: 1.5)
    monkeypatch.setattr(
        dtp, "compute_centerline_dice", lambda g, p, **k: {"centerline_dice": 0.5}
    )
    monkeypatch.setattr(dtp, "compute_cc_diff", lambda g, p: 0)
    cache = tmp_path / "cache.pt"

    def main(*extra, cache_path=cache):
        argv = ["--checkpoint", str(checkpoint), "--cache", str(cache_path), *extra]
        assert dtp.main(argv) == 0
        return capsys.readouterr().out

    return main, calls, state, checkpoint, cache


def test_it_scores_the_checkpoint_with_its_own_recipe_on_the_protocol(run):
    main, calls, state, checkpoint, cache = run
    out = main()
    assert calls["villa"] == [
        1
    ]  # villa's metrics are required before anything is scored
    assert calls["load"] == [b"weights v1"]
    # The dataset is built for the checkpoint's recipe and recorded inputs, not config.json's or the defaults.
    assert calls["dataset"] == [dict(SETTINGS, use_lasagna=True)]
    # The loop's protocol, in fp32 as the loop validates.
    assert calls["collect"] == [{"protocol": "protocol-a", "amp": False}]
    # Only the ink-containing patches are measured.
    assert "scored patches: 4, ink-containing: 3" in out
    assert calls["threshold"] == [3] and set(calls["topo"]) == {3}
    baseline = [line for line in out.splitlines() if "the loop's measurement" in line]
    assert len(baseline) == 1 and baseline[0].split()[:2] == ["0.300", "1"]
    assert (
        "Baseline (topology threshold 0.300, no post-processing): skel_dist=1.500, "
        "gate=2.0"
    ) in out


def test_the_stored_score_is_compared_only_on_the_same_protocol_and_inputs(run):
    main, calls, state, checkpoint, cache = run
    state["chk"].update(
        val_protocol="protocol-a",
        validation_diag={"inputs_sha256": "inputs-a"},
        avg_skel_dist=3.0,
    )
    assert "Stored avg_skel_dist=3.0, on the same protocol and inputs" in main()
    state["chk"]["validation_diag"] = {"inputs_sha256": "inputs-old"}
    out = main()
    assert "Stored avg_skel_dist=3.0 is not comparable" in out and "inputs-old" in out


def test_unwarped_scores_a_lasagna_checkpoint_without_the_warp(run):
    main, calls, state, checkpoint, cache = run
    main()
    main("--unwarped")
    assert [d["use_lasagna"] for d in calls["dataset"]] == [True, False]
    assert len(calls["collect"]) == 2  # the warp is part of the cache key


def test_the_cache_is_used_only_for_its_checkpoint_protocol_and_inputs(run):
    main, calls, state, checkpoint, cache = run
    main()
    blob = torch.load(cache, weights_only=True)
    assert blob["key"]["checkpoint_sha256"] == hashlib.sha256(b"weights v1").hexdigest()
    assert "loaded cached predictions: 4 patches" in main()
    assert len(calls["collect"]) == 1
    checkpoint.write_bytes(b"weights v2")  # a promotion
    assert "another checkpoint or validation sample" in main()
    assert len(calls["collect"]) == 2
    state["inputs"] = "inputs-b"  # other validation labels
    main()
    state["protocol"] = "protocol-b"  # another depth band
    main()
    assert len(calls["collect"]) == 4
    main("--refresh")
    assert len(calls["collect"]) == 5
    cache.write_bytes(b"not a cache")
    assert "ignoring unreadable prediction cache" in main()
    assert len(calls["collect"]) == 6


def test_an_incomplete_sample_is_neither_measured_nor_cached(run):
    main, calls, state, checkpoint, cache = run
    state["complete"] = False
    with pytest.raises(SystemExit, match="sample is incomplete"):
        main()
    assert not cache.exists()


def test_predictions_whose_inputs_differ_from_the_key_are_not_cached(run):
    main, calls, state, checkpoint, cache = run
    state["diag_inputs"] = "inputs-other"
    assert "not caching" in main()
    assert not cache.exists()


def test_a_cache_that_cannot_be_written_does_not_lose_the_run(run, tmp_path):
    main, calls, state, checkpoint, cache = run
    out = main(cache_path=tmp_path / "missing" / "cache.pt")
    assert "could not cache the predictions" in out and "Baseline" in out


def test_the_checkpoint_bytes_hashed_are_the_ones_loaded(run):
    main, calls, state, checkpoint, cache = run
    main()
    (loaded,) = calls["load"]
    key = torch.load(cache, weights_only=True)["key"]
    assert key["checkpoint_sha256"] == hashlib.sha256(loaded).hexdigest()
    assert isinstance(io.BytesIO(loaded).read(), bytes)
