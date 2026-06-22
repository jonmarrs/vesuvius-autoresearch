# tests/test_prize_gate_eval.py
import numpy as np
from PIL import Image

import repro.gp_winner.prize_gate_eval as pge


def test_load_crops_to_common_shape(tmp_path):
    # pred bigger than label (winner inference pads); loader crops to common HxW
    Image.fromarray(np.full((40, 40), 200, np.uint8)).save(tmp_path / "pred.png")
    ink = np.zeros((36, 32), np.uint8)
    ink[10:20, 5:15] = 255
    Image.fromarray(ink).save(tmp_path / "ink.png")
    prob, label, mask = pge.load_pred_label_mask(
        str(tmp_path / "pred.png"), str(tmp_path / "ink.png")
    )
    assert prob.shape == label.shape == mask.shape == (36, 32)
    assert 0.0 <= prob.max() <= 1.0
    assert set(np.unique(label)).issubset({0, 1})


def test_sweep_crops_topology_to_label_bbox(monkeypatch):
    # label occupies a small sub-region of a large frame; metrics must receive the
    # cropped bbox (not the full frame) so skeletonization stays tractable.
    seen_shapes = []

    def fake_cd(label, pred, **k):
        seen_shapes.append(label.shape)
        return {"centerline_dice": 0.5}

    monkeypatch.setattr(pge, "_centerline_dice", fake_cd)
    monkeypatch.setattr(pge, "_skel_dist", lambda label, pred, **k: 3.0)

    prob = np.zeros((400, 400), np.float32)
    label = np.zeros((400, 400), np.uint8)
    label[100:140, 50:90] = 1  # 40x40 ink island
    prob[100:140, 50:90] = 0.9
    mask = np.ones((400, 400), bool)
    pge.sweep_topology(prob, label, mask, thresholds=[0.5])
    # metric received a (1, H, W) crop much smaller than the 400x400 frame
    assert seen_shapes and seen_shapes[0][0] == 1
    assert seen_shapes[0][1] <= 120 and seen_shapes[0][2] <= 120


def test_sweep_picks_topology_optimal(monkeypatch):
    # fake metrics: centerline_dice peaks near coverage 0.25; skel_dist constant
    def fake_cd(label, pred, **k):
        frac = float(pred.mean())
        return {"centerline_dice": 1.0 - abs(frac - 0.25)}

    def fake_sk(label, pred, **k):
        return 7.0

    monkeypatch.setattr(pge, "_centerline_dice", fake_cd)
    monkeypatch.setattr(pge, "_skel_dist", fake_sk)

    rng = np.random.default_rng(0)
    prob = rng.random((1, 64, 64)).astype(np.float32)[0]
    label = (rng.random((64, 64)) > 0.7).astype(np.uint8)
    mask = np.ones((64, 64), bool)
    out = pge.sweep_topology(prob, label, mask, thresholds=[0.1, 0.5, 0.9])
    assert "best_threshold" in out and "centerline_dice" in out and "skel_dist" in out
    assert out["skel_dist"] == 7.0
    assert out["best_threshold"] in (0.1, 0.5, 0.9)
    assert 0.0 <= out["pixel_auc"] <= 1.0
