"""Tests for the registered non-blank control.

The control exists because an unscaled render exits 0 and writes an entirely
black strip, which would then be scored as "no ink" rather than "no render" -- a
silent failure in the direction of a null. So the test that matters most is that
a black strip actually FAILS, and that the sliver exemption cannot be widened
into a hole a genuinely blank arm slips through.
"""

import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import check_strip_nonblank as mod  # noqa: E402

_SCRIPT = os.path.join(_REPO, "scripts", "check_strip_nonblank.py")


def _tile(path, w, h, kind):
    """kind: 'inked' has bright content, 'black' is all zero, 'pad' is black with
    a thin bright edge so p99 > 0 like the real sliver tiles."""
    a = np.zeros((h, w), dtype=np.uint8)
    if kind == "inked":
        a[:, ::3] = 255
    elif kind == "pad":
        a[:, -max(1, w // 50) :] = 253
    Image.fromarray(a).save(path, quality=95)


def _arm(tmp_path, name, tiles):
    d = tmp_path / name / "meshes" / "ink"
    d.mkdir(parents=True)
    for i, (w, h, kind) in enumerate(tiles):
        _tile(str(d / f"w120-129_flat.{i:03d}.jpg"), w, h, kind)
    return str(tmp_path / name)


def test_a_normal_strip_passes(tmp_path):
    arm = _arm(
        tmp_path,
        "good",
        [(5000, 400, "inked"), (5000, 400, "inked"), (600, 400, "pad")],
    )
    ok, _ = mod.check(arm)
    assert ok


def test_an_all_black_strip_fails(tmp_path):
    """The whole point. This is what an unscaled render produces."""
    arm = _arm(tmp_path, "blank", [(5000, 400, "black"), (5000, 400, "black")])
    ok, notes = mod.check(arm)
    assert not ok
    assert any("BLANK" in n for n in notes)


def test_one_black_full_tile_fails_even_beside_good_ones(tmp_path):
    """A partial render failure must not be averaged away by its neighbours."""
    arm = _arm(
        tmp_path,
        "partial",
        [(5000, 400, "inked"), (5000, 400, "black"), (600, 400, "pad")],
    )
    ok, _ = mod.check(arm)
    assert not ok


def test_an_empty_sliver_does_not_void_an_arm_whose_full_tiles_are_inked(tmp_path):
    """Matches the registration, which tests "p95 > 0 on the five full tiles" and
    says nothing about the trailing sliver.

    An earlier version demanded p99 > 0 on the sliver too. That was stricter than
    the protocol and produced a FALSE POSITIVE on real data: gap133s5's sliver is
    70 px wide and entirely empty, and the arm was reported VOID although its five
    full tiles read p95 254/186/174/238/122. This test pins the corrected rule so
    the stricter one cannot creep back."""
    arm = _arm(tmp_path, "emptysliver", [(5000, 400, "inked"), (600, 400, "black")])
    ok, notes = mod.check(arm)
    assert ok
    assert any("exempt" in n for n in notes)


def test_a_wide_tile_never_gets_the_sliver_exemption(tmp_path):
    """If the exemption applied by position rather than width, a blank final tile
    of full width would pass."""
    arm = _arm(tmp_path, "widelast", [(5000, 400, "inked"), (5000, 400, "black")])
    assert not mod.check(arm)[0]
    assert mod.SLIVER_MAX_WIDTH < 5000


def test_a_missing_ink_dir_fails_rather_than_passing_vacuously(tmp_path):
    d = tmp_path / "empty" / "meshes" / "ink"
    d.mkdir(parents=True)
    ok, notes = mod.check(str(tmp_path / "empty"))
    assert not ok
    assert any("no *_flat" in n for n in notes)


def test_it_accepts_either_the_arm_dir_or_the_ink_dir(tmp_path):
    arm = _arm(tmp_path, "either", [(5000, 400, "inked")])
    assert mod.check(arm)[0]
    assert mod.check(os.path.join(arm, "meshes", "ink"))[0]


def test_the_cli_exits_nonzero_on_a_blank_arm(tmp_path):
    arm = _arm(tmp_path, "cliblank", [(5000, 400, "black")])
    rc = subprocess.run([sys.executable, _SCRIPT, arm], capture_output=True, text=True)
    assert rc.returncode == 1
    assert "VOID" in rc.stdout


def test_the_cli_exits_zero_on_a_good_arm(tmp_path):
    arm = _arm(tmp_path, "cligood", [(5000, 400, "inked"), (600, 400, "pad")])
    rc = subprocess.run([sys.executable, _SCRIPT, arm], capture_output=True, text=True)
    assert rc.returncode == 0, rc.stdout
    assert "PASS" in rc.stdout


def test_a_very_sparse_strip_fails_and_that_is_a_known_limitation(tmp_path):
    """Pins a limitation rather than a feature. The registered control is p95 > 0,
    so a strip that is only ~0.5% inked has p95 = 0 and is voided as BLANK even
    though it carries signal. The control cannot separate "sparse ink" from "no
    render".

    That is acceptable HERE only because every measured arm sits at 44.8-47.2%
    nonzero, nowhere near the boundary. If a future ROI renders genuinely sparse
    strips this control must be re-specified before it is trusted -- it would void
    real data. Written after my own first expectation (warn, do not void) turned
    out to contradict the registered rule."""
    d = tmp_path / "sparse" / "meshes" / "ink"
    d.mkdir(parents=True)
    a = np.zeros((400, 5000), dtype=np.uint8)
    a[:, ::200] = 255  # ~0.5% nonzero
    Image.fromarray(a).save(str(d / "w120-129_flat.000.jpg"), quality=95)
    ok, notes = mod.check(str(tmp_path / "sparse"))
    assert not ok
    assert any("BLANK" in n for n in notes)


def test_the_nonzero_band_warns_without_voting_on_its_own(tmp_path):
    """The nonzero-fraction band is advisory: a strip inside the p95 rule but
    outside the band warns and still passes, so the two checks cannot be confused
    for one another."""
    d = tmp_path / "dense" / "meshes" / "ink"
    d.mkdir(parents=True)
    a = np.full((400, 5000), 200, dtype=np.uint8)  # ~100% nonzero, above the band
    Image.fromarray(a).save(str(d / "w120-129_flat.000.jpg"), quality=95)
    ok, notes = mod.check(str(tmp_path / "dense"))
    assert ok
    assert any("WARNING" in n for n in notes)


# --- "no tiles" is not "blank" -------------------------------------------------
#
# Found 2026-09-04 while checking the first bootstrap arm: pointing the script at
# an arm directory printed "the arm is VOID and must not be scored" when the only
# real problem was that the tiles live under a different root. VOID is the most
# destructive verdict this script has, and it was being asserted on a mistyped
# path. The two cases need opposite responses -- re-point vs discard the arm.


def _predictions_arm(tmp_path, name, tiles):
    """The layout the render pipeline actually writes: ink_metric/predictions."""
    d = tmp_path / name / "ink_metric" / "predictions"
    d.mkdir(parents=True)
    for i, (w, h, kind) in enumerate(tiles):
        _tile(str(d / f"w120-129_flat_overlay.{i:03d}.jpg"), w, h, kind)
    return str(tmp_path / name)


def test_the_render_pipeline_layout_is_resolved(tmp_path):
    """Passing the render dir must find ink_metric/predictions without the caller
    knowing the internal layout."""
    arm = _predictions_arm(
        tmp_path, "outer_x", [(5000, 400, "inked"), (5000, 400, "inked")]
    )
    ok, notes = mod.check(arm)
    assert ok, notes


def test_no_tiles_is_reported_separately_from_a_blank_strip(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    ok, notes = mod.check(str(d))
    assert not ok
    assert notes[0].startswith(mod._NO_TILES)
    joined = " ".join(notes)
    assert "NOT a blank-strip verdict" in joined
    assert "VOID" not in joined


def test_a_blank_strip_still_says_void(tmp_path):
    """The softening must not have weakened the verdict that matters."""
    arm = _predictions_arm(
        tmp_path, "outer_blank", [(5000, 400, "black"), (5000, 400, "black")]
    )
    ok, notes = mod.check(arm)
    assert not ok
    assert not any(n.startswith(mod._NO_TILES) for n in notes)
