"""Tests for the full-band chunk stitcher (merged-1667 column baselines)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repro.sota_data.merged_fullband_score import chunk_trims, stitch


def test_chunk_trims_cover_width_contiguously():
    specs = [(0, 3800), (3544, 3800), (7088, 3800), (10632, 3800)]
    total_w = 10632 + 3800
    trims = chunk_trims(specs, overlap=256)
    # each entry: (x0, left_trim, right_trim); assembled spans must tile exactly
    spans = [
        (x0 + lt, x0 + w - rt)
        for (x0, w), (x0b, lt, rt) in zip(specs, trims, strict=False)
    ]
    assert spans[0][0] == 0 and spans[-1][1] == total_w
    for (a0, a1), (b0, b1) in zip(spans, spans[1:], strict=False):
        assert a1 == b0  # contiguous, no gap, no double-cover


def test_stitch_assembles_known_values_with_seams_in_overlap_middles():
    specs = [(0, 40), (32, 40), (64, 30)]  # overlap 8, total width 94
    H = 6
    preds = {}
    for i, (x0, w) in enumerate(specs):
        preds[x0] = np.full((H, w), float(i), np.float32)
    full = stitch(preds, specs, overlap=8, total_w=94)
    assert full.shape == (6, 94)
    # seams at x0+overlap/2 of each junction: 32+4=36, 64+4=68
    assert (full[:, :36] == 0).all()
    assert (full[:, 36:68] == 1).all()
    assert (full[:, 68:] == 2).all()
    assert np.isfinite(full).all()


def test_stitch_refuses_missing_chunk():
    specs = [(0, 40), (32, 40)]
    with pytest.raises(ValueError, match="missing"):
        stitch({0: np.zeros((4, 40), np.float32)}, specs, overlap=8, total_w=72)


def test_stitch_refuses_wrong_chunk_shape():
    specs = [(0, 40), (32, 40)]
    preds = {0: np.zeros((4, 40), np.float32), 32: np.zeros((4, 39), np.float32)}
    with pytest.raises(ValueError, match="shape"):
        stitch(preds, specs, overlap=8, total_w=72)
