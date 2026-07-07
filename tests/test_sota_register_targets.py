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
    assert rr.MARKER == os.path.join(rr.REG_DIR, "VALIDATED")
    # restore default so other tests/imports see slice-5 behavior
    rr._set_target("orig")


def test_set_target_unknown_raises():
    with pytest.raises(ValueError, match="nosuch"):
        rr._set_target("nosuch")
