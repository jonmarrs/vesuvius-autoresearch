import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data.gt_register import parse_obj_vt, register_label_to_region


def test_parse_obj_vt_positional(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nvt 10 20\nv 4 5 6\nvt 30 40\nf 1/1 2/2\n")
    v, vt = parse_obj_vt(p)
    assert v.shape == (2, 3) and vt.shape == (2, 2)
    assert np.allclose(v[1], [4, 5, 6]) and np.allclose(vt[0], [10, 20])


def test_parse_obj_vt_mismatch_raises(tmp_path):
    p = str(tmp_path / "m.obj")
    with open(p, "w") as f:
        f.write("v 1 2 3\nv 4 5 6\nvt 10 20\n")
    with pytest.raises(ValueError, match="mismatch"):
        parse_obj_vt(p)


def test_register_label_to_region_recovers_block():
    # synthetic: region grid maps 1:1 to obj vertices; label is a block.
    h = w = 40
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    region_xyz = np.stack([xx, yy, np.zeros_like(xx)], axis=-1)  # (h,w,3)
    obj_v = region_xyz.reshape(-1, 3)  # vertices = region pts
    H = W = 40
    # vt with row=H-v,col=u convention: choose vt so that vertex at (r,c) -> label (r,c)
    # label pixel (row,col) = (H - vt_v, vt_u). Want that to equal (r,c) for grid pixel r,c
    # so vt_u = c, vt_v = H - r.
    vt = np.stack([xx.reshape(-1), (H - yy).reshape(-1)], axis=1)  # (u, v)
    old_label = np.zeros((H, W), np.uint8)
    old_label[10:25, 12:30] = 255
    reg, residual, period = register_label_to_region(
        region_xyz, obj_v, vt, old_label, size=40
    )
    assert residual < 1e-3
    inter = np.logical_and(reg > 127, old_label > 127).sum()
    union = np.logical_or(reg > 127, old_label > 127).sum()
    assert inter / union > 0.9
    assert 0.0 <= period <= 1.0


# --- placement gating on the TRAINING path (2026-08-14) --------------------------------
# gt_prep_fragment gated only on residual + periodicity, both of which are blind to a
# bodily displaced label. That is how the GT fine-tune trained on labels carrying a 167%
# scale error. See reports/detector/registration_offset_2026-08-07.md.


def test_teacher_lookup_never_returns_the_registered_gt_itself(tmp_path, monkeypatch):
    """local_data/sota_gt/<frag> holds the GT, not the teacher.

    Comparing the GT against it scores a perfect placement and would wave every region
    through. This exact confusion cost a measurement earlier in the investigation, so the
    lookup must never resolve to that root even when it is the only thing present.
    """
    from repro.sota_data.gt_register import _teacher_crop_for

    monkeypatch.chdir(tmp_path)
    frag = "20230702185753_y4000_x2500"
    d = tmp_path / "local_data" / "sota_gt" / frag
    d.mkdir(parents=True)
    (d / f"{frag}_inklabels.png").write_bytes(b"not-a-teacher")
    assert _teacher_crop_for(frag) is None


def test_teacher_lookup_finds_the_distill_and_xscroll_crops(tmp_path, monkeypatch):
    from repro.sota_data.gt_register import _teacher_crop_for

    monkeypatch.chdir(tmp_path)
    frag = "seg_y0_x0"
    d = tmp_path / "local_data" / "sota_distill" / frag
    d.mkdir(parents=True)
    (d / f"{frag}_inklabels.png").write_bytes(b"x")
    assert "sota_distill" in _teacher_crop_for(frag)

    frag2 = "seg2_y0_x0"
    d2 = tmp_path / "local_data" / "sota_xscroll" / f"scroll1_{frag2}"
    d2.mkdir(parents=True)
    (d2 / f"scroll1_{frag2}_inklabels.png").write_bytes(b"x")
    assert "sota_xscroll" in _teacher_crop_for(frag2)


def test_training_gate_defaults_to_the_shipping_placement_threshold():
    """The training path and the benchmark gate must not diverge on what 'placed' means."""
    import inspect

    from repro.sota_data import gt_register as gr
    from repro.sota_data.register_run import MAX_PLACEMENT_OFFSET_L2PX

    sig = inspect.signature(gr.gt_prep_fragment)
    assert "max_placement_offset" in sig.parameters
    assert sig.parameters["max_placement_offset"].default is None, (
        "default must resolve to MAX_PLACEMENT_OFFSET_L2PX at call time, not be pinned to a "
        "literal that can drift from the benchmark gate"
    )
    src = inspect.getsource(gr.gt_prep_fragment)
    assert "MAX_PLACEMENT_OFFSET_L2PX" in src
    assert MAX_PLACEMENT_OFFSET_L2PX == 48.0


def test_unverifiable_placement_drops_by_default_and_is_recorded_when_overridden():
    """No teacher crop means we cannot check placement, so the region is not usable."""
    import inspect

    from repro.sota_data import gt_register as gr

    src = inspect.getsource(gr.gt_prep_fragment)
    assert "allow_unverified_placement" in src
    assert "placement_verified" in src, (
        "an unverified region must be marked, not silently indistinguishable from a "
        "verified one"
    )


# --- fine-tune train/validate disjointness (2026-08-14) --------------------------------


def test_finetune_validation_is_disjoint_from_training():
    """gt_finetune validated on kept[0], a TRAINING region. Every other pipeline holds one out.

    Selection monitored train loss so nothing published was chosen on it, but a val metric
    measured on training data is the train-region-fit confusion this project was burned by,
    and it becomes a selection bug the moment `monitor` changes.
    """
    import inspect

    from repro.sota_data import gt_finetune as gf

    # strip comments: the fix documents the old pattern in prose, and a naive substring
    # check would trip on that explanation rather than on real code
    code = "\n".join(
        ln.split("#")[0] for ln in inspect.getsource(gf.cmd_finetune).splitlines()
    )
    assert "valid_fragment_id=kept[0]" not in code, (
        "validation set is a training region"
    )
    assert "train_ids, valid_id = kept[:-1], kept[-1]" in code


def test_finetune_refuses_a_split_too_small_to_validate():
    import inspect

    from repro.sota_data import gt_finetune as gf

    code = "\n".join(
        ln.split("#")[0] for ln in inspect.getsource(gf.cmd_finetune).splitlines()
    )
    assert "len(kept) < 2" in code, (
        "one kept region means train and validate are the same data; must refuse"
    )
