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


def _stub_metrics(monkeypatch):
    monkeypatch.setattr(
        pge, "_centerline_dice", lambda label, pred, **k: {"centerline_dice": 0.5}
    )
    monkeypatch.setattr(pge, "_skel_dist", lambda label, pred, **k: 3.0)


def test_a_label_without_ink_inside_the_mask_is_refused(monkeypatch):
    """Villa's centerline_dice scores any prediction about 2 against a label with no
    skeleton, and the sweep reported the largest as topology-optimal."""
    import pytest

    _stub_metrics(monkeypatch)
    prob = np.full((32, 32), 0.9, np.float32)
    mask = np.ones((32, 32), bool)
    with pytest.raises(pge.InkFreeLabel, match="no ink inside the mask"):
        pge.sweep_topology(prob, np.zeros((32, 32), np.uint8), mask, [0.5])
    label = np.zeros((32, 32), np.uint8)
    label[2:4, 2:20] = 1
    mask[:8] = False  # the only ink lies outside the mask
    with pytest.raises(pge.InkFreeLabel, match="no ink inside the mask"):
        pge.sweep_topology(prob, label, mask, [0.5])
    # The check is on the label villa is given, after its conversion to uint8.
    wide = np.zeros((32, 32), np.uint16)
    wide[10:12, 2:20] = 256
    with pytest.raises(pge.InkFreeLabel, match="no ink inside the mask"):
        pge.sweep_topology(prob, wide, np.ones((32, 32), bool), [0.5])


def _main_args(tmp_path, monkeypatch, label):
    import sys

    monkeypatch.setattr(pge, "_ensure_wandb_disabled", lambda: None)
    Image.fromarray(np.full((16, 16), 200, np.uint8)).save(tmp_path / "pred.png")
    Image.fromarray(label).save(tmp_path / "ink.png")
    out = tmp_path / "card.json"
    argv = [
        "pge",
        "--pred",
        str(tmp_path / "pred.png"),
        "--label",
        str(tmp_path / "ink.png"),
    ]
    monkeypatch.setattr(sys, "argv", argv + ["--out", str(out)])
    return out


def test_main_exits_with_the_reason_for_an_ink_free_label(tmp_path, monkeypatch):
    import pytest

    _stub_metrics(monkeypatch)
    out = _main_args(tmp_path, monkeypatch, np.zeros((16, 16), np.uint8))
    with pytest.raises(
        SystemExit, match=r"ink\.png: the label has no ink inside the mask"
    ):
        pge.main()
    assert not out.exists()


def test_main_does_not_report_other_errors_as_an_ink_free_label(tmp_path, monkeypatch):
    import pytest

    def failing(label, pred, **k):
        raise ValueError("inside the metric")

    monkeypatch.setattr(pge, "_centerline_dice", failing)
    label = np.zeros((16, 16), np.uint8)
    label[4:6, 2:14] = 255
    _main_args(tmp_path, monkeypatch, label)
    with pytest.raises(ValueError, match="inside the metric"):
        pge.main()
