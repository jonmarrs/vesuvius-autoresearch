"""Tests for scripts/measure_real_winding_nonlinearity.py.

These tests use small hand-constructed synthetic CSR ray-crossing arrays
with known answers -- they do NOT require the downloaded PHercParis4
dataset. That keeps this file fast and runnable without network access,
per the task's TDD requirement.
"""

import os
import re
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"
    ),
)

from measure_real_winding_nonlinearity import (  # noqa: E402
    _R_model,
    build_report,
    compute_gaps_and_ratios,
    equivalent_alpha,
    pct,
    sha256_of_file,
)


def _build_ray(t_values, level_values):
    """Helper: one ray's crossing_t / crossing_level arrays."""
    return np.asarray(t_values, dtype=np.float32), np.asarray(
        level_values, dtype=np.int16
    )


def _stack_rays(rays, ray_origin=None, ray_step=None, seed_winding=None):
    """Concatenate a list of (t, level) ray tuples into full CSR arrays,
    building crossing_offsets automatically. `ray_step` defaults to unit
    +x vectors (norm 1) for every ray; `seed_winding` defaults to zeros."""
    n_rays = len(rays)
    all_t = (
        np.concatenate([r[0] for r in rays]) if rays else np.array([], dtype=np.float32)
    )
    all_level = (
        np.concatenate([r[1] for r in rays]) if rays else np.array([], dtype=np.int16)
    )
    counts = [len(r[0]) for r in rays]
    offsets = np.zeros(n_rays + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)

    if ray_step is None:
        ray_step = np.tile(np.array([0.0, 0.0, 1.0], dtype=np.float32), (n_rays, 1))
    if ray_origin is None:
        ray_origin = np.zeros((n_rays, 3), dtype=np.float32)
    if seed_winding is None:
        seed_winding = np.zeros(n_rays, dtype=np.int16)

    return {
        "crossing_t": all_t,
        "crossing_level": all_level,
        "crossing_offsets": offsets,
        "ray_origin_zyx": ray_origin,
        "ray_step_zyx": ray_step,
        "seed_winding": seed_winding,
    }


# ---------------------------------------------------------------------------
# Gap / ratio computation
# ---------------------------------------------------------------------------


def test_uniform_spacing_gives_ratio_exactly_one():
    """A ray with evenly-spaced crossings at adjacent windings must give
    gap == spacing exactly, and ratio == 1.0 exactly (the task's stated
    known-answer case)."""
    ray = _build_ray([0.0, 10.0, 20.0, 30.0], [0, 1, 2, 3])
    arrays = _stack_rays([ray])  # unit step vector -> gap == t-diff exactly

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.gaps.tolist() == pytest.approx([10.0, 10.0, 10.0])
    assert result.ratios.tolist() == pytest.approx([1.0, 1.0])


def test_geometric_spacing_gives_known_constant_ratio():
    """A ray with geometrically-spaced crossings (common ratio 2) must give
    ratio == 2.0 exactly at every step."""
    # t-diffs: 10, 20, 40 -> geometric with ratio 2
    ray = _build_ray([0.0, 10.0, 30.0, 70.0], [5, 6, 7, 8])
    arrays = _stack_rays([ray])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.gaps.tolist() == pytest.approx([10.0, 20.0, 40.0])
    assert result.ratios.tolist() == pytest.approx([2.0, 2.0])


def test_gap_uses_step_norm_not_just_t_diff():
    """The gap formula is |t2-t1| * ||step||, not just |t2-t1| -- verify a
    non-unit step vector is honored."""
    ray = _build_ray([0.0, 10.0], [0, 1])
    step = np.array([[0.0, 0.0, 3.0]], dtype=np.float32)  # norm 3
    arrays = _stack_rays([ray], ray_step=step)

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.gaps.tolist() == pytest.approx([30.0])


def test_level_skip_excludes_the_pair_and_breaks_the_ratio_chain():
    """A level skip (diff != 1) must exclude that ONE pair from gaps, and
    must ALSO exclude both ratios that would have referenced it -- even
    though the two flanking pairs are themselves individually valid.
    ray: t=[0,10,25,35], level=[0,1,3,4]
      pair(0,1): level diff 1 -> valid gap = 10
      pair(1,2): level diff 2 -> EXCLUDED (not adjacent)
      pair(2,3): level diff 1 -> valid gap = 10
    Expected: 2 valid gaps (10, 10), 0 valid ratios (no two ADJACENT valid
    gaps exist -- the excluded pair sits between them), 1 excluded pair.
    """
    ray = _build_ray([0.0, 10.0, 25.0, 35.0], [0, 1, 3, 4])
    arrays = _stack_rays([ray])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.gaps.tolist() == pytest.approx([10.0, 10.0])
    assert result.ratios.tolist() == []
    assert result.counts["excluded_nonadjacent_level_pairs"] == 1
    assert result.counts["n_gaps_valid"] == 2
    assert result.counts["n_ratios_valid"] == 0


def test_gaps_never_cross_a_ray_boundary():
    """Two rays back-to-back in the CSR arrays must never produce a gap or
    ratio spanning the boundary between them, even if the second ray's
    first level continues numerically from the first ray's last level."""
    ray_a = _build_ray([0.0, 10.0], [0, 1])
    ray_b = _build_ray(
        [0.0, 10.0, 20.0], [2, 3, 4]
    )  # levels continue 2,3,4 -- must NOT bridge
    arrays = _stack_rays([ray_a, ray_b])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    # ray_a: 1 gap (10). ray_b: 2 gaps (10, 10), 1 ratio (1.0). No 3rd gap
    # or bridging ratio from ray_a's last crossing to ray_b's first.
    assert result.gaps.tolist() == pytest.approx([10.0, 10.0, 10.0])
    assert len(result.ratios) == 1
    assert result.ratios.tolist() == pytest.approx([1.0])
    assert result.gap_ray_index.tolist() == [0, 1, 1]


def test_rays_with_fewer_than_2_crossings_yield_no_gaps():
    ray_a = _build_ray([0.0], [0])  # 1 crossing
    ray_b = _build_ray([0.0, 10.0], [0, 1])  # 2 crossings -> 1 gap, 0 ratios
    arrays = _stack_rays([ray_a, ray_b])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.counts["n_rays_lt2_crossings"] == 1
    assert result.counts["n_rays_lt3_crossings"] == 2
    assert len(result.gaps) == 1
    assert len(result.ratios) == 0


def test_degenerate_zero_length_step_excludes_the_whole_ray():
    ray_a = _build_ray([0.0, 10.0, 20.0], [0, 1, 2])
    ray_b = _build_ray([0.0, 10.0, 20.0], [0, 1, 2])
    step = np.array(
        [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32
    )  # ray_a degenerate, ray_b fine
    arrays = _stack_rays([ray_a, ray_b], ray_step=step)

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.counts["n_rays_degenerate_step"] == 1
    assert result.gaps.tolist() == pytest.approx([10.0, 10.0])
    assert result.gap_ray_index.tolist() == [1, 1]


def test_out_of_order_t_is_sorted_before_pairing():
    """If a ray's crossings are not already stored in ascending-t order,
    the computation must sort by t within the ray before treating array
    neighbors as physically adjacent."""
    ray = _build_ray([20.0, 0.0, 10.0], [2, 0, 1])  # scrambled order
    arrays = _stack_rays([ray])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.gaps.tolist() == pytest.approx([10.0, 10.0])
    assert result.ratios.tolist() == pytest.approx([1.0])


def test_duplicate_t_is_excluded_as_degenerate():
    ray = _build_ray([0.0, 10.0, 10.0, 20.0], [0, 1, 2, 3])
    arrays = _stack_rays([ray])

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    assert result.counts["excluded_degenerate_t_pairs"] == 1
    assert result.gaps.tolist() == pytest.approx([10.0, 10.0])


def test_anchor_winding_uses_seed_winding_plus_level():
    """gap_anchor_winding / ratio_anchor_winding must equal
    seed_winding[ray] + level of the LOWER-level crossing of the pair --
    this is the verified relationship the equivalent-alpha derivation
    depends on."""
    ray = _build_ray([0.0, 10.0, 20.0], [-2, -1, 0])
    seed_winding = np.array([25], dtype=np.int16)
    arrays = _stack_rays([ray], seed_winding=seed_winding)

    result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )

    # crossings at absolute windings 23, 24, 25 -> gap anchors 23, 24
    assert result.gap_anchor_winding.tolist() == [23, 24]
    assert result.ratio_anchor_winding.tolist() == [23]


# ---------------------------------------------------------------------------
# Equivalent alpha
# ---------------------------------------------------------------------------


def test_R_model_is_exactly_one_at_alpha_one_for_any_n0():
    """Algebraic identity from the derivation: a linear spiral (alpha=1)
    gives ratio exactly 1 regardless of the anchor winding number."""
    for n0 in [1.0, 10.0, 50.0, 127.0]:
        r = _R_model(np.array([1.0]), np.array([n0]))
        assert r[0] == pytest.approx(1.0, abs=1e-9)


def test_equivalent_alpha_round_trips_a_known_alpha():
    """The strongest correctness test for the inversion: pick a known
    alpha and n0, compute the forward ratio R(alpha, n0) algebraically,
    feed it through `equivalent_alpha`, and confirm the recovered alpha
    matches the one we started with."""
    for true_alpha, n0 in [(0.6, 25.0), (0.2, 50.0), (2.0, 80.0), (0.95, 10.0)]:
        r_obs = _R_model(np.array([true_alpha]), np.array([n0]))
        result = equivalent_alpha(
            ratios=r_obs,
            anchor_winding=np.array([n0]),
            ray_index=np.array([0]),
        )
        assert result.counts["n_resolved"] == 1
        assert result.alpha[0] == pytest.approx(true_alpha, rel=1e-4)


def test_equivalent_alpha_at_ratio_one_is_one():
    result = equivalent_alpha(
        ratios=np.array([1.0, 1.0, 1.0]),
        anchor_winding=np.array([10.0, 50.0, 127.0]),
        ray_index=np.array([0, 1, 2]),
    )
    assert result.alpha == pytest.approx([1.0, 1.0, 1.0], abs=1e-4)


def test_equivalent_alpha_excludes_nonpositive_anchor_winding():
    result = equivalent_alpha(
        ratios=np.array([1.0, 1.0]),
        anchor_winding=np.array([-3.0, 0.0]),
        ray_index=np.array([0, 1]),
    )
    assert result.counts["excluded_nonpositive_anchor_winding"] == 2
    assert result.counts["n_resolved"] == 0
    assert len(result.alpha) == 0


def test_equivalent_alpha_excludes_out_of_bracket_ratio():
    """A ratio far outside anything achievable within the bracket (e.g. an
    absurdly large ratio implying alpha << lo) must be reported as
    unresolved, not silently clipped to the bracket edge."""
    result = equivalent_alpha(
        ratios=np.array([1e6]),
        anchor_winding=np.array([50.0]),
        ray_index=np.array([0]),
        lo=0.5,
        hi=2.0,
    )
    assert result.counts["excluded_ratio_out_of_bracket_range"] == 1
    assert result.counts["n_resolved"] == 0


def test_equivalent_alpha_splits_above_ceiling_and_below_floor():
    """A too-large ratio (needs alpha < lo) and a too-small ratio (needs
    alpha > hi, i.e. below the achievable floor) must land in the correct,
    distinct diagnostic buckets."""
    n0 = 50.0
    floor = float(_R_model(np.array([2.0]), np.array([n0]))[0])  # R at alpha=hi=2.0
    ceiling = float(_R_model(np.array([0.5]), np.array([n0]))[0])  # R at alpha=lo=0.5
    result = equivalent_alpha(
        ratios=np.array([floor - 0.01, ceiling + 0.01]),
        anchor_winding=np.array([n0, n0]),
        ray_index=np.array([0, 1]),
        lo=0.5,
        hi=2.0,
    )
    assert result.counts["excluded_below_floor"] == 1
    assert result.counts["excluded_above_ceiling"] == 1
    assert result.counts["n_resolved"] == 0


# ---------------------------------------------------------------------------
# sha256 verification helper
# ---------------------------------------------------------------------------


def test_sha256_of_file_matches_known_hash(tmp_path):
    p = tmp_path / "sample.bin"
    p.write_bytes(b"hello winding data")
    import hashlib

    expected = hashlib.sha256(b"hello winding data").hexdigest()
    assert sha256_of_file(str(p)) == expected


def test_sha256_of_file_detects_mismatch(tmp_path):
    p = tmp_path / "sample.bin"
    p.write_bytes(b"hello winding data")
    assert sha256_of_file(str(p)) != "0" * 64


# ---------------------------------------------------------------------------
# Report narrative <-> counts-dict consistency (regression coverage for the
# class of bug where a percentage in prose is hand-typed instead of computed
# from the same counts dict a table above it reports, and silently drifts
# out of sync on a rerun)
# ---------------------------------------------------------------------------


def test_pct_helper_matches_manual_division():
    assert pct(1, 4) == pytest.approx(25.0)
    assert pct(0, 5) == pytest.approx(0.0)
    import math

    assert math.isnan(pct(3, 0))


def test_narrative_below_floor_percentage_matches_the_counts_it_quotes():
    """Regression test for the class of bug where a narrative percentage is
    hand-typed instead of computed from the same counts dict the Exclusions
    table above it reports. Builds a small synthetic multi-ray scenario
    engineered to produce a non-round below-floor percentage (so a stale
    hardcoded value from an earlier draft could not coincidentally match),
    then parses BOTH the quoted percentage and the two counts it is derived
    from directly out of the RENDERED REPORT TEXT (not the Python objects
    that produced it), and asserts they agree -- exactly what a reviewer
    reading only the .txt file would do."""
    rng = np.random.default_rng(7)
    rays = []
    seeds = []
    for i in range(40):
        n_crossings = 6
        gaps = rng.uniform(
            2.0, 60.0, size=n_crossings - 1
        )  # irregular -> some extreme ratios
        t = np.concatenate([[0.0], np.cumsum(gaps)]).astype(np.float32)
        level = np.arange(n_crossings, dtype=np.int16)
        rays.append((t, level))
        seeds.append(20 + i)  # moderate-to-large absolute winding numbers

    arrays = _stack_rays(rays, seed_winding=np.array(seeds, dtype=np.int16))
    gap_result = compute_gaps_and_ratios(
        arrays["crossing_t"],
        arrays["crossing_level"],
        arrays["crossing_offsets"],
        arrays["ray_step_zyx"],
        arrays["seed_winding"],
    )
    alpha_result = equivalent_alpha(
        gap_result.ratios, gap_result.ratio_anchor_winding, gap_result.ratio_ray_index
    )
    shard_results = [
        {"shard": "shard_test", "gap_result": gap_result, "alpha_result": alpha_result}
    ]

    report = build_report(shard_results)

    below_floor = int(
        re.search(r"excluded_below_floor\s+([\d,]+)", report).group(1).replace(",", "")
    )
    out_of_bracket = int(
        re.search(r"excluded_ratio_out_of_bracket_range\s+([\d,]+)", report)
        .group(1)
        .replace(",", "")
    )
    assert out_of_bracket > 0, "test scenario must actually produce unresolved ratios"
    expected_pct = pct(below_floor, out_of_bracket)

    quoted = re.search(
        r"and ([\d.]+)% of the ([\d,]+) "
        r"unresolvable ratios are BELOW the model's floor",
        report,
    )
    assert quoted is not None, (
        "PLAIN READING paragraph's below-floor sentence not found"
    )
    quoted_pct = float(quoted.group(1))
    quoted_count = int(quoted.group(2).replace(",", ""))

    assert quoted_count == out_of_bracket
    assert quoted_pct == pytest.approx(expected_pct, abs=0.05)
