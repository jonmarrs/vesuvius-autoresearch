"""reports/cycle_length_gain_2026-10-18.md quotes cycle_length_gain_2026-10-18.json correctly."""

from __future__ import annotations

import datetime as dt
import json
import math
import statistics
import sys
from pathlib import Path

import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cycle_length_gain as clg  # noqa: E402

REPORT = " ".join(
    (ROOT / "reports/cycle_length_gain_2026-10-18.md").read_text().split()
)
PREREG = " ".join(
    (ROOT / "reports/cycle_length_gain_prereg_2026-10-18.md").read_text().split()
)
RESULT = json.loads((ROOT / "reports/cycle_length_gain_2026-10-18.json").read_text())
NIGHT, DAY = RESULT["arms"]
INCUMBENT = 0.265762


def signed(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(x):.4f}"


def at(start: str) -> dict:
    (c,) = [c for c in DAY["cycles"] if c["start"].startswith(start)]
    return c


def matched(keep) -> list[float]:
    out = []
    for c in NIGHT["cycles"]:
        same = [d["val_f1"] for d in DAY["cycles"] if d["cycle"] == c["cycle"]]
        if same and keep(c):
            out.append(c["val_f1"] - statistics.mean(same))
    return out


def t_interval(xs: list[float]) -> tuple[float, float, float]:
    m = statistics.mean(xs)
    half = stats.t.ppf(0.975, len(xs) - 1) * statistics.stdev(xs) / math.sqrt(len(xs))
    return m, m - half, m + half


def test_the_arms_are_the_two_named_shifts_with_no_stop_reached():
    assert RESULT["since"] == "2026-10-17T21:17:25"
    assert RESULT["sources"] == {
        "sprint_logs": [
            "sprint_logs/sprint_log_2026-10-17_19-10-03_night_shift.md",
            "sprint_logs/sprint_log_2026-10-18_07-35-03_day_shift.md",
        ],
        "run_log": ["run.log.old", "run.log"],
    }
    assert (NIGHT["budget"], DAY["budget"]) == (3600, 900)
    assert RESULT["promotion"] is None
    cycles = NIGHT["cycles"] + DAY["cycles"]
    assert len(cycles) == 52 and {c["result"] for c in cycles} == {"REVERTED"}
    assert NIGHT["crashed"] == DAY["crashed"] == 0
    assert all(c["steps"] is not None for c in cycles)
    assert "all 52 were REVERTED" in REPORT and "none crashed" in REPORT


def test_the_arms_table():
    rows = [
        ("cycles scored", NIGHT["scored"], DAY["scored"]),
        ("mean val_f1", f"{NIGHT['mean']:.4f}", f"{DAY['mean']:.4f}"),
        ("SD", f"{NIGHT['sd']:.4f}", f"{DAY['sd']:.4f}"),
        (
            "highest",
            f"{max(c['val_f1'] for c in NIGHT['cycles']):.4f}",
            f"{max(c['val_f1'] for c in DAY['cycles']):.4f}",
        ),
        (
            "median steps",
            f"{NIGHT['median_steps']:,.0f}",
            f"{DAY['median_steps']:,.0f}",
        ),
    ]
    for name, night, day in rows:
        assert f"| {name} | {night} | {day} |" in REPORT
    assert f"10 sixty-minute cycles averaged val_f1 {NIGHT['mean']:.4f}" in REPORT
    assert f"42 fifteen-minute cycles {DAY['mean']:.4f}" in REPORT
    # Both SDs inside the pooled probe's interval, which the pre-registration quotes.
    assert (
        "0.0029 (0.0019–0.0058, #109)" in PREREG
        and "0.0029 (0.0019–0.0058, #109)" in REPORT
    )
    assert 0.0019 < DAY["sd"] < NIGHT["sd"] < 0.0058


def test_the_closest_cycle_to_the_promotion_bar():
    best = max(c["val_f1"] for c in NIGHT["cycles"] + DAY["cycles"])
    assert (
        best == max(c["val_f1"] for c in DAY["cycles"])
        and best < INCUMBENT + clg.TOLERANCE
    )
    assert (
        f"promotion bar, {INCUMBENT + clg.TOLERANCE:.4f} (the incumbent's {INCUMBENT:.4f} plus 0.01), "
        f"was the day's {best:.4f}" in REPORT
    )


def test_the_comparisons_are_recomputed_and_quoted():
    (primary,) = RESULT["comparisons"]["all"]
    (secondary,) = RESULT["comparisons"]["steps_held"]
    f1 = [[c["val_f1"] for c in arm["cycles"]] for arm in (NIGHT, DAY)]
    assert primary == pytest.approx(dict(clg.welch(*f1), long=0, short=1))
    held = [
        [c["val_f1"] for c in arm["cycles"] if clg._steps_held(c)]
        for arm in (NIGHT, DAY)
    ]
    assert secondary == pytest.approx(dict(clg.welch(*held), long=0, short=1))
    for name, c in (("all cycles (primary)", primary), ("descriptive)", secondary)):
        quoted = f"{name} | {signed(c['diff'])} | {signed(c['lo'])} to {signed(c['hi'])} | {c['reading']} |"
        assert quoted in REPORT
    assert (primary["reading"], secondary["reading"]) == (
        "no measurable gain",
        "higher",
    )
    assert (
        f"a difference of {signed(primary['diff'])}, Welch 95% interval "
        f"{signed(primary['lo'])} to {signed(primary['hi'])}" in REPORT
    )
    assert (
        primary["hi"] < clg.TOLERANCE / 2
    )  # "its top is under half the 0.01 tolerance"


def test_use_uamt_false_in_each_arm():
    (night,) = [c for c in NIGHT["cycles"] if c["cycle"] == "use_uamt_False"]
    (day,) = [c for c in DAY["cycles"] if c["cycle"] == "use_uamt_False"]
    assert night["val_f1"] == min(c["val_f1"] for c in NIGHT["cycles"])
    assert (
        f"scored {night['val_f1']:.4f} at 60 minutes ({night['steps']:,} steps, the night's lowest) "
        f"and {day['val_f1']:.4f} at 15 minutes ({day['steps']:,} steps)" in REPORT
    )


def test_the_matched_tweaks():
    assert all(
        any(d["cycle"] == c["cycle"] for d in DAY["cycles"]) for c in NIGHT["cycles"]
    )
    every = matched(lambda c: True)
    held = matched(clg._steps_held)
    assert (len(every), len(held)) == (10, 8)
    m, lo, hi = t_interval(every)
    assert f"{signed(m)} over all 10 (95% {signed(lo)} to {signed(hi)})" in REPORT
    m8, lo8, hi8 = t_interval(held)
    assert f"{signed(m8)} over the 8 without" in REPORT
    assert (
        f"({signed(lo8)} to {signed(hi8)}), the night higher in 7 of those 8" in REPORT
    )
    assert sum(x > 0 for x in held) == 7
    # "about a third of the tolerance", "no interval above reaches past 0.0053".
    assert 0.28 < m8 / clg.TOLERANCE < 0.38
    tops = [hi, hi8] + [
        c["hi"] for k in ("all", "steps_held") for c in RESULT["comparisons"][k]
    ]
    assert f"{max(tops):.4f}" == "0.0053" and "reaches past 0.0053" in REPORT


def test_the_side_load_cycles_and_the_day_step_range():
    for start, name, steps in [
        ("2026-10-18T09:31", "multi_task_heads_False", 1280),
        ("2026-10-18T15:34", "batch_size_16", 650),
        ("2026-10-18T15:50", "lr_0.001", 1290),
        ("2026-10-18T16:56", "multi_task_heads_False", 1220),
        ("2026-10-18T17:13", "target_fiber_source_sobel_z", 1120),
    ]:
        c = at(start)
        assert (c["cycle"], c["steps"]) == (name, steps)
        assert f"`{name}` ({steps:,}" in REPORT
    assert at("2026-10-18T11:10")["steps"] == 650  # "as at 11:10"
    plain = [
        c["steps"]
        for c in DAY["cycles"]
        if clg._steps_held(c) and not c["cycle"].startswith("aug_mode_")
    ]
    aug = [c["steps"] for c in DAY["cycles"] if c["cycle"].startswith("aug_mode_")]
    assert len(plain) == 36 and all(950 <= s <= 1050 for s in aug)
    assert (
        f"trained {min(plain):,}–{max(plain):,} steps, median {statistics.median(plain):,.0f}"
        in REPORT
    )
    assert min(plain) == at("2026-10-18T17:13")["steps"]
    assert DAY["median_steps"] * 4 == NIGHT["median_steps"]


def test_the_cycle_spacing():
    def spacing(arm):
        starts = [dt.datetime.fromisoformat(c["start"]) for c in arm["cycles"]]
        return (starts[-1] - starts[0]).total_seconds() / 60 / (len(starts) - 1)

    day, night = spacing(DAY), spacing(NIGHT)
    assert f"started {day:.1f} minutes apart and the night's {night:.1f}" in REPORT
    assert f"tries {night / day:.1f} candidates" in REPORT
