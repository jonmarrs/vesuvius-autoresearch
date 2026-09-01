"""The two-seed power analysis produces numbers that argue for changing villa's
procedure, so its arithmetic has to be right.

The exact arm is fully deterministic and hand-checkable; the parametric arm is
seeded. Both are pinned here. The properties tested are the ones the report's
conclusions rest on, not the incidental output format.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "analyse_two_seed_check_power.py"


def run():
    return subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=True
    ).stdout


def test_exact_and_parametric_agree_on_the_null_rate():
    """The report's central claim rests on two independent methods agreeing: an
    assumption-free enumeration over 4 values and a 200k simulation. If they ever
    diverge, one of them is wrong and the headline is unsupported."""
    out = run()
    assert "1/6 orderings call a null change a win" in out, (
        "exact rule A must be 1 of 6"
    )
    assert "3/6 orderings call a null change a win" in out, (
        "exact rule B must be 3 of 6"
    )
    # parametric false-positive row at true effect 0
    row = [ln for ln in out.splitlines() if ln.strip().startswith("0%")][0]
    a, b = [float(x.rstrip("%")) for x in row.split() if x.endswith("%")][1:3]
    assert abs(a - 100 * 1 / 6) < 1.5, f"rule A parametric {a}% must match exact 16.7%"
    assert abs(b - 50.0) < 1.5, f"rule B parametric {b}% must match exact 50%"


def test_rule_b_is_a_coin_flip_at_every_seed_count():
    """Averaging cannot break a symmetric comparison of equal distributions. If
    this ever showed rule B improving with k, the simulation would be biased."""
    out = run()
    seg = out.split("HOW MANY SEEDS")[1].split("rule B is a coin flip")[0]
    b_rates = [
        float(ln.split()[2].rstrip("%"))
        for ln in seg.splitlines()
        if ln.strip()[:1].isdigit()
    ]
    assert len(b_rates) >= 5
    assert all(abs(r - 50.0) < 1.0 for r in b_rates), (
        f"rule B must stay ~50%, got {b_rates}"
    )


def test_more_seeds_monotonically_helps_rule_a():
    """The recommendation is 'use three seeds'. That only follows if the rate
    falls monotonically with k."""
    out = run()
    seg = out.split("HOW MANY SEEDS")[1].split("rule B is a coin flip")[0]
    a_rates = [
        float(ln.split()[1].rstrip("%"))
        for ln in seg.splitlines()
        if ln.strip()[:1].isdigit()
    ]
    assert a_rates == sorted(a_rates, reverse=True), f"must fall with k, got {a_rates}"
    assert a_rates[1] < 6.0, "three seeds must reach about 5%, the reported figure"


def test_two_metric_rule_is_never_weaker_than_one():
    """The report claims the two-metric rule is stronger across the whole
    plausible correlation range and never weaker. At rho=1 it must degenerate to
    the single-metric rate, not exceed it."""
    out = run()
    seg = out.split("TWO-METRIC RULE")[1].split("single-metric")[0]
    # note: `"" in "-01"` is True in Python, so a blank-line filter written that
    # way silently admits empty lines. Match on shape instead.
    rates = [
        float(ln.split()[1].rstrip("%"))
        for ln in seg.splitlines()
        if len(ln.split()) == 2 and ln.split()[1].endswith("%")
    ]
    assert rates == sorted(rates), f"must rise with correlation, got {rates}"
    assert rates[-1] <= 17.0, (
        "at perfect correlation it degenerates to ~16.6%, never worse"
    )
    assert rates[0] < 2.0, "at negative correlation it should be well under 2%"
