"""Tests for the checkpoint pruner.

The test that earns its place is `test_a_referenced_arm_is_never_dropped`. This
project once asserted checkpoints were stale, was told to clear them, checked
first, and found every one cited by a live report. The reference check is the
whole safety property, so it is pinned directly rather than trusted.
"""

import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import prune_fit_checkpoints as mod  # noqa: E402


def _arm(spiral_out, name, size=16):
    d = spiral_out / name
    d.mkdir(parents=True)
    (d / mod.CKPT).write_bytes(b"x" * size)
    (d / "satisfaction_metrics_fitted.json").write_text("{}")
    return d


def _repo(tmp_path, mentions=()):
    r = tmp_path / "repo"
    (r / "reports").mkdir(parents=True)
    (r / "reports" / "a_report.md").write_text(
        "\n".join(f"see {m} for detail" for m in mentions) or "nothing here"
    )
    return r


def test_finds_checkpoints_and_their_sizes(tmp_path):
    so = tmp_path / "spiral_out"
    _arm(so, "2026-01-01_x-patch_alpha", size=32)
    _arm(so, "2026-01-02_x-patch_beta", size=8)
    found = mod.find_checkpoints(str(so))
    assert [f[0] for f in found] == [
        "2026-01-01_x-patch_alpha",
        "2026-01-02_x-patch_beta",
    ]
    assert [f[2] for f in found] == [32, 8]


def test_an_arm_named_in_a_report_is_referenced(tmp_path):
    repo = _repo(tmp_path, mentions=["2026-01-01_x-patch_alpha/checkpoint_fitted.ckpt"])
    ref, needle = mod.is_referenced(str(repo), "2026-01-01_x-patch_alpha")
    assert ref
    assert needle == "2026-01-01_x-patch_alpha"


def test_an_arm_referred_to_by_short_tag_alone_is_referenced(tmp_path):
    """Reports sometimes cite `baseline01`, not the full dated directory."""
    repo = _repo(tmp_path, mentions=["the baseline01 fit"])
    ref, needle = mod.is_referenced(str(repo), "2026-08-28_s1_slice-x-patch_baseline01")
    assert ref
    assert needle == "baseline01"


def test_an_unmentioned_arm_is_not_referenced(tmp_path):
    repo = _repo(tmp_path, mentions=["something else entirely"])
    ref, _ = mod.is_referenced(str(repo), "2026-01-02_x-patch_beta")
    assert not ref


def test_a_referenced_arm_is_never_dropped(tmp_path, capsys):
    """End to end: the cited checkpoint survives --delete, the other does not."""
    so = tmp_path / "spiral_out"
    keep = _arm(so, "2026-01-01_x-patch_baseline01")
    drop = _arm(so, "2026-01-02_x-patch_gap133")
    repo = _repo(tmp_path, mentions=["baseline01"])
    sys.argv = [
        "x",
        "--spiral-out",
        str(so),
        "--repo",
        str(repo),
        "--delete",
    ]
    mod.main()
    assert (keep / mod.CKPT).exists(), "a referenced checkpoint was deleted"
    assert not (drop / mod.CKPT).exists()
    assert (drop / "satisfaction_metrics_fitted.json").exists(), (
        "analysis inputs must survive; only the checkpoint is pruned"
    )


def test_dry_run_is_the_default(tmp_path):
    so = tmp_path / "spiral_out"
    a = _arm(so, "2026-01-02_x-patch_gap133")
    repo = _repo(tmp_path)
    sys.argv = ["x", "--spiral-out", str(so), "--repo", str(repo)]
    mod.main()
    assert (a / mod.CKPT).exists(), "dry run must not delete"


def test_logs_are_not_searched_for_references(tmp_path):
    """A training log naming an arm is not a dependency on its checkpoint;
    searching logs would protect everything forever and defeat the tool."""
    assert "logs" not in mod.SEARCH_SUBDIRS
    assert set(mod.SEARCH_SUBDIRS) <= {"reports", "docs", "scripts", "repro", "tests"}
