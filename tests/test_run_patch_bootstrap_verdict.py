"""Tests for the verdict runner's path resolution.

The runner decides nothing; the only thing it can get wrong is which files it
hands to the analysis. The dangerous case is an ambiguous fit directory, which
arises the moment a single arm is re-run, so that is pinned hardest.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import run_patch_bootstrap_verdict as mod  # noqa: E402


def _arm(root, tag, *, dirs=1, metrics=True, sat=True):
    if metrics:
        d = root / f"outer_{tag}" / "ink_metric"
        d.mkdir(parents=True)
        (d / "metrics.json").write_text(json.dumps({"summary": {}}))
    for k in range(dirs):
        f = root / f"2026-09-0{k + 1}_s1_slice_x-patch_{tag}"
        f.mkdir()
        if sat:
            (f / "satisfaction_metrics_fitted.json").write_text(
                json.dumps({"summary": {}})
            )


def test_a_clean_arm_resolves(tmp_path):
    _arm(tmp_path, "boot090s1")
    m, s = mod.resolve(str(tmp_path), "boot090s1")
    assert m.endswith("metrics.json")
    assert s.endswith("satisfaction_metrics_fitted.json")


def test_two_fit_directories_is_refused_not_guessed(tmp_path):
    """A re-run arm leaves two directories. Picking either silently could pair
    fresh metrics with a stale satisfaction file."""
    _arm(tmp_path, "boot090s1", dirs=2)
    with pytest.raises(SystemExit) as e:
        mod.resolve(str(tmp_path), "boot090s1")
    assert "exactly one fit directory, found 2" in str(e.value)
    assert "Refusing to guess" in str(e.value)


def test_an_unscored_arm_is_named(tmp_path):
    _arm(tmp_path, "rand090s3", metrics=False)
    with pytest.raises(SystemExit) as e:
        mod.resolve(str(tmp_path), "rand090s3")
    assert "not scored yet" in str(e.value)


def test_a_missing_satisfaction_file_is_caught(tmp_path):
    _arm(tmp_path, "boot090s2", sat=False)
    with pytest.raises(SystemExit) as e:
        mod.resolve(str(tmp_path), "boot090s2")
    assert "satisfaction_metrics_fitted.json" in str(e.value)


def test_build_args_emits_one_spec_per_registered_arm(tmp_path):
    for t in mod.BOOT + mod.RAND:
        _arm(tmp_path, t)
    specs = mod.build_args(str(tmp_path))
    assert len(specs) == 6
    assert [s.split("=")[0] for s in specs] == list(mod.BOOT + mod.RAND)
    assert all("," in s for s in specs)


def test_the_registered_arm_names_match_the_analysis(tmp_path):
    import analyse_patch_bootstrap as an

    assert mod.BOOT == an.BOOTSTRAP_ARMS
    assert mod.RAND == an.RANDOM_ARMS
