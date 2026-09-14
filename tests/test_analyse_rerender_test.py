"""Tests for the re-render verdict, written before the re-render finished.

The threshold was registered before the number. The reason this is a script with
a test rather than a judgement call is that ±2% applied by eye, while looking at
a number I would prefer to be inside it, is how a band becomes "well, 2.3% is
basically 2%".
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_rerender_test as mod  # noqa: E402


def test_the_registered_constants():
    assert mod.BAND == 0.02
    assert mod.ORIGINAL_TAG == "curbase_s1"
    assert mod.RERENDER_TAG == "curbase_s1rr"
    assert mod.OLD_SHA_PREFIX == "d8c5f488a"


def _metrics(tmp_path, tag, ink, strip=403_291_800):
    d = tmp_path / f"outer_{tag}" / "ink_metric"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total_fg_pixels": ink,
                    "total_pixels": strip,
                    "overall_fg_fraction": ink / strip,
                    "overall_line_score": 0.33,
                    "overall_column_score": 0.14,
                }
            }
        )
    )


def _sha(tmp_path, tag, sha):
    (tmp_path / f"outer_{tag}" / "VILLA_SHA").write_text(sha + "\n")


def _run(tmp_path, capsys):
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    mod.main()
    return capsys.readouterr().out


@pytest.mark.parametrize(
    "ink,expected",
    [
        (2_904_520, "INERT"),
        (2_950_000, "INERT"),
        (2_860_000, "INERT"),
        (3_020_000, "ADDS INK"),
        (2_800_000, "REMOVES INK"),
    ],
)
def test_the_band_is_applied_mechanically(tmp_path, capsys, ink, expected):
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    _metrics(tmp_path, "curbase_s1rr", ink)
    _sha(tmp_path, "curbase_s1rr", "d82e13edf3390df0f3e3791b6c9a3ddae16d3360")
    assert expected in _run(tmp_path, capsys)


def test_the_boundary_is_not_fudged(tmp_path, capsys):
    """2.3% is not 'basically 2%'."""
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    _metrics(tmp_path, "curbase_s1rr", int(2_904_520 * 1.023))
    _sha(tmp_path, "curbase_s1rr", "d82e13edf")
    assert "ADDS INK" in _run(tmp_path, capsys)


def test_a_rerender_on_the_OLD_code_is_void_not_inert(tmp_path, capsys):
    """The failure that would look most like success: re-rendering with the same
    code gives an identical number, which reads as 'inert' unless the SHA is
    checked."""
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    _metrics(tmp_path, "curbase_s1rr", 2_904_520)
    _sha(tmp_path, "curbase_s1rr", "d8c5f488a1111111111111111111111111111111")
    out = _run(tmp_path, capsys)
    assert "VOID" in out and "OLD code" in out
    assert "INERT" not in out.split("VERDICT")[1]


def test_a_missing_sha_is_void(tmp_path, capsys):
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    _metrics(tmp_path, "curbase_s1rr", 2_904_520)
    assert "VOID" in _run(tmp_path, capsys)


def test_a_large_area_change_is_void(tmp_path, capsys):
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    _metrics(tmp_path, "curbase_s1rr", 2_904_520, strip=500_000_000)
    _sha(tmp_path, "curbase_s1rr", "d82e13edf")
    assert "VOID" in _run(tmp_path, capsys)


def test_an_unscored_rerender_is_refused(tmp_path):
    _metrics(tmp_path, "curbase_s1", 2_904_520)
    sys.argv = ["x", "--spiral-out", str(tmp_path)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "refused" in str(e.value)
