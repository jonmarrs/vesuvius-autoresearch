"""reports/cycle_length_gain_replication_2026-10-19.md quotes its JSON, and the JSON reproduces the first result."""

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
    (ROOT / "reports/cycle_length_gain_replication_2026-10-19.md").read_text().split()
)
RESULT = json.loads(
    (ROOT / "reports/cycle_length_gain_replication_2026-10-19.json").read_text()
)
FIRST = json.loads((ROOT / "reports/cycle_length_gain_2026-10-18.json").read_text())
PROBE = json.loads((ROOT / "reports/noise_probe_v3_pooled_2026-10-17.json").read_text())
NIGHT1, DAY, NIGHT2 = RESULT["arms"]
INCUMBENT = 0.265762


def signed(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(x):.4f}"


def quoted(c: dict) -> str:
    return (
        f"{signed(c['diff'])}, {signed(c['lo'])} to {signed(c['hi'])}: {c['reading']}"
    )


def f1(arm: dict, keep=lambda c: True) -> list[float]:
    return [c["val_f1"] for c in arm["cycles"] if keep(c)]


def plain(c: dict) -> bool:
    return clg._steps_held(c) and not c["cycle"].startswith("aug_mode_")


def t_interval(xs: list[float]) -> tuple[float, float, float]:
    m = statistics.mean(xs)
    half = stats.t.ppf(0.975, len(xs) - 1) * statistics.stdev(xs) / math.sqrt(len(xs))
    return m, m - half, m + half


def matched(night: dict, keep=lambda c: True) -> list[float]:
    out = []
    for c in night["cycles"]:
        same = [d["val_f1"] for d in DAY["cycles"] if d["cycle"] == c["cycle"]]
        assert same, c["cycle"]  # every night tweak also ran by day
        if keep(c):
            out.append(c["val_f1"] - statistics.mean(same))
    return out


def spacing(arm: dict) -> float:
    starts = [dt.datetime.fromisoformat(c["start"]) for c in arm["cycles"]]
    return (starts[-1] - starts[0]).total_seconds() / 60 / (len(starts) - 1)


def without_oom(d):
    return json.loads(json.dumps(d).replace(', "oom": false', ""))


def test_the_three_named_shifts_with_no_stop_reached():
    assert RESULT["since"] == FIRST["since"] == "2026-10-17T21:17:25"
    assert RESULT["sources"] == {
        "sprint_logs": [
            "sprint_logs/sprint_log_2026-10-17_19-10-03_night_shift.md",
            "sprint_logs/sprint_log_2026-10-18_07-35-03_day_shift.md",
            "sprint_logs/sprint_log_2026-10-18_19-10-03_night_shift.md",
        ],
        "run_log": ["run.log.old", "run.log"],
    }
    assert [a["budget"] for a in RESULT["arms"]] == [3600, 900, 3600]
    assert RESULT["promotion"] is None
    cycles = [c for a in RESULT["arms"] for c in a["cycles"]]
    assert len(cycles) == 64 and {c["result"] for c in cycles} == {"REVERTED"}
    assert not any(c["oom"] for c in cycles)
    assert all(a["crashed"] == 0 for a in RESULT["arms"])
    assert all(c["steps"] is not None for c in cycles)
    assert "(all 64 were REVERTED)" in REPORT and "none crashed" in REPORT


def test_it_reproduces_the_first_result():
    first = without_oom(FIRST)
    again = without_oom(RESULT)
    assert again["arms"][:2] == first["arms"]
    for k in ("all", "steps_held"):
        assert again["comparisons"][k][0] == first["comparisons"][k][0]
    assert "equal `cycle_length_gain_2026-10-18.json` exactly" in REPORT


def test_the_arms_table():
    arms = RESULT["arms"]
    rows = [
        ("cycles scored", [str(a["scored"]) for a in arms]),
        ("mean val_f1", [f"{a['mean']:.4f}" for a in arms]),
        ("SD", [f"{a['sd']:.4f}" for a in arms]),
        ("highest", [f"{max(f1(a)):.4f}" for a in arms]),
        ("median steps", [f"{a['median_steps']:,.0f}" for a in arms]),
    ]
    for name, cells in rows:
        assert f"| {name} | {' | '.join(cells)} |" in REPORT
    assert (
        f"12 sixty-minute cycles averaged val_f1 {NIGHT2['mean']:.4f} and the 10-18 day's 42 "
        f"fifteen-minute cycles {DAY['mean']:.4f}" in REPORT
    )
    assert 0.0019 < NIGHT2["sd"] < 0.0058
    best = max(NIGHT2["cycles"], key=lambda c: c["val_f1"])
    assert best["cycle"] == "loss_st_0.2"
    assert max(f1(DAY)) > best["val_f1"]
    assert (
        f"`loss_st_0.2` at {best['val_f1']:.4f}, came no closer to the promotion bar, "
        f"{INCUMBENT + clg.TOLERANCE:.4f}, than the day's {max(f1(DAY)):.4f}" in REPORT
    )


def test_the_comparisons_are_recomputed_and_quoted():
    for k, keep in (("all", lambda c: True), ("steps_held", clg._steps_held)):
        for c, night in zip(RESULT["comparisons"][k], (0, 2), strict=False):
            assert (c["long"], c["short"]) == (night, 1)
            a, b = f1(RESULT["arms"][night], keep), f1(DAY, keep)
            assert c == pytest.approx(dict(clg.welch(a, b), long=night, short=1))
    (p1, p2), (s1, s2) = (
        RESULT["comparisons"]["all"],
        RESULT["comparisons"]["steps_held"],
    )
    assert f"| all cycles (primary) | {quoted(p1)} | {quoted(p2)} |" in REPORT
    assert f"(secondary, descriptive) | {quoted(s1)} | {quoted(s2)} |" in REPORT
    assert [c["reading"] for c in (p1, p2, s1, s2)] == [
        "no measurable gain",
        "no measurable gain",
        "higher",
        "no measurable gain",
    ]
    assert (
        f"a difference of {signed(p2['diff'])}, Welch 95% interval {signed(p2['lo'])} to "
        f"{signed(p2['hi'])}. The first arm gave {signed(p1['diff'])} ({signed(p1['lo'])} to "
        f"{signed(p1['hi'])})" in REPORT
    )
    assert p1["hi"] < clg.TOLERANCE / 2 and p2["hi"] < clg.TOLERANCE / 2
    # "The replication's interval reaches 0.0001 below zero"
    assert f"{-s2['lo']:.4f}" == "0.0001" and "reaches 0.0001 below zero" in REPORT


def test_use_uamt_false_on_both_nights():
    (n1,), (d,), (n2,) = (
        [c for c in a["cycles"] if c["cycle"] == "use_uamt_False"]
        for a in RESULT["arms"]
    )
    for night in (NIGHT1, NIGHT2):
        assert (
            min(night["cycles"], key=lambda c: c["val_f1"])["cycle"] == "use_uamt_False"
        )
    assert f"{n1['val_f1']:.4f}" == f"{n2['val_f1']:.4f}"
    assert (
        f"It scored {n1['val_f1']:.4f} at 60 minutes both times ({n1['steps']:,} and {n2['steps']:,} "
        f"steps), against {d['val_f1']:.4f} at 15 minutes ({d['steps']:,} steps)"
        in REPORT
    )


def test_the_exploratory_numbers():
    tops = [c["hi"] for k in ("all", "steps_held") for c in RESULT["comparisons"][k]]
    pooled = clg.welch(f1(NIGHT1) + f1(NIGHT2), f1(DAY))
    pooled_held = clg.welch(
        f1(NIGHT1, clg._steps_held) + f1(NIGHT2, clg._steps_held),
        f1(DAY, clg._steps_held),
    )
    assert pooled["n_long"] == 22
    assert (
        f"22 cycles, {signed(pooled['diff'])} ({signed(pooled['lo'])} to {signed(pooled['hi'])}). "
        f"Without `use_uamt_*` and `batch_size_*`: {signed(pooled_held['diff'])} "
        f"({signed(pooled_held['lo'])} to {signed(pooled_held['hi'])})" in REPORT
    )
    every, held = matched(NIGHT2), matched(NIGHT2, clg._steps_held)
    assert (len(every), len(held)) == (12, 10)
    m, lo, hi = t_interval(every)
    m10, lo10, hi10 = t_interval(held)
    assert (
        f"{signed(m)} over all 12 (95% {signed(lo)} to {signed(hi)}), and {signed(m10)} over the 10 "
        f"without `use_uamt_*` and `batch_size_*` ({signed(lo10)} to {signed(hi10)}), the night higher in "
        f"{sum(x > 0 for x in held)} of those 10" in REPORT
    )
    m8, lo8, hi8 = t_interval(matched(NIGHT1, clg._steps_held))
    assert (
        f"The first arm gave {signed(m8)} over its 8 ({signed(lo8)} to {signed(hi8)})"
        in REPORT
    )
    tops += [
        pooled["hi"],
        pooled_held["hi"],
        hi,
        hi10,
        hi8,
        t_interval(matched(NIGHT1))[2],
    ]
    assert f"The highest interval top in this report is {max(tops):.4f}" in REPORT
    # "about +0.002 to +0.003, a fifth to a third of the tolerance": the step-neutral estimates
    gains = [RESULT["comparisons"]["steps_held"][i]["diff"] for i in (0, 1)]
    gains += [pooled_held["diff"], m10, m8]
    assert min(gains) >= clg.TOLERANCE / 5 and max(gains) < 0.0035
    assert "about +0.002 to +0.003, a fifth to a third of the tolerance" in REPORT


def test_the_side_load_rows_and_the_step_ranges():
    for start, name, steps in [
        ("2026-10-18T22:14", "weight_decay_0.1", 4590),
        ("2026-10-19T04:23", "loss_ink_dice_0.6", 5100),
        ("2026-10-19T06:26", "loss_fiber_bce_0.1", 5130),
    ]:
        (c,) = [c for c in NIGHT2["cycles"] if c["start"].startswith(start)]
        assert (c["cycle"], c["steps"]) == (name, steps)
        assert f"`{name}` ({steps:,}) |" in REPORT
    s2 = [c["steps"] for c in NIGHT2["cycles"] if plain(c)]
    s1 = [c["steps"] for c in NIGHT1["cycles"] if plain(c)]
    assert min(s2) == 4590  # "the arm's lowest step count"
    assert (
        f"Its {len(s2)} cycles without step-changing configs trained {min(s2):,}–{max(s2):,} steps, "
        f"median {statistics.median(s2):,.0f}; the 10-17 night's {len(s1)} trained {min(s1):,}–{max(s1):,}"
        in REPORT
    )
    rest = clg.welch(f1(NIGHT2, lambda c: c["cycle"] != "weight_decay_0.1"), f1(DAY))
    assert (
        f"{signed(rest['diff'])} ({signed(rest['lo'])} to {signed(rest['hi'])}), {rest['reading']}"
        in REPORT
    )


def test_the_owners_arithmetic():
    night, day = spacing(NIGHT2), spacing(DAY)
    assert f"started {night:.1f} minutes apart and the day's {day:.1f}" in REPORT
    assert f"about {night / day:.1f} times as many candidates" in REPORT
    n_short = math.floor(len(NIGHT2["cycles"]) * night / day)
    assert f"about {n_short} in the hours that held these 12" in REPORT
    fp = PROBE["false_promotion"]
    assert f"point rate of {100 * fp['point']:.2f}% per" in REPORT
    for n in (12, n_short):
        assert f"a night of {n} " in REPORT
        assert f"{100 * (1 - (1 - fp['point']) ** n):.1f}%" in REPORT
    assert f"from {100 * fp['low']:.3f}% to {100 * fp['high']:.1f}%" in REPORT
