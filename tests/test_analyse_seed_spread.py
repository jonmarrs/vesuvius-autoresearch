"""The seed-spread analysis is the executable form of a pre-registration, so its
arithmetic and its gates must be right BEFORE the real data arrives. Every test
here uses synthetic metrics files with hand-checkable answers.

The gate that matters most is the quality band: pooling a fit of different quality
would report a fit-quality difference as seed noise, which is precisely the error
the pre-registration exists to prevent.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "analyse_seed_spread.py"


def write_arm(tmp: Path, tag: str, total_fg: float, sat: float | None = None) -> str:
    m = tmp / f"{tag}_metrics.json"
    m.write_text(
        json.dumps(
            {
                "summary": {
                    "total_fg_pixels": total_fg,
                    "overall_fg_fraction": total_fg / 2.5e7,
                    "overall_line_score": 0.4,
                    "overall_column_score": 0.2,
                }
            }
        )
    )
    if sat is None:
        return f"{tag}={m}"
    s = tmp / f"{tag}_sat.json"
    s.write_text(json.dumps({"summary": {"satisfied_area_fraction": sat}}))
    return f"{tag}={m},{s}"


def run(*specs):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), *specs],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout


def test_cv_matches_a_hand_computed_value(tmp_path):
    """Read the CV from the JSON, not the printed table: stdout rounds to 4 dp and
    comparing that against full precision fails for reasons that say nothing about
    the arithmetic."""
    import statistics

    vals = [90.0, 100.0, 110.0, 100.0]
    outfile = tmp_path / "spread.json"
    run(
        *[write_arm(tmp_path, f"s{i}", v, 0.84) for i, v in enumerate(vals)],
        "--out",
        str(outfile),
    )
    got = json.loads(outfile.read_text())["total_fg_pixels"]["cv"]
    want = statistics.stdev(vals) / statistics.fmean(vals)
    assert abs(got - want) < 1e-12


def test_identical_fits_give_zero_spread(tmp_path):
    out = run(*[write_arm(tmp_path, f"s{i}", 200.0, 0.84) for i in range(3)])
    assert "HEADLINE  total_fg_pixels CV = 0.0000" in out


def test_a_differing_quality_fit_is_refused_not_pooled(tmp_path):
    """The registered gate. A fit outside the satisfied-area band is not a
    like-for-like member; pooling it would report fit quality as seed noise."""
    specs = [
        write_arm(tmp_path, "a", 100.0, 0.840),
        write_arm(tmp_path, "b", 101.0, 0.841),
        write_arm(tmp_path, "bad", 400.0, 0.100),
    ]
    out = run(*specs)
    assert "NOT COMPARABLE" in out
    assert "outliers, reported separately and NOT pooled: bad" in out
    # the wild value must not reach the CV
    cv = float(
        [ln for ln in out.splitlines() if ln.startswith("HEADLINE")][0].split("=")[1]
    )
    assert cv < 0.02, "the excluded outlier must not inflate the spread"


def test_within_band_fits_are_pooled(tmp_path):
    specs = [
        write_arm(tmp_path, "a", 100.0, 0.840),
        write_arm(tmp_path, "b", 120.0, 0.845),
        write_arm(tmp_path, "c", 110.0, 0.848),
    ]
    out = run(*specs)
    assert "-> pooled" in out and "NOT COMPARABLE" not in out


def test_verdict_branches_are_the_registered_ones(tmp_path):
    """Verdict text must follow the thresholds fixed in advance, not the data."""
    tight = run(
        *[
            write_arm(tmp_path, f"t{i}", v, 0.84)
            for i, v in enumerate([100.0, 101.0, 100.5])
        ]
    )
    assert "OVERSTATED the floor" in tight
    wide = run(
        *[
            write_arm(tmp_path, f"w{i}", v, 0.84)
            for i, v in enumerate([80.0, 100.0, 120.0])
        ]
    )
    assert "very noisy across seeds" in wide


def test_pairwise_count_is_n_choose_2(tmp_path):
    """Four fits must yield six pairwise differences, as registered."""
    out = run(*[write_arm(tmp_path, f"s{i}", 100.0 + i, 0.84) for i in range(4)])
    row = [ln for ln in out.splitlines() if ln.startswith("total_fg_pixels")][0]
    assert row.split()[1] == "4"
    assert "pair min" in out and "pair max" in out


def run_expect_fail(*specs):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), *specs], capture_output=True, text=True
    )
    assert r.returncode != 0, "expected a refusal, got success"
    return r.stdout + r.stderr


def test_a_single_survivor_is_refused_not_reported_as_zero_spread(tmp_path):
    """The dangerous case. Three fits of wildly different quality leave one survivor
    after the quality gate; sd of one value is 0, which would print CV 0.0000 and
    read as 'no seed noise at all'. That is a fabrication from a single point, and
    it would have produced a confident wrong verdict on real data."""
    specs = [
        write_arm(tmp_path, "a", 100.0, 0.10),
        write_arm(tmp_path, "b", 200.0, 0.50),
        write_arm(tmp_path, "c", 300.0, 0.90),
    ]
    out = run_expect_fail(*specs)
    assert "a spread cannot be computed" in out
    assert "fabrication" in out
    assert "CV = 0.0000" not in out


def test_two_pooled_fits_warn_that_the_sample_is_undersized(tmp_path):
    """n=2 is computable but below the registered design of four, and a CV from two
    points carries uncertainty comparable to itself. It must say so."""
    out = run(
        write_arm(tmp_path, "a", 100.0, 0.840), write_arm(tmp_path, "b", 115.0, 0.845)
    )
    assert "WARNING: only 2 fits pooled" in out
    assert "registered design is four" in out
