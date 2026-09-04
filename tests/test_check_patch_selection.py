"""Tests for the patch-selection verifier.

A checker that cannot fail is worthless, so every enforced invariant here has a
test that violates it and asserts the specific complaint. The area-match test is
the one that matters most: a count-matched control left the arms at 76.4% vs
70.0% of area, which would have confounded evidence quality with evidence
quantity -- the exact thing the RANDOM arm exists to rule out.
"""

import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import check_patch_selection as mod  # noqa: E402


def _reference(tmp_path, patches):
    p = tmp_path / "satisfied_fitted.json"
    p.write_text(
        json.dumps(
            {
                "patches": [
                    {"id": i, "fraction": f, "total_area": a} for i, f, a in patches
                ]
            }
        )
    )
    return str(p)


def _dataset(tmp_path, name, ids):
    d = tmp_path / name / "verified_patches"
    d.mkdir(parents=True)
    for i in ids:
        (d / i).mkdir()
    return str(tmp_path / name)


def _world(tmp_path):
    """Ten patches: five good (0.95), five poor (0.50), all equal area."""
    good = [(f"g{i}", 0.95, 100.0) for i in range(5)]
    poor = [(f"p{i}", 0.50, 100.0) for i in range(5)]
    return _reference(tmp_path, good + poor), [g[0] for g in good], [p[0] for p in poor]


def test_a_correct_build_passes(tmp_path):
    ref, good, poor = _world(tmp_path)
    boot = _dataset(tmp_path, "boot", good)
    rand = _dataset(tmp_path, "rand", good[:2] + poor[:3])  # same count, same area
    failures, s = mod.check(ref, boot, rand, 0.90)
    assert failures == [], failures
    assert s["BOOTSTRAP"]["mean"] > s["RANDOM"]["mean"]


def test_a_patch_absent_from_the_reference_is_caught(tmp_path):
    ref, good, poor = _world(tmp_path)
    boot = _dataset(tmp_path, "boot", [*good, "ghost"])
    rand = _dataset(tmp_path, "rand", good[:2] + poor[:3])
    failures, _ = mod.check(ref, boot, rand, 0.90)
    assert any("absent from the reference" in f for f in failures), failures


def test_a_below_threshold_patch_in_bootstrap_is_caught(tmp_path):
    ref, good, poor = _world(tmp_path)
    boot = _dataset(tmp_path, "boot", [*good, poor[0]])
    rand = _dataset(tmp_path, "rand", good[:2] + poor[:3])
    failures, _ = mod.check(ref, boot, rand, 0.90)
    assert any("leaked" in f for f in failures), failures


def test_an_area_mismatch_is_caught(tmp_path):
    """The count-matched control this study explicitly rejected."""
    ref, good, poor = _world(tmp_path)
    boot = _dataset(tmp_path, "boot", good)  # 500 area
    rand = _dataset(tmp_path, "rand", poor[:2])  # 200 area
    failures, _ = mod.check(ref, boot, rand, 0.90)
    assert any("NOT area-matched" in f for f in failures), failures


def test_area_matching_is_judged_on_area_not_count(tmp_path):
    """Equal counts with unequal areas must FAIL; unequal counts with equal
    areas must PASS. This is the whole amendment."""
    ref = _reference(
        tmp_path,
        [("big1", 0.95, 400.0), ("big2", 0.95, 400.0)]
        + [(f"sm{i}", 0.50, 100.0) for i in range(8)],
    )
    small = [f"sm{i}" for i in range(8)]

    equal_count = mod.check(
        ref,
        _dataset(tmp_path, "b1", ["big1", "big2"]),  # 800
        _dataset(tmp_path, "r1", small[:2]),  # 200
        0.90,
    )[0]
    assert any("NOT area-matched" in f for f in equal_count)

    equal_area = mod.check(
        ref,
        _dataset(tmp_path, "b2", ["big1", "big2"]),  # 800
        _dataset(tmp_path, "r2", small),  # 800
        0.90,
    )[0]
    assert equal_area == [], equal_area


def test_the_summary_reports_area_weighted_mean_distinctly(tmp_path):
    """Area weighting is not decorative: it changes the number when patch sizes
    differ, which is why the registration matches on area."""
    ref = _reference(tmp_path, [("a", 1.0, 1.0), ("b", 0.0, 99.0)])
    s = mod.summarise({"a", "b"}, *mod.load_reference(ref))
    assert s["mean"] == 0.5
    assert s["area_weighted_mean"] == 0.01
