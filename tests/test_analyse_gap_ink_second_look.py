"""Tests for the second-look analysis.

Written before any of the five new arms produced a number.

The two tests that matter are the ones enforcing the registration against me:
that alpha is the Pocock 0.0294 rather than 0.05, and that a partial sample is
REFUSED rather than reported. The first-look script accepted >=2 per arm, and by
the end of that arm its guard no longer bit -- I had to decline to peek by hand.
Relying on that again would be relying on the wrong thing.
"""

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import analyse_gap_ink_arm as look1  # noqa: E402
import analyse_gap_ink_second_look as mod  # noqa: E402


def _files(tmp_path, values):
    args = []
    for tag, fg in values.items():
        p = tmp_path / f"{tag}.json"
        p.write_text(
            json.dumps(
                {
                    "summary": {
                        "total_fg_pixels": fg,
                        "overall_fg_fraction": fg / 3.6e8,
                        "overall_line_score": 0.35 + (fg % 7) * 1e-4,
                        "overall_column_score": 0.19 + (fg % 5) * 1e-3,
                    }
                }
            )
        )
        args.append(f"{tag}={p}")
    return args


def _full(base_vals, gap_vals):
    v = {}
    for t, x in zip(mod.BASE_ARMS, base_vals, strict=False):
        v[t] = x
    for t, x in zip(mod.GAP_ARMS, gap_vals, strict=False):
        v[t] = x
    return v


def test_alpha_is_the_pocock_boundary_not_the_usual_one():
    """The whole reason this script exists separately from the first look."""
    assert mod.ALPHA == 0.0294
    assert look1.ALPHA == 0.05
    assert mod.ALPHA < look1.ALPHA


def test_it_requires_six_per_arm():
    assert mod.REQUIRED_PER_ARM == 6
    assert len(mod.BASE_ARMS) == 6
    assert len(mod.GAP_ARMS) == 6


def test_a_partial_sample_is_refused_not_reported(tmp_path):
    """The no-peeking rule, enforced structurally. Five per arm must be an error."""
    vals = _full(
        [1.79e6, 1.73e6, 1.62e6, 1.68e6, 1.70e6, 1.71e6],
        [1.59e6, 1.60e6, 1.45e6, 1.55e6, 1.52e6, 1.57e6],
    )
    del vals["seed06"], vals["gap133s6"]
    sys.argv = ["x", *_files(tmp_path, vals)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "SECOND LOOK" in str(e.value)
    assert "interim" in str(e.value)


def test_an_unregistered_arm_is_refused(tmp_path):
    vals = _full([1.79e6] * 6, [1.59e6] * 6)
    vals["margin0"] = 1.6e6
    sys.argv = ["x", *_files(tmp_path, vals)]
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert "margin0" in str(e.value)


def test_the_first_look_arms_alone_are_refused(tmp_path):
    """4 and 3 is look 1's sample. Running it through the second-look alpha would
    be re-testing the same data at a different threshold."""
    vals = {t: 1.7e6 for t in mod.BASE_ARMS[:4]}
    vals.update({t: 1.55e6 for t in mod.GAP_ARMS[:3]})
    sys.argv = ["x", *_files(tmp_path, vals)]
    with pytest.raises(SystemExit):
        mod.main()


def test_a_real_effect_is_established_at_the_stricter_alpha(tmp_path, capsys):
    vals = _full(
        [1.79e6, 1.73e6, 1.62e6, 1.68e6, 1.75e6, 1.71e6],
        [1.45e6, 1.48e6, 1.44e6, 1.46e6, 1.50e6, 1.47e6],
    )
    sys.argv = ["x", *_files(tmp_path, vals)]
    mod.main()
    out = capsys.readouterr().out
    assert "REDUCES" in out
    assert "MET" in out


def test_an_effect_that_only_clears_0_05_is_NOT_established(tmp_path, capsys):
    """The case the stricter alpha exists for: a p between 0.0294 and 0.05 must
    read as not established, and must say the question is closed."""
    base = [1.79e6, 1.73e6, 1.62e6, 1.68e6, 1.75e6, 1.71e6]
    gap = [1.686e6, 1.646e6, 1.566e6, 1.716e6, 1.626e6, 1.596e6]
    w = look1.welch(base, gap)
    assert mod.ALPHA <= w["p"] < 0.05, (
        f"fixture must land between the alphas, got {w['p']:.4f}"
    )
    sys.argv = [
        "x",
        *_files(
            tmp_path, dict(zip(mod.BASE_ARMS + mod.GAP_ARMS, base + gap, strict=False))
        ),
    ]
    mod.main()
    out = capsys.readouterr().out
    assert "not established" in out
    assert "CLOSED" in out
    assert "MISS" in out


def test_separation_is_labelled_confirmatory_only(tmp_path, capsys):
    vals = _full(
        [1.79e6, 1.78e6, 1.77e6, 1.76e6, 1.75e6, 1.74e6],
        [1.45e6, 1.44e6, 1.43e6, 1.42e6, 1.41e6, 1.40e6],
    )
    sys.argv = ["x", *_files(tmp_path, vals)]
    mod.main()
    out = capsys.readouterr().out
    assert "COMPLETE" in out
    assert "never replaces" in out
    assert "0.108%" in out  # 1/C(12,6)


def test_it_writes_the_registered_fields(tmp_path):
    vals = _full(
        [1.79e6, 1.73e6, 1.62e6, 1.68e6, 1.75e6, 1.71e6],
        [1.45e6, 1.48e6, 1.44e6, 1.46e6, 1.50e6, 1.47e6],
    )
    out = tmp_path / "res.json"
    sys.argv = ["x", *_files(tmp_path, vals), "--out", str(out)]
    mod.main()
    got = json.loads(out.read_text())
    assert got["alpha"] == 0.0294
    assert len(got["base"]) == 6 and len(got["gap"]) == 6
    assert got["prediction_met"] is True
