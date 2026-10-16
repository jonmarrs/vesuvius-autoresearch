import os
import sys

import cv2
import numpy as np
import pytest
import tifffile

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.distill_prep import prep_distill_fragment, teacher_region_for


def test_teacher_region_for_same_scale():
    teacher = np.arange(100 * 80).reshape(100, 80).astype(np.uint8)
    out = teacher_region_for(
        teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40)
    )
    assert np.array_equal(out, teacher[10:30, 20:40])


def test_teacher_region_for_scales_box():
    # teacher at 2x the level scale: box coordinates double
    teacher = np.zeros((200, 160), np.uint8)
    teacher[20:60, 40:80] = 255
    out = teacher_region_for(
        teacher, level_shape=(100, 80), region_box=(10, 20, 30, 40)
    )
    assert out.shape == (40, 40)
    assert out.max() == 255 and out.min() == 255  # exactly the marked block


def test_prep_writes_fragment_with_teacher_label(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((64, 64), np.uint8)
    teacher[16:48, 16:48] = 200  # above threshold 128
    out = prep_distill_fragment(layers, teacher, str(tmp_path), "segT_y0_x0")
    lab = cv2.imread(os.path.join(out, "segT_y0_x0_inklabels.png"), 0)
    assert lab.shape == (64, 64)
    assert lab[32, 32] == 255 and lab[0, 0] == 0  # binarized teacher
    assert sorted(os.listdir(os.path.join(out, "layers"))) == [
        f"{i:02d}.tif" for i in range(17, 43)
    ]
    assert os.path.exists(os.path.join(out, "segT_y0_x0_mask.png"))


def test_prep_loads_via_detector(tmp_path):
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import read_image_mask

    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.full((64, 64), 200, np.uint8)
    prep_distill_fragment(layers, teacher, str(tmp_path), "segT2_y0_x0")
    cfg = DetectorConfig(data_root=str(tmp_path))
    images, mask, frag_mask = read_image_mask(cfg, "segT2_y0_x0")
    assert images.shape[2] == 26
    assert mask.max() == 1.0  # teacher-positive label present


def test_prep_teacher_shape_mismatch_raises(tmp_path):
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((200, 20), np.uint8)  # >20% off in both axes
    with pytest.raises(ValueError, match="mismatch"):
        prep_distill_fragment(layers, teacher, str(tmp_path), "segT3_y0_x0")


def test_prep_accepts_uniform_scale_teacher(tmp_path):
    # teacher at 4x the region scale (level-0 teacher for a level-2 region)
    layers = (np.random.rand(26, 64, 64) * 255).astype(np.uint8)
    teacher = np.zeros((256, 256), np.uint8)
    teacher[64:192, 64:192] = 200  # center block above threshold
    out = prep_distill_fragment(layers, teacher, str(tmp_path), "segS_y0_x0")
    lab = cv2.imread(os.path.join(out, "segS_y0_x0_inklabels.png"), 0)
    assert lab.shape == (64, 64)
    assert lab[32, 32] == 255 and lab[0, 0] == 0  # scaled + binarized correctly


def test_a_teacher_at_another_scale_per_axis_is_refused(tmp_path):
    """4x in y but 3.64x in x (a 9% short x, the size of the 2026-08-07 registration
    error) was accepted, and the crop then stretched over the region."""
    teacher = np.zeros((1020, 728), np.uint8)
    with pytest.raises(ValueError, match="mismatch"):
        teacher_region_for(teacher, level_shape=(255, 200), region_box=(0, 0, 100, 100))
    layers = np.zeros((26, 100, 100), np.uint8)
    with pytest.raises(ValueError, match="mismatch"):
        prep_distill_fragment(
            layers, np.zeros((400, 364), np.uint8), str(tmp_path), "s_y0_x0"
        )


def test_a_pyramid_levels_rounding_is_accepted():
    from repro.sota_data.distill_prep import same_integer_scale

    assert same_integer_scale((1020, 803), (255, 201))  # level 0 vs level 2, rounded
    assert same_integer_scale((64, 64), (64, 64))
    assert same_integer_scale((64, 64), (256, 256))  # either way round
    assert not same_integer_scale((1020, 728), (255, 200))


def test_prep_empty_region_raises(tmp_path):
    # A region offset outside the segment extent yields a zero-height region; that must
    # be a loud ValueError, not a ZeroDivisionError (seen live on small PHerc0172 segs).
    layers = np.zeros((26, 0, 4096), np.uint8)
    teacher = np.zeros((64, 64), np.uint8)
    with pytest.raises(ValueError, match="empty region"):
        prep_distill_fragment(layers, teacher, str(tmp_path), "segE_y9999_x0")


@pytest.fixture
def runners(monkeypatch):
    """distill_run and xscroll_run, importable without s3fs (a stand-in when absent)."""
    import importlib
    import types

    names = ("repro.sota_data.xscroll_run", "repro.sota_data.distill_run")
    try:
        import s3fs  # noqa: F401

        fresh = False
    except ImportError:
        monkeypatch.setitem(sys.modules, "s3fs", types.ModuleType("s3fs"))
        for name in names:
            monkeypatch.delitem(sys.modules, name, raising=False)
        fresh = True
    yield tuple(importlib.import_module(name) for name in reversed(names))
    if fresh:  # leave no module bound to the stand-in
        package = sys.modules["repro.sota_data"]
        for name in names:
            sys.modules.pop(name, None)
            if hasattr(package, name.rsplit(".", 1)[1]):
                delattr(package, name.rsplit(".", 1)[1])


def _stub_measure(scores):
    """_measure that scores checkpoints from ``scores`` (by basename), else 0.3."""

    def measure(ckpt, fid, data_root=None):
        f1 = scores.get(os.path.basename(ckpt), 0.3)
        metrics = {
            "val_f1": f1,
            "ap_prevalence_lift": 1.5 + f1,
            "roc_auc": 0.5 + f1 / 2,
        }
        return metrics, np.full((16, 16), f1, np.float32)

    return measure


def _fragment_label(data_root, fid):
    os.makedirs(os.path.join(data_root, fid))
    cv2.imwrite(
        os.path.join(data_root, fid, f"{fid}_inklabels.png"),
        np.zeros((16, 16), np.uint8),
    )


def test_the_selection_note_names_epoch_selection(runners):
    """It said AP and roc_auc were unaffected; epoch selection affects every column."""
    distill_run, _ = runners
    note = distill_run.selection_note(12)
    assert "best of 12 epochs" in note and "AP and roc_auc included" in note
    assert "The last-epoch row follows a fixed rule" in note
    assert "unaffected" not in note


def test_a_fetched_teacher_records_its_bucket_file(tmp_path, monkeypatch, runners):
    """Provenance recorded the teacher's pixels but not which released file it was."""
    distill_run, _ = runners

    class Bucket:
        def ls(self, prefix, detail=False):
            return [f"{prefix}/b_pred.tif", f"{prefix}/a_pred.tif", f"{prefix}/x.txt"]

        def get(self, src, dst):
            tifffile.imwrite(dst, np.full((8, 8), 200, np.uint8))

    monkeypatch.setattr(distill_run, "TEACHER_DIR", str(tmp_path))
    monkeypatch.setattr(distill_run, "_fs", Bucket)
    path = distill_run.fetch_teacher("seg1")
    record = distill_run.teacher_provenance(path, tifffile.imread(path))
    assert record["source"].endswith("/a_pred.tif")
    assert len(record["candidates"]) == 2
    line = distill_run.provenance_line(
        {"binarize_threshold": 128, "teachers": {"seg1": record}}
    )
    assert "a_pred.tif" in line
    # A teacher cached before sources were recorded claims none.
    os.remove(path + ".source.json")
    assert distill_run.teacher_provenance(path, tifffile.imread(path))["source"] is None


def test_the_distillation_report_states_how_the_student_was_selected(
    tmp_path, monkeypatch, runners
):
    """The caveat was printed only beside teacher provenance, and said too little."""
    import json

    distill_run, _ = runners
    monkeypatch.chdir(tmp_path)
    fid = distill_run.frag_id(distill_run.HELD_SEG, *distill_run.HELD_REGION)
    _fragment_label(distill_run.DATA_ROOT, fid)
    os.makedirs(distill_run.MODEL_DIR)
    for epoch in (1, 2, 3):
        open(
            os.path.join(distill_run.MODEL_DIR, f"detector_epoch={epoch}.ckpt"), "w"
        ).close()
    os.makedirs("reports/detector")
    with open(distill_run.BASELINE_JSON, "w") as f:
        json.dump({"vs_teacher": {"val_f1": 0.37}}, f)
    monkeypatch.setattr(
        distill_run, "_measure", _stub_measure({"detector_epoch=2.ckpt": 0.66})
    )
    distill_run.cmd_measure()  # no teacher_provenance.json
    report = open(distill_run.REPORT_MD).read()
    assert "best of 3 epochs by val_f1 on this region" in report
    # A selection-free row beside the selected one: the last epoch, a fixed rule.
    assert (
        "| distilled student, last epoch (`detector_epoch=3.ckpt`) | 0.3000" in report
    )
    record = json.load(open(distill_run.REPORT_JSON))
    assert record["selection"]["distilled"] == f"best of 3 epochs by val_f1 on {fid}"
    assert record["best_checkpoint"] == "detector_epoch=2.ckpt"
    assert sorted(record["per_epoch"]) == [
        f"detector_epoch={e}.ckpt" for e in (1, 2, 3)
    ]


def test_checkpoints_are_ordered_by_epoch_whatever_lightning_appends(tmp_path, runners):
    """detector_epoch=3-v1.ckpt made the int() sort key raise."""
    distill_run, _ = runners
    for name in (
        "detector_epoch=10.ckpt",
        "detector_epoch=3-v1.ckpt",
        "detector_epoch=2.ckpt",
        "notes.txt",
    ):
        open(tmp_path / name, "w").close()
    names = [os.path.basename(p) for p in distill_run.epoch_checkpoints(str(tmp_path))]
    assert names == [
        "detector_epoch=2.ckpt",
        "detector_epoch=3-v1.ckpt",
        "detector_epoch=10.ckpt",
    ]


def test_the_cross_scroll_report_says_which_rows_were_selected_on_it(
    tmp_path, monkeypatch, runners
):
    """A re-run wrote "diversity is the only variable" over the hand-corrected report,
    whose own caveat called arm B vs the legacy detector selection-free; but arm B's
    epoch is the one chosen on this region."""
    import json

    distill_run, xscroll_run = runners
    monkeypatch.chdir(tmp_path)
    held = xscroll_run._fid(xscroll_run.HELD)
    _fragment_label(xscroll_run.DATA_ROOT, held)
    os.makedirs(xscroll_run.MODEL_DIR)
    open(os.path.join(xscroll_run.MODEL_DIR, "detector_epoch=7.ckpt"), "w").close()
    os.makedirs("reports/detector")
    legacy = {"val_f1": 0.21, "ap_prevalence_lift": 1.47, "roc_auc": 0.591}
    with open(xscroll_run.BASELINES_JSON, "w") as f:
        json.dump(
            {
                "arms": {
                    "baseline_epoch7": {"vs_teacher": legacy},
                    "armA_scroll1_student": {"vs_teacher": legacy},
                }
            },
            f,
        )
    monkeypatch.setattr(
        distill_run, "_measure", _stub_measure({"detector_epoch=7.ckpt": 0.28})
    )
    xscroll_run.cmd_measure()
    report = open(xscroll_run.REPORT_MD).read()
    assert "only variable" not in report
    assert "needs no selection asymmetry" not in report
    assert "the selection-free comparisons are arm A vs the legacy detector" in report
    assert "| arm B, last epoch (`detector_epoch=7.ckpt`) |" in report
    assert "on that region arm A's row is optimistic" in report
    record = json.load(open(xscroll_run.REPORT_JSON))
    assert record["selection"]["armB"].startswith("best of 1 epochs by val_f1")
