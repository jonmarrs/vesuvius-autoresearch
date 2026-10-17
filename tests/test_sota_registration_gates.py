"""The registration gates fail closed: a score needs the validation that passed on exactly
the label, stats and teacher it scores, on thresholds no looser than the target's, from a
segment that is not retired."""

import json
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.register import placement_peak


@pytest.fixture
def modules(monkeypatch):
    """register_run and gt_finetune, importable without s3fs (a stand-in when absent)."""
    import importlib
    import types

    names = (
        "repro.sota_data.gt_finetune",
        "repro.sota_data.gt_register",
        "repro.sota_data.register_run",
        "repro.sota_data.distill_run",
    )
    try:
        import s3fs  # noqa: F401

        fresh = False
    except ImportError:
        monkeypatch.setitem(sys.modules, "s3fs", types.ModuleType("s3fs"))
        for name in names:
            monkeypatch.delitem(sys.modules, name, raising=False)
        fresh = True
    rr = importlib.import_module("repro.sota_data.register_run")
    ft = importlib.import_module("repro.sota_data.gt_finetune")
    yield rr, ft
    if fresh:  # leave no module bound to the stand-in
        package = sys.modules["repro.sota_data"]
        for name in names:
            sys.modules.pop(name, None)
            if hasattr(package, name.rsplit(".", 1)[1]):
                delattr(package, name.rsplit(".", 1)[1])


def _text_lines(h=640, w=640, pitch=64, seed=0):
    """Rows of word-like strokes: periodic at the line pitch, as registered text is."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w), np.uint8)
    for top in range(40, h - 60, pitch):
        x = 30
        while x < w - 60:
            length = int(rng.integers(20, 60))
            img[top : top + 22, x : x + length] = 255
            x += length + int(rng.integers(10, 30))
    return img


def test_placement_without_any_scored_window_is_not_zero():
    """A landscape with nothing to score returned (0, 0), which every gate passes."""
    flat = np.full((240, 240), 255, np.uint8)  # every shift ties: no peak
    with pytest.raises(ValueError, match="search boundary"):
        placement_peak(flat, flat, max_shift=32)
    border = np.zeros((240, 240), np.uint8)
    border[:4] = 255  # ink only outside every comparison window
    with pytest.raises(ValueError):
        placement_peak(border, border, max_shift=32)
    dy, dx, _, _ = placement_peak(flat, flat, max_shift=32, strict=False)
    assert max(abs(dy), abs(dx)) >= 32  # the probes read the clamp instead


@pytest.fixture
def heldout(tmp_path, monkeypatch, modules):
    """The held-out target's files, synthetic and correctly registered."""
    rr, _ = modules
    rr._set_target("heldout")
    reg_dir = tmp_path / "reg"
    frag_root = tmp_path / "frags"
    frag = frag_root / rr.FRAG_ID
    os.makedirs(reg_dir)
    os.makedirs(frag / "layers")
    for name, value in (
        ("REG_DIR", str(reg_dir)),
        ("MARKER", str(reg_dir / "VALIDATED")),
        ("REG_LABEL", str(reg_dir / "registered_label_l2region.png")),
        ("REG_STATS", str(reg_dir / "registration_stats.json")),
        ("XSCROLL_ROOT", str(frag_root)),
    ):
        monkeypatch.setattr(rr, name, value)
    label = _text_lines()
    cv2.imwrite(rr.REG_LABEL, label)
    cv2.imwrite(str(frag / f"{rr.FRAG_ID}_inklabels.png"), label)  # the teacher
    surface = np.full(label.shape, 100, np.uint8)
    cv2.imwrite(str(frag / "layers" / "30.tif"), surface)
    cv2.imwrite(str(reg_dir / "registered_oldsurface_l2region.png"), surface)
    with open(rr.REG_STATS, "w") as f:
        json.dump({"method": "synthetic", "region_median_residual": 5.0}, f)
    return rr


def _stats(rr):
    with open(rr.REG_STATS) as f:
        return json.load(f)


def test_a_passing_validation_vouches_for_exactly_what_it_saw(heldout):
    rr = heldout
    rr.cmd_validate([])
    assert _stats(rr)["gate"]["passed"]
    rr._check_marker(_stats(rr))  # scoring may proceed
    # warp writes a new label: the old marker no longer vouches for it
    cv2.imwrite(rr.REG_LABEL, np.roll(_text_lines(), 7, 1))
    with pytest.raises(ValueError, match="changed since validation"):
        rr._check_marker(_stats(rr))


def test_a_failed_or_crashed_validation_leaves_no_marker(heldout):
    """A failing run removed the marker, but a crash kept the last run's."""
    rr = heldout
    rr.cmd_validate([])
    assert os.path.exists(rr.MARKER)
    os.remove(os.path.join(rr.REG_DIR, "registered_oldsurface_l2region.png"))
    with pytest.raises(ValueError, match="missing"):
        rr.cmd_validate([])
    assert not os.path.exists(rr.MARKER)
    with pytest.raises(ValueError, match="not validated"):
        rr._check_marker(_stats(rr))


def test_an_old_text_marker_is_not_trusted(heldout):
    rr = heldout
    rr.cmd_validate([])
    with open(rr.MARKER, "w") as f:
        f.write("validated (teacher_free)\n")  # the format before 2026-10-16
    with pytest.raises(ValueError, match="predates hashed markers"):
        rr._check_marker(_stats(rr))


@pytest.mark.parametrize(
    "argv",
    [
        ["--max-placement-offset", "1000"],
        ["--min-periodicity", "0.1"],
        ["--max-median-residual", "50"],
    ],
)
def test_thresholds_cannot_be_loosened_from_the_command_line(heldout, argv):
    """Enrichment and periodicity defaulted to 0 (off), and placement could be raised."""
    with pytest.raises(ValueError, match="looser than this target's"):
        heldout.cmd_validate(argv)


def test_the_targets_thresholds_apply_by_default(heldout):
    rr = heldout
    rr.cmd_validate([])
    gate = _stats(rr)["gate"]
    assert gate["min_periodicity"] == 0.6 and gate["max_median_residual"] == 12.0
    assert _stats(rr)["placement"]["max_offset"] == rr.MAX_PLACEMENT_OFFSET_L2PX


def test_a_retired_segment_is_not_validated_or_scored(modules, monkeypatch):
    rr, _ = modules
    rr._set_target("orig")  # 20230702185753, retired 2026-08-14
    for command in (rr.cmd_validate, rr.cmd_score, rr.cmd_warp_obj):
        with pytest.raises(ValueError, match="retired non-scoring"):
            command()


def test_fine_tuning_rechecks_every_kept_region(modules):
    """The 2026-07 prep record kept all four regions, with no placement check; fed to
    cmd_finetune it reached training on displaced labels."""
    _, ft = modules
    with open("reports/detector/gt_finetune_heldout.json") as f:
        july = json.load(f)["prep"]
    kept, refused = ft.verified_kept(july)
    assert kept == []
    assert refused == {
        "20230702185753_y4000_x2500": "a retired segment",
        "20230702185753_y7000_x4000": "a retired segment",
        "20231005123336_y4000_x2500": "placement not verified",
        "20231005123336_y7000_x4000": "placement not verified",
    }
    good = {
        "frag_id": "seg_y0_x0",
        "passed": True,
        "placement_verified": True,
        "placement_offset_level2_px": 30.0,
    }
    far = {**good, "frag_id": "far_y0_x0", "placement_offset_level2_px": 57.5}
    held = {**good, "frag_id": "20231210121321_y0_x0"}
    record = {
        "regions": [good, far, held],
        "kept": ["seg_y0_x0", "far_y0_x0", "20231210121321_y0_x0"],
    }
    kept, refused = ft.verified_kept(record)
    assert kept == ["seg_y0_x0"]
    assert refused["far_y0_x0"].startswith("placement 57.5 px")
    assert refused["20231210121321_y0_x0"] == "the held-out evaluation segment"


def test_a_peak_that_scores_nothing_is_not_zero_offset():
    """Ink only in rows the comparison windows never see: every shift was unscored, and
    the initial (0, 0) came back with a Dice of -1, which the gate read as a pass."""
    from repro.sota_data.register import PlacementNotLocated

    edge = np.zeros((240, 240), np.uint8)
    edge[1:3] = 255
    with pytest.raises(PlacementNotLocated):
        placement_peak(edge, edge, max_shift=32)


def test_the_target_is_read_wherever_allow_retired_is_placed(modules):
    """Before the key, the flag made the key look like an option: orig ran instead."""
    rr, _ = modules
    for argv in (
        ["p", "score", "--allow-retired", "heldout"],
        ["p", "score", "heldout", "--allow-retired"],
    ):
        assert rr._parse_cli(argv) == ("score", "heldout", True, ["p", "score"])
    assert rr._parse_cli(
        ["p", "validate", "heldout", "--max-median-residual", "10"]
    ) == (
        "validate",
        "heldout",
        False,
        ["p", "validate", "--max-median-residual", "10"],
    )
