import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root
from repro.sota_data import register_run as rr


def test_targets_has_both_keys():
    assert set(rr.TARGETS) == {"orig", "heldout"}
    assert rr.TARGETS["orig"]["seg"] == "20230702185753"
    assert rr.TARGETS["heldout"]["seg"] == "20231210121321"


def test_set_target_orig_keeps_slice5_paths():
    rr._set_target("orig")
    assert rr.SEG == "20230702185753"
    assert rr.REPORT_MD == "reports/detector/registered_gt_validation.md"
    assert rr.FRAG_ID == "scroll1_20230702185753_y4000_x2500"
    assert rr.XSCROLL_ROOT == "local_data/sota_xscroll"


def test_set_target_heldout_distinct():
    rr._set_target("heldout")
    assert rr.SEG == "20231210121321"
    assert rr.FRAG_ID == "20231210121321_y4000_x2500"
    assert rr.XSCROLL_ROOT == "local_data/sota_distill"
    assert rr.REPORT_MD == "reports/detector/registered_gt_heldout_validation.md"
    assert rr.OLD_ROOT.endswith("train_scrolls/20231210121321")
    assert rr.MESH_NEW.startswith("20231210121321-on-")
    assert rr.OBJ_PATH.endswith("20231210121321_original.obj")
    # per-target working dir isolates fetched meshes / outputs
    assert rr.REG_DIR == "local_data/sota_registration/heldout"
    assert os.path.join(rr.REG_DIR, "VALIDATED") == rr.MARKER
    # restore default so other tests/imports see slice-5 behavior
    rr._set_target("orig")


def test_set_target_unknown_raises():
    with pytest.raises(ValueError, match="nosuch"):
        rr._set_target("nosuch")


def test_targets_carry_prose_fields():
    for key in ("orig", "heldout"):
        t = rr.TARGETS[key]
        for f in (
            "report_title",
            "train_region_models",
            "selection_caveat_models",
            "overlay_ref",
            "extra_disclosure",
        ):
            assert f in t, f"{key} missing {f}"
    # orig: all students trained on the region; heldout: none trained, arm A selection-only
    assert set(rr.TARGETS["orig"]["train_region_models"]) == set(rr._ALL_STUDENTS)
    assert rr.TARGETS["heldout"]["train_region_models"] == []
    assert rr.TARGETS["heldout"]["selection_caveat_models"] == [
        "arm A (1-scroll student)"
    ]


def test_set_target_rebinds_prose_globals():
    rr._set_target("heldout")
    assert rr.REPORT_TITLE.startswith("Held-out")
    assert set() == rr.TRAIN_REGION_MODELS
    assert "arm A (1-scroll student)" in rr.SELECTION_CAVEAT_MODELS
    rr._set_target("orig")
    assert set(rr._ALL_STUDENTS) == rr.TRAIN_REGION_MODELS
    assert set() == rr.SELECTION_CAVEAT_MODELS


# --- regression: the hardcoded LEVEL0_SHAPE bug (2026-08-07) ---------------------------
# A single module-level LEVEL0_SHAPE pinned to 20230702185753's geometry was applied to
# every segment, displacing and stretching 20231210121321's registered label and
# manufacturing the "held-out reads at chance" result. See
# reports/detector/registration_offset_2026-08-07.md.


def test_level0_shape_is_per_segment_and_correct():
    """Shapes must differ per segment and match the bucket's surface volumes."""
    assert rr.LEVEL0_SHAPES["20230702185753"] == (50600, 36400)
    assert rr.LEVEL0_SHAPES["20231210121321"] == (51000, 39980)
    assert rr.LEVEL0_SHAPES["20230702185753"] != rr.LEVEL0_SHAPES["20231210121321"], (
        "the two segments have different geometry -- sharing one shape is the 2026-08-07 bug"
    )


def test_set_target_binds_the_matching_shape():
    for key in ("orig", "heldout"):
        rr._set_target(key)
        assert rr.LEVEL0_SHAPES[rr.SEG] == rr.LEVEL0_SHAPE, (
            f"{key}: LEVEL0_SHAPE must follow the target's segment"
        )


def test_unknown_segment_refuses_to_borrow_geometry():
    """A segment with no recorded shape must raise, never fall back to a default."""
    rr.TARGETS["_probe"] = dict(rr.TARGETS["orig"], seg="99999999999999")
    try:
        with pytest.raises(ValueError, match="no level-0 shape recorded"):
            rr._set_target("_probe")
    finally:
        del rr.TARGETS["_probe"]
        rr._set_target("orig")


def test_region_in_mesh_tracks_the_segments_own_shape():
    """The region->mesh crop must move when the segment's level-0 shape changes."""
    import numpy as np

    mesh = np.zeros((2000, 2000, 3), np.float32)
    rr._set_target("orig")
    rr.REGION_L2 = (4000, 2500, 4096)

    rr.LEVEL0_SHAPE = rr.LEVEL0_SHAPES["20230702185753"]
    a = rr._region_in_mesh(mesh).shape[:2]
    rr.LEVEL0_SHAPE = rr.LEVEL0_SHAPES["20231210121321"]
    b = rr._region_in_mesh(mesh).shape[:2]
    assert a != b, (
        "crop is insensitive to level-0 shape -- the bug would be unobservable"
    )
    rr._set_target("orig")


def test_placement_threshold_is_derived_not_convenient():
    """48 px must stay far below the bug it exists to catch, and above the measured floor.

    Raising this to accommodate a failing target is the 2026-07 failure mode; the guard is
    that the threshold keeps a wide margin against the real LEVEL0_SHAPE displacement.
    """
    thr = rr.MAX_PLACEMENT_OFFSET_L2PX
    assert 32.0 < thr < 100.0, "threshold left the band justified by the measured floor"
    bug_offset = 435.0  # measured LEVEL0_SHAPE displacement, level-2 px
    assert bug_offset / thr > 5.0, (
        "threshold too loose to catch a gross misregistration"
    )
