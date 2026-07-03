import os
import sys

import pytest

sys.path.insert(0, os.path.abspath("."))  # repo root, so `repro.*` is importable
from repro.sota_data.distill_run import BUCKET, SCROLLS, _scroll_prefix, xfrag_id


def test_scroll_registry_keys():
    assert SCROLLS == {"scroll1": "PHercParis4", "pherc0139": "PHerc0139",
                       "pherc1667": "PHerc1667", "pherc0172": "PHerc0172"}


def test_scroll_prefix_builds_bucket_paths():
    assert _scroll_prefix("scroll1", "segA", "ink-detection") == \
        f"{BUCKET}/PHercParis4/segments/segA/ink-detection"
    assert _scroll_prefix("pherc0139", "segB", "surface-volumes") == \
        f"{BUCKET}/PHerc0139/segments/segB/surface-volumes"
    assert _scroll_prefix("pherc1667", "segC", "surface-volumes") == \
        f"{BUCKET}/PHerc1667/segments/segC/surface-volumes"
    assert _scroll_prefix("pherc0172", "segD", "ink-detection") == \
        f"{BUCKET}/PHerc0172/segments/segD/ink-detection"


def test_scroll_prefix_unknown_key_raises():
    with pytest.raises(ValueError, match="nosuch"):
        _scroll_prefix("nosuch", "segA", "ink-detection")


def test_xfrag_id_format():
    assert xfrag_id("pherc0139", "20250108000000-w025", 4000, 2500) == \
        "pherc0139_20250108000000-w025_y4000_x2500"
