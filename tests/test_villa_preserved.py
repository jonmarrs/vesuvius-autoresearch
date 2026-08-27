"""The preserved copies must stay byte-identical to the pin, and stay complete.

Upstream deleted these between our pin and 2026-08-26. If a future pin bump lands
and these have drifted or gone missing, the GP-winner replication stops being
reproducible and the only identified unblock path for the exhausted GT data
closes. Both are silent failures, so they are pinned here.
"""

import hashlib
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PRESERVED = REPO_ROOT / "repro" / "villa_preserved" / "ink_detection"
VILLA = REPO_ROOT / "villa"
PIN = "ced62390e"

# The three segments reports/detector/gt_training_data_exhaustion_2026-08-15.md
# names as the unblock path: labels exist, geometry absent from the open bucket.
UNBLOCK_SEGMENTS = ("20230820203112", "20230826170124", "20230903193206")

needs_villa = pytest.mark.skipif(
    not (VILLA / ".git").exists() and not (VILLA / "ink-detection").exists(),
    reason="villa submodule not checked out",
)


def _digest(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def test_the_gp_winner_recipe_is_preserved():
    """train_timesformer_og.py is the recipe Phase 2 retrained to held-out AUC
    0.905. Upstream deleted it; without this copy the replication is unrunnable."""
    assert (PRESERVED / "train_timesformer_og.py").exists()
    assert (PRESERVED / "train_timesformer_og.py").stat().st_size > 10_000


def test_the_unblock_labels_are_preserved():
    """These three are the only identified route out of the GT exhaustion, and
    upstream has deleted the directory they lived in."""
    for seg in UNBLOCK_SEGMENTS:
        p = PRESERVED / "all_labels" / f"{seg}_inklabels.png"
        assert p.exists(), f"{seg} label missing"
        assert p.stat().st_size > 50_000, f"{seg} label suspiciously small"


@needs_villa
def test_every_preserved_file_matches_the_pin_byte_for_byte():
    """These are copies, not our work. If one drifts, it has been edited, and a
    silently edited copy of someone else's file is worse than no copy."""
    for path in sorted(PRESERVED.rglob("*")):
        if not path.is_file() or path.name == "README.md":
            continue
        rel = path.relative_to(PRESERVED).as_posix()
        out = subprocess.run(
            ["git", "-C", str(VILLA), "show", f"{PIN}:ink-detection/{rel}"],
            capture_output=True,
        )
        if out.returncode != 0:
            pytest.skip(f"pin object unavailable for {rel}")
        assert _digest(path.read_bytes()) == _digest(out.stdout), f"{rel} drifted"


@needs_villa
def test_the_recovery_command_in_the_readme_works():
    """The README tells a reader the other 42 labels are one command away. That
    claim is load-bearing for the decision not to copy 45 MB, so it is checked
    rather than asserted."""
    out = subprocess.run(
        [
            "git",
            "-C",
            str(VILLA),
            "show",
            f"{PIN}:ink-detection/all_labels/20230827161847_inklabels.png",
        ],
        capture_output=True,
    )
    assert out.returncode == 0
    assert len(out.stdout) > 50_000
    assert out.stdout[:8] == b"\x89PNG\r\n\x1a\n"
