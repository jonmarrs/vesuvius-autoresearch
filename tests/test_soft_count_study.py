"""Offline tests for the soft-count study's statistics (synthetic data only)."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _mod(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


study = _mod("soft_count_study")
sums_mod = _mod("soft_count_sums")


def test_pooled_sd_is_within_group_on_the_log_scale() -> None:
    # Two groups at very different means but identical relative spread: pooling must not see the gap.
    g1 = [100.0, 110.0, 121.0]
    g2 = [1000.0, 1100.0, 1210.0]
    sd, df = study.pooled_sd([g1, g2])
    assert df == 4
    assert math.isclose(sd, math.log(1.1), rel_tol=1e-12)


def test_ratio_is_half_when_soft_spread_is_half_on_the_log_scale() -> None:
    rng = np.random.default_rng(0)
    h = [[math.exp(x) for x in rng.normal(0, 0.06, 6)] for _ in range(2)]
    s = [[math.exp(0.5 * math.log(v)) for v in g] for g in h]  # ln S = 0.5 ln H exactly
    r = study.ratio_with_ci(h, s, np.random.default_rng(1))
    assert math.isclose(r["R"], 0.5, rel_tol=1e-12)
    assert r["ci"][0] <= 0.5 + 1e-9 and r["ci"][1] >= 0.5 - 1e-9
    assert study.classify(*r["ci"], "less", "more") == "less"


def test_classify_and_d_verdict_directions() -> None:
    assert study.classify(0.5, 0.9, "better", "worse") == "better"
    assert study.classify(1.1, 1.5, "better", "worse") == "worse"
    assert study.classify(0.8, 1.2, "better", "worse") == "no detectable difference"
    assert study.d_verdict(1.0, [1.1, 1.4]) == "S discriminates better"
    assert study.d_verdict(1.0, [0.5, 0.9]) == "S discriminates worse"
    assert study.d_verdict(1.0, [0.8, 1.3]) == "no detectable difference"
    assert study.d_verdict(-0.4, [-0.6, -0.3]) == "S discriminates worse"


def test_sums_threshold_matches_villa_ge() -> None:
    p = np.array([[0.0, 0.25, 0.5, 0.75], [1.0, 0.49, 0.51, 0.5]], dtype=np.float16)
    r = sums_mod.sums(p)
    assert r["H_from_float16"] == 5  # >= 0.5, as villa's mask = fg_prob >= fg_threshold
    assert math.isclose(r["S"], float(p.astype(np.float64).sum()))
    assert math.isclose(r["S_sub_threshold"], 0.25 + float(np.float16(0.49)))
    assert r["pixels"] == 8
